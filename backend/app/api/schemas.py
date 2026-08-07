from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.services.action_context import (
    PAGES_ACTION_CONTEXT_SCHEMA,
    RESOURCE_ACTION_CONTEXT_SCHEMA,
)


class LoginRequest(BaseModel):
    # Kept optional for backwards compatibility; a password login is global
    # and the active company is selected only after authentication.
    tenant: str | None = Field(default=None, min_length=2, max_length=64)
    username: str = Field(min_length=1, max_length=128)
    password: str = Field(min_length=1, max_length=512)


class LoginResponse(BaseModel):
    token: str
    token_type: str = "bearer"
    tenant: str
    user: dict[str, object]
    companies: list[dict[str, object]] = Field(default_factory=list)
    default_tenant: str | None = None
    is_platform_owner: bool = False
    can_apply_company: bool = False


class TenantSwitchRequest(BaseModel):
    tenant: str = Field(min_length=2, max_length=64)


class CliExecuteRequest(BaseModel):
    line: str = Field(min_length=1, max_length=16_384)


class AiToolCallRequest(BaseModel):
    arguments: dict[str, object] = Field(default_factory=dict)


class AgentResourceReference(BaseModel):
    resource_type: str = Field(
        min_length=2,
        max_length=128,
        pattern=r"^[a-z][a-z0-9_.:-]*$",
    )
    resource_ref: str = Field(
        min_length=1,
        max_length=160,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._:@/-]*$",
    )
    resource_version: str | None = Field(
        default=None,
        min_length=1,
        max_length=160,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._:@/-]*$",
    )


class AgentActionContext(BaseModel):
    """Bounded presentation hint; never live evidence or authorization."""

    model_config = ConfigDict(populate_by_name=True)

    schema_: Literal[
        "warehouse.pages-action-context.v1",
        "warehouse.resource-action-context.v1",
    ] = Field(alias="schema")
    action_key: str = Field(
        min_length=3,
        max_length=160,
        pattern=r"^[a-z][a-z0-9_.:-]*$",
    )
    resource_type: str | None = Field(
        default=None,
        min_length=2,
        max_length=128,
        pattern=r"^[a-z][a-z0-9_.:-]*$",
    )
    resource_ref: str | None = Field(
        default=None,
        min_length=1,
        max_length=160,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._:@/-]*$",
    )
    resource_version: str | None = Field(
        default=None,
        min_length=1,
        max_length=160,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._:@/-]*$",
    )
    related_resources: list[AgentResourceReference] = Field(default_factory=list, max_length=4)
    workspace_ref: str | None = Field(
        default=None,
        min_length=1,
        max_length=160,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]*$",
    )
    deployment_id: str | None = Field(
        default=None,
        min_length=1,
        max_length=160,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]*$",
    )
    suggested_tool_names: list[str] = Field(default_factory=list, max_length=8)

    @model_validator(mode="after")
    def validate_schema_shape(self) -> AgentActionContext:
        if self.schema_ == PAGES_ACTION_CONTEXT_SCHEMA:
            if not self.workspace_ref or not self.action_key.startswith("pages."):
                raise ValueError("Pages action context requires a Pages action and workspace")
        elif self.schema_ == RESOURCE_ACTION_CONTEXT_SCHEMA:
            if not self.resource_type or not self.resource_ref:
                raise ValueError("Resource action context requires a typed resource reference")
        return self


class AgentRunRequest(BaseModel):
    text: str = Field(min_length=1, max_length=16_384)
    conversation_id: str | None = Field(default=None, max_length=128)
    turn_id: str | None = Field(default=None, min_length=1, max_length=128)
    # A surface identifies presentation context only.  It never selects a
    # different model, command set, planner, or execution path.
    surface: str = Field(default="assistant", min_length=1, max_length=64)
    # The presentation may request a fast or deliberative inference policy,
    # but both modes still enter the same shared Auto Runtime and capability
    # gateway.
    context_mode: Literal["balanced", "thinking"] = "balanced"
    # Canonical UI/account locale. In auto mode a strong language signal in
    # the current turn may override it; fixed mode always honours this value.
    locale: Literal["zh-Hant", "zh-Hans", "en"] | None = None
    language_mode: Literal["auto", "fixed"] = "auto"
    # A control-surface action may expose a bounded catalogue hint. The
    # Runtime still judges freely, reloads live state and enforces capability
    # permission/confirmation contracts at execution time.
    action_context: AgentActionContext | None = None
    # A confirmation card only issues this opaque, one-use authorization
    # signal. The shared Runtime consumes it; the card endpoint never invokes
    # a business adapter directly.
    resume_confirmation_action_id: int | None = Field(default=None, ge=1)
    authorization_keychain_id: str | None = Field(default=None, max_length=128)
    hidden_user_turn: bool = False
    terminal_event: bool = False


class WarehouseLineInput(BaseModel):
    name: str = Field(min_length=1, max_length=256)
    qty: float = Field(gt=0)
    unit: str | None = Field(default=None, max_length=32)
    batch: str | None = Field(default=None, max_length=160)
    production_date: str | None = Field(default=None, max_length=10)
    shelf_life_days: int | None = Field(default=None, ge=0, le=36_500)
    expire_at: str | None = Field(default=None, max_length=10)
    purchase_order_line_id: int | None = Field(default=None, ge=1)


class InboundCreateRequest(BaseModel):
    request_id: str | None = Field(default=None, max_length=160)
    purchase_order_id: int | None = Field(default=None, ge=1)
    lines: list[WarehouseLineInput] = Field(min_length=1, max_length=500)
    warehouse: str | None = Field(default=None, min_length=1, max_length=256)
    source: str | None = Field(default=None, max_length=256)
    handler: str | None = Field(default=None, max_length=256)
    type: str | None = Field(default=None, max_length=80)


class OutboundCreateRequest(BaseModel):
    request_id: str | None = Field(default=None, max_length=160)
    lines: list[WarehouseLineInput] = Field(min_length=1, max_length=500)
    use: str | None = Field(default=None, max_length=80)
    dept: str | None = Field(default=None, max_length=256)
    target: str | None = Field(default=None, max_length=256)
    urgent: bool = False


class ReplenishmentRequest(BaseModel):
    item_name: str = Field(min_length=1, max_length=256)
    need: float = Field(gt=0)
    unit: str | None = Field(default=None, max_length=32)
    stock: float | None = None
    safe: float | None = None


class ShipmentDispatchRequest(BaseModel):
    item: str = Field(min_length=1, max_length=256)
    qty: float = Field(gt=0)
    to: str = Field(min_length=1, max_length=256)
    from_: str | None = Field(default=None, alias="from", max_length=256)


class ShipmentActionRequest(BaseModel):
    shipment_no: str = Field(min_length=1, max_length=96)
