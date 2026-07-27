from __future__ import annotations

from pydantic import BaseModel, Field


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


class AgentRunRequest(BaseModel):
    text: str = Field(min_length=1, max_length=16_384)
    conversation_id: str | None = Field(default=None, max_length=128)


class WarehouseLineInput(BaseModel):
    name: str = Field(min_length=1, max_length=256)
    qty: float = Field(gt=0)
    unit: str | None = Field(default=None, max_length=32)
    production_date: str | None = Field(default=None, max_length=10)
    shelf_life_days: int | None = Field(default=None, ge=0, le=36_500)


class InboundCreateRequest(BaseModel):
    request_id: str | None = Field(default=None, max_length=160)
    lines: list[WarehouseLineInput] = Field(min_length=1, max_length=500)
    warehouse: str = Field(min_length=1, max_length=256)
    source: str | None = Field(default=None, max_length=256)
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
