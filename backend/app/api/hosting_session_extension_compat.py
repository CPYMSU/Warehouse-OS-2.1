"""Keep the original intelligent-hosting dependency and function extension points."""

from __future__ import annotations

from fastapi import APIRouter, Body, Depends, HTTPException, Response, status

from app.api import intelligent_hosting as legacy
from app.core.config import Settings, get_settings
from app.services.intelligent_hosting import HostingPrincipal, credential_for_actor
from app.services.workspace_autonomy import provision_idempotently

router = APIRouter(tags=["intelligent-hosting-extension-compat"])


@router.post("/api/hosting/v2/sessions", status_code=status.HTTP_201_CREATED)
def intelligent_hosting_session_create(
    response: Response,
    payload: dict[str, object] = Body(default={}),
    principal: HostingPrincipal = Depends(legacy.hosting_principal),
    settings: Settings = Depends(get_settings),
) -> dict[str, object]:
    response.headers["Cache-Control"] = "no-store"
    one_time: dict[str, object] | None = None
    if principal.credential is not None:
        credential = principal.credential
    else:
        if principal.actor is None:
            raise HTTPException(status_code=401, detail="Account session is required")
        provision = payload.get("provision")
        if isinstance(provision, dict):
            provisioned = provision_idempotently(principal.actor, provision, settings)
            credential = credential_for_actor(
                principal.actor,
                provisioned["workspace"]["uuid"],
            )
            if provisioned.get("api_key"):
                one_time = {
                    "provisioned": {
                        key: provisioned.get(key)
                        for key in (
                            "asset",
                            "workspace",
                            "components",
                            "database",
                            "storage",
                        )
                    },
                    "credential": {
                        key: provisioned.get(key)
                        for key in (
                            "credential_id",
                            "key_id",
                            "key_kind",
                            "is_primary",
                            "label",
                            "api_key",
                            "api_key_hint",
                            "scopes",
                            "expires_at",
                            "base_url",
                            "plaintext_exposed_once",
                        )
                    },
                }
        else:
            workspace_ref = payload.get("workspace_ref")
            if workspace_ref in (None, ""):
                raise HTTPException(
                    status_code=422,
                    detail="workspace_ref or provision is required for an account session",
                )
            credential = credential_for_actor(principal.actor, workspace_ref)
    result = legacy.create_session(principal, credential, payload)
    if bool(payload.get("execute")):
        result = legacy.execute_message(
            principal,
            result["session"]["id"],
            {
                "message": str(payload.get("message") or payload.get("goal") or ""),
                "desired_state": payload.get("desired_state") or {},
                "execute": True,
            },
            settings,
        )
    if one_time is not None:
        result["one_time"] = one_time
    return result
