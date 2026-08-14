"""Bounded control-surface context shared across Auto Runtime continuations.

The context identifies the resource and user intent that originated a turn.
Ordinary action context is deliberately neither a workflow selector nor
evidence that the resource exists.  A governed resource-operation context is a
stronger control-surface intent: it bounds which capabilities and resource
identity may be used, while remaining neither authorization nor live evidence.
"""

from __future__ import annotations

import re
from collections.abc import Collection

PAGES_ACTION_CONTEXT_SCHEMA = "warehouse.pages-action-context.v1"
RESOURCE_ACTION_CONTEXT_SCHEMA = "warehouse.resource-action-context.v1"
RESOURCE_OPERATION_CONTEXT_SCHEMA = "warehouse.resource-operation-context.v1"
ACTION_CONTEXT_SCHEMAS = frozenset(
    {
        PAGES_ACTION_CONTEXT_SCHEMA,
        RESOURCE_ACTION_CONTEXT_SCHEMA,
        RESOURCE_OPERATION_CONTEXT_SCHEMA,
    }
)

_ACTION_KEY = re.compile(r"^[a-z][a-z0-9_.:-]{2,159}$")
_RESOURCE_TYPE = re.compile(r"^[a-z][a-z0-9_.:-]{1,127}$")
_RESOURCE_REF = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:@/-]{0,159}$")
_TOOL_NAME = re.compile(r"^[a-z][a-z0-9_]{2,127}$")
_ARGUMENT_NAME = re.compile(r"^[a-z][a-z0-9_-]{0,63}$")
_ARGUMENT_VALUE = re.compile(r"^[^\x00\r\n]{1,240}$")


def _argument_map(value: object, *, limit: int = 8) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}
    bounded: dict[str, str] = {}
    for raw_key, raw_value in value.items():
        key = str(raw_key or "").strip()
        item = str(raw_value or "").strip()
        if not _ARGUMENT_NAME.fullmatch(key) or not _ARGUMENT_VALUE.fullmatch(item):
            continue
        bounded[key] = item
        if len(bounded) >= limit:
            break
    return bounded


def _argument_choices(value: object, *, limit: int = 8) -> dict[str, list[str]]:
    if not isinstance(value, dict):
        return {}
    bounded: dict[str, list[str]] = {}
    for raw_key, raw_values in value.items():
        key = str(raw_key or "").strip()
        if not _ARGUMENT_NAME.fullmatch(key) or not isinstance(raw_values, list):
            continue
        choices: list[str] = []
        for raw_value in raw_values:
            item = str(raw_value or "").strip()
            if _ARGUMENT_VALUE.fullmatch(item) and item not in choices:
                choices.append(item)
            if len(choices) >= 32:
                break
        if choices:
            bounded[key] = choices
        if len(bounded) >= limit:
            break
    return bounded


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
    if schema == RESOURCE_OPERATION_CONTEXT_SCHEMA:
        operation_tool_name = str(value.get("operation_tool_name") or "").strip()
        if not _TOOL_NAME.fullmatch(operation_tool_name):
            return None
        if active is not None and operation_tool_name not in active:
            return None
        observation_tool_names: list[str] = []
        for item in value.get("observation_tool_names") or []:
            name = str(item or "").strip()
            if not _TOOL_NAME.fullmatch(name) or (active is not None and name not in active):
                continue
            if name != operation_tool_name and name not in observation_tool_names:
                observation_tool_names.append(name)
            if len(observation_tool_names) >= 4:
                break
        resource_argument_name = str(value.get("resource_argument_name") or "id").strip()
        if not _ARGUMENT_NAME.fullmatch(resource_argument_name):
            return None
        defaults = _argument_map(value.get("operation_defaults"))
        choices = _argument_choices(value.get("operation_choices"))
        for key, default in defaults.items():
            if key in choices and default not in choices[key]:
                return None
        bounded.update(
            {
                "operation_tool_name": operation_tool_name,
                "observation_tool_names": observation_tool_names,
                "resource_argument_name": resource_argument_name,
                "operation_defaults": defaults,
                "operation_choices": choices,
                "trust_boundary": (
                    "Control-surface operation scope and immutable resource identity; "
                    "not live evidence, authorization or proof of completion. Capability "
                    "execution must still re-observe state and enforce permissions, "
                    "confirmation and transaction invariants."
                ),
            }
        )
    else:
        bounded["trust_boundary"] = (
            "Control-surface resource and intent hint only; not live evidence, tool "
            "selection, authorization, workflow prescription or proof of completion."
        )
    return bounded
