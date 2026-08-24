"""Google login, callback, current-session and logout endpoints."""
from __future__ import annotations

import secrets
from typing import Annotated
from urllib.parse import quote, urlsplit

from fastapi import APIRouter, Depends, Query, Request, status
from fastapi.responses import RedirectResponse, Response

from app.api.dependencies import (
    AuthServiceDependency,
    CurrentPrincipalDependency,
    GoogleOAuthDependency,
    SettingsDependency,
    require_csrf,
)
from app.api.errors import ApiError
from app.api.schemas.auth import AuthSessionResponse
from app.infrastructure.google_oauth import GoogleOAuthError

router = APIRouter(prefix="/auth", tags=["auth"])
callback_alias_router = APIRouter(tags=["auth"])
_STATE_COOKIE = "google_oauth_state"
_VERIFIER_COOKIE = "google_oauth_verifier"
_NONCE_COOKIE = "google_oauth_nonce"


@router.get("/google/login", response_class=RedirectResponse)
def google_login(
    settings: SettingsDependency,
    google: GoogleOAuthDependency,
) -> RedirectResponse:
    if not settings.google_auth_enabled or google is None:
        raise ApiError(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            code="GOOGLE_AUTH_NOT_CONFIGURED",
            message="Google login is not configured for this environment.",
        )
    state_token, verifier, nonce, challenge = google.create_transaction()
    response = RedirectResponse(
        google.authorization_url(
            state=state_token,
            nonce=nonce,
            code_challenge=challenge,
        ),
        status_code=status.HTTP_302_FOUND,
    )
    for name, value in (
        (_STATE_COOKIE, state_token),
        (_VERIFIER_COOKIE, verifier),
        (_NONCE_COOKIE, nonce),
    ):
        response.set_cookie(
            name,
            value,
            max_age=600,
            httponly=True,
            secure=settings.auth_cookie_secure,
            samesite="lax",
            path=_oauth_cookie_path(settings),
        )
    return response


@router.get("/google/callback", response_class=RedirectResponse)
@callback_alias_router.get(
    "/api/auth/callback/google",
    response_class=RedirectResponse,
    include_in_schema=False,
)
def google_callback(
    request: Request,
    settings: SettingsDependency,
    auth_service: AuthServiceDependency,
    google: GoogleOAuthDependency,
    code: Annotated[str | None, Query()] = None,
    state_token: Annotated[str | None, Query(alias="state")] = None,
    error: Annotated[str | None, Query()] = None,
) -> RedirectResponse:
    if not settings.google_auth_enabled or google is None:
        raise ApiError(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            code="GOOGLE_AUTH_NOT_CONFIGURED",
            message="Google login is not configured for this environment.",
        )
    if error:
        response = RedirectResponse(
            _with_auth_error(settings.auth_post_login_redirect, error),
            status_code=status.HTTP_303_SEE_OTHER,
        )
        _clear_oauth_cookies(response, settings)
        return response

    expected_state = request.cookies.get(_STATE_COOKIE)
    verifier = request.cookies.get(_VERIFIER_COOKIE)
    nonce = request.cookies.get(_NONCE_COOKIE)
    if (
        not state_token
        or not expected_state
        or not secrets.compare_digest(state_token, expected_state)
        or not verifier
        or not nonce
        or not code
    ):
        raise ApiError(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="INVALID_OAUTH_CALLBACK",
            message="Google login state could not be verified. Please try again.",
        )
    try:
        identity = google.exchange_code(
            code=code,
            code_verifier=verifier,
            expected_nonce=nonce,
        )
    except GoogleOAuthError as exc:
        raise ApiError(
            status_code=status.HTTP_502_BAD_GATEWAY,
            code="GOOGLE_LOGIN_FAILED",
            message=str(exc),
        ) from exc

    session, raw_token = auth_service.sign_in(identity)
    response = RedirectResponse(
        settings.auth_post_login_redirect,
        status_code=status.HTTP_303_SEE_OTHER,
    )
    response.set_cookie(
        settings.auth_cookie_name,
        raw_token,
        max_age=settings.auth_session_ttl_hours * 3600,
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite="lax",
        path="/",
    )
    _clear_oauth_cookies(response, settings)
    return response


@router.get("/me", response_model=AuthSessionResponse)
def get_me(
    principal: CurrentPrincipalDependency,
    settings: SettingsDependency,
) -> AuthSessionResponse:
    return AuthSessionResponse.from_principal(
        principal,
        auth_enabled=settings.google_auth_enabled,
    )


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_csrf)],
)
def logout(
    request: Request,
    settings: SettingsDependency,
    auth_service: AuthServiceDependency,
    principal: CurrentPrincipalDependency,
) -> Response:
    del principal
    auth_service.sign_out(request.cookies.get(settings.auth_cookie_name))
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    response.delete_cookie(settings.auth_cookie_name, path="/")
    return response


def _clear_oauth_cookies(
    response: Response,
    settings: SettingsDependency,
) -> None:
    for name in (_STATE_COOKIE, _VERIFIER_COOKIE, _NONCE_COOKIE):
        response.delete_cookie(name, path=_oauth_cookie_path(settings))


def _oauth_cookie_path(settings: SettingsDependency) -> str:
    redirect_uri = settings.google_redirect_uri or ""
    return urlsplit(redirect_uri).path or "/"


def _with_auth_error(base_url: str, error: str) -> str:
    separator = "&" if "?" in base_url else "?"
    return f"{base_url}{separator}auth_error={quote(error[:100])}"
