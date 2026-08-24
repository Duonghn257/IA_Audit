"""Google OpenID Connect adapter for the web-server authorization flow."""
from __future__ import annotations

import base64
import hashlib
import secrets
from urllib.parse import urlencode

import requests
from google.auth.exceptions import GoogleAuthError
from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2 import id_token

from app.domain.auth import AuthIdentity

_AUTHORIZATION_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
_TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"


class GoogleOAuthError(RuntimeError):
    """Raised when Google cannot establish a trusted user identity."""


class GoogleOAuthClient:
    def __init__(
        self,
        *,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        allowed_domains: tuple[str, ...] = (),
    ) -> None:
        self._client_id = client_id
        self._client_secret = client_secret
        self._redirect_uri = redirect_uri
        self._allowed_domains = frozenset(value.lower() for value in allowed_domains)

    @staticmethod
    def create_transaction() -> tuple[str, str, str, str]:
        state = secrets.token_urlsafe(32)
        verifier = secrets.token_urlsafe(64)
        nonce = secrets.token_urlsafe(32)
        digest = hashlib.sha256(verifier.encode("ascii")).digest()
        challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
        return state, verifier, nonce, challenge

    def authorization_url(
        self,
        *,
        state: str,
        nonce: str,
        code_challenge: str,
    ) -> str:
        return f"{_AUTHORIZATION_ENDPOINT}?{urlencode({
            'client_id': self._client_id,
            'redirect_uri': self._redirect_uri,
            'response_type': 'code',
            'scope': 'openid email profile',
            'state': state,
            'nonce': nonce,
            'code_challenge': code_challenge,
            'code_challenge_method': 'S256',
            'prompt': 'select_account',
        })}"

    def exchange_code(
        self,
        *,
        code: str,
        code_verifier: str,
        expected_nonce: str,
    ) -> AuthIdentity:
        try:
            response = requests.post(
                _TOKEN_ENDPOINT,
                data={
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                    "code": code,
                    "code_verifier": code_verifier,
                    "grant_type": "authorization_code",
                    "redirect_uri": self._redirect_uri,
                },
                timeout=15,
            )
            response.raise_for_status()
            raw_id_token = response.json().get("id_token")
            if not raw_id_token:
                raise GoogleOAuthError("Google did not return an ID token.")
            claims = id_token.verify_oauth2_token(
                raw_id_token,
                GoogleRequest(),
                self._client_id,
            )
        except (requests.RequestException, ValueError, GoogleAuthError) as exc:
            raise GoogleOAuthError("Google token verification failed.") from exc

        if not secrets.compare_digest(str(claims.get("nonce", "")), expected_nonce):
            raise GoogleOAuthError("Google ID token nonce did not match.")
        subject = str(claims.get("sub", "")).strip()
        email = str(claims.get("email", "")).strip().lower()
        if not subject or not email or claims.get("email_verified") is not True:
            raise GoogleOAuthError("A verified Google account email is required.")
        hosted_domain = str(claims.get("hd", "")).strip().lower() or None
        if self._allowed_domains and hosted_domain not in self._allowed_domains:
            raise GoogleOAuthError("This Google Workspace domain is not allowed.")
        return AuthIdentity(
            provider="GOOGLE",
            provider_subject=subject,
            email=email,
            email_verified=True,
            display_name=str(claims.get("name") or email),
            picture_url=str(claims.get("picture") or "") or None,
            hosted_domain=hosted_domain,
        )
