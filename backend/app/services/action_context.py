"""Bounded control-surface context shared across Auto Runtime continuations.

The context identifies the resource and user intent that originated a turn.  It
is deliberately neither a workflow selector nor evidence that the resource
exists: models may use, supplement, or reject the suggested capabilities after
observing current state.
"""

from __future__ import annotations

import re
from collections.abc import Collection

PAGES_ACTION_CONTEXT_SCHEMA = "warehouse.pages-action-context.v1"
RESOURCE_ACTION_CONTEXT_SCHEMA = "warehouse.resource-action-context.v1"
ACTION_CONTEXT_SCHEMAS = frozenset({PAGES_ACTION_CONTEXT_SCHEMA, RESOURCE_ACTION_CONTEXT_SCHEMA})

_ACTION_KEY = re.compile(r"^[a-z][a-z0-9_.:-]{2,159}$")
_RESOURCE_TYPE = re.compile(r"^[a-z][a-z0-9_.:-]{1,127}$")
_RESOURCE_REF = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:@/-]{0,159}$")
_TOOL_NAME = re.compile(r"^[a-z][a-z0-9_]{2,127}$")


def _resource_reference(value: object) -> dict[str, str] | None:
    if not isinstance(value, dict):
        return None
    resource_type = str(value.get("resource_type") or "").strip()
    resource_ref = str(value.get("resource_ref") or "").strip()
    resource_version = str(value.get("resource_version") or "").strip()
    if not _RESOURCE_TYPE.fullmatch(resource_type):
        return None
    if not _RESOURCE_REF.fullmatch(resource_ref):
        return None
    if resource_version and not _RESOURCE_REF.fullmatch(resource_version):
        return None
    bounded = {"resource_type": resource_type, "resource_ref": resource_ref}
    if resource_version:
        bounded["resource_version"] = resource_version
    return bounded


def bounded_action_context(
    value: object,
    *,
    active_tool_names: Collection[str] | None = None,
) -> dict[str, object] | None:
    """Return a small non-authoritative resource hint, or reject it entirely."""

    if not isinstance(value, dict):
        return None
    schema = str(value.get("schema") or "").strip()
    if schema not in ACTION_CONTEXT_SCHEMAS:
        return None
    action_key = str(value.get("action_key") or "").strip()
    if not _ACTION_KEY.fullmatch(action_key):
        return None

    bounded: dict[str, object] = {"schema": schema, "action_key": action_key}
    if schema == PAGES_ACTION_CONTEXT_SCHEMA:
        workspace_ref = str(value.get("workspace_ref") or "").strip()
        deployment_id = str(value.get("deployment_id") or "").strip()
        if not _RESOURCE_REF.fullmatch(workspace_ref):
            return None
        if deployment_id and not _RESOURCE_REF.fullmatch(deployment_id):
            return None
        bounded["workspace_ref"] = workspace_ref
        if deployment_id:
            bounded["deployment_id"] = deployment_id
        bounded["resource_type"] = "digital_asset.workspace"
        bounded["resource_ref"] = workspace_ref
    else:
        primary = _resource_reference(value)
        if primary is None:
            return None
        bounded.update(primary)
        related: list[dict[str, str]] = []
        for item in value.get("related_resources") or []:
            reference = _resource_reference(item)
            if reference is not None and reference not in related:
                related.append(reference)
            if len(related) >= 4:
                break
        if related:
            bounded["related_resources"] = related

    active = {str(name) for name in active_tool_names} if active_tool_names is not None else None
    suggested: list[str] = []
    for item in value.get("suggested_tool_names") or []:
        name = str(item or "").strip()
        if not _TOOL_NAME.fullmatch(name) or (active is not None and name not in active):
            continue
        if name not in suggested:
            suggested.append(name)
        if len(suggested) >= 8:
            break
    bounded["suggested_tool_names"] = suggested
    bounded["trust_boundary"] = (
        "Control-surface resource and intent hint only; not live evidence, tool "
        "selection, authorization, workflow prescription or proof of completion."
    )
    return bounded
