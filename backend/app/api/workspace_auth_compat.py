"""Compatibility adapters for callers that use the original auth function shape."""

from __future__ import annotations

from fastapi.security import HTTPAuthorizationCredentials

from app.api.workspace_autonomy import autonomous_workspace_credential
from app.core.config import get_settings
from app.services.digital_asset_hosting import WorkspaceCredential


def authenticate_workspace_key(
    token: str,
    *,
    signing_secret: str,
) -> WorkspaceCredential:
    """Keep the original signature while making the database the expiry authority."""

    settings = get_settings()
    if signing_secret != settings.integration_secret:
        # The caller-provided secret remains part of the compatibility contract;
        # refuse an unexpected verifier rather than silently changing trust roots.
        raise ValueError("Workspace signing secret does not match the active service")
    return autonomous_workspace_credential(
        HTTPAuthorizationCredentials(scheme="Bearer", credentials=token),
        settings,
    )
