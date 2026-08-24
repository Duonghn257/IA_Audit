"""API schemas for authenticated browser sessions."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.api.dependencies import AuthPrincipal


class AuthUserResponse(BaseModel):
    user_id: str
    email: str
    display_name: str
    picture_url: str | None
    hosted_domain: str | None
    provider: str


class AuthSessionResponse(BaseModel):
    auth_enabled: bool
    csrf_token: str
    expires_at: datetime | None
    user: AuthUserResponse

    @classmethod
    def from_principal(
        cls,
        principal: AuthPrincipal,
        *,
        auth_enabled: bool,
    ) -> "AuthSessionResponse":
        user = principal.user
        return cls(
            auth_enabled=auth_enabled,
            csrf_token=principal.csrf_token,
            expires_at=principal.expires_at,
            user=AuthUserResponse(
                user_id=user.user_id,
                email=user.email,
                display_name=user.display_name,
                picture_url=user.picture_url,
                hosted_domain=user.hosted_domain,
                provider=user.provider,
            ),
        )
