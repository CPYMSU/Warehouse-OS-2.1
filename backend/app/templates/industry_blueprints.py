#!/usr/bin/env python3
"""Versioned industry organisation blueprints.

This module is the single source of truth (SSOT) for the organisation that is
created when a tenant selects an industry template.  It deliberately has no
database or ``ai_service`` dependency, so migrations, APIs and tests can all
consume the same deterministic data.

Public getters always return a deep copy.  Callers may therefore add database
ids, edit names, or prepare a diff without mutating the process-wide defaults.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Iterable, Mapping, Optional


BLUEPRINT_SCHEMA_VERSION = 1
BLUEPRINT_DATA_VERSION = "2026.08.01.1"
DEFAULT_BLUEPRINT_KEY = "generic_warehouse"

# The built-in application permissions that organisation templates may grant.
# CLI capabilities are intentionally not included: a blueprint must never grant
# an arbitrary command capability merely because a tenant selected an industry.
BLUEPRINT_PERMISSION_KEYS = frozenset(
    {
        "overview.read",
        "alerts.read",
        "erp.read",
        "finance.read",
        "finance.write",
        "reports.read",
        "terminal.use",
        "browser.read",
        "browser.run",
        "inventory.read",
        "inventory.import",
        "inventory.inbound",
        "inventory.outbound",
        "inventory.shipment",
        "inventory.adjust",
        "ledger.read",
        "ledger.write",
        "approval.review",
        "gis.read",
        "gis.locate",
        "gis.manage",
        "gis.ai_delegate",
        "settings.manage",
        "users.manage",
        "permissions.topology.read",
        "permissions.topology.manage",
        "permissions.delegate",
        "ai.use",
        "ai.write",
        "audit.read",
        "procurement.workflow.use",
        "procurement.workflow.approve",
        "procurement.workflow.admin",
        "procurement.workflow.external",
        "procurement.workflow.global.read",
        "procurement.workflow.global.act",
        "procurement.workflow.global.reassign",
        "legal.manage",
        "assets.read",
        "assets.manage",
        "asset_mgmt.read",
        "asset_mgmt.manage",
        "asset_mgmt.trade",
        "research.read",
        "research.write",
        "research.review",
        "cases.read",
        "cases.create",
        "cases.process",
        "cases.assign",
        "cases.close",
        "cases.analytics.read",
        "cases.config.manage",
        "cases.all.manage",
        "records.read",
        "records.create",
        "records.edit",
        "records.archive",
        "records.config.manage",
        "records.all.manage",
        "records.cli.manage",
        "tasks.read",
        "tasks.create",
        "tasks.assign",
        "tasks.manage",
    }
)

VALID_DEPARTMENT_TYPES = frozenset({"company", "department", "team", "project", "other"})

# Raw SQL remains a governed exception, not a replacement for business APIs.
# These are the only native application-data domains a position blueprint may
# name.  Every position also receives its own ``department:<code>`` extension
# namespace so a manager can add business-specific tables without crossing an
# organisational boundary.
DB_NATIVE_DOMAINS = frozenset(
    {"inventory", "finance", "procurement", "legal", "assets", "operations"}
)

# The mapping is deliberately explicit, including departments that do not yet
# own a native application table family.  An empty tuple means that the
# department is limited to its own extension namespace until a core table
# family is formally classified by the SQL policy.
DB_DEPARTMENT_NATIVE_DOMAINS: dict[str, tuple[str, ...]] = {
    "management": (),
    "warehouse_ops": ("inventory",),
    "procurement": ("procurement",),
    "finance": ("finance",),
    "hr_admin": (),
    "marketing_customer": (),
    "production_maintenance": ("inventory",),
    "dispatch_safety": (),
    "procurement_warehouse": ("procurement", "inventory"),
    "legal_compliance": ("legal",),
    "research_technology": ("operations",),
    "manufacturing_production": ("inventory",),
    "quality": (),
    "equipment": ("inventory",),
    "project_management": ("operations",),
    "construction_engineering": ("inventory", "operations"),
    "safety_quality": (),
    "materials_warehouse": ("inventory", "procurement"),
    "procurement_contracts": ("procurement", "legal"),
    "front_service": (),
    "kitchen": ("inventory",),
    "food_safety": (),
    "clinical": (),
    "nursing": (),
    "pharmacy_supplies": ("inventory",),
    "equipment_sterilization": ("inventory",),
    "hr_admin_compliance": ("legal",),
    "store_operations": ("inventory",),
    "merchandising": ("inventory",),
    "warehouse_replenishment": ("inventory", "procurement"),
    "operations_dispatch": ("inventory", "operations"),
    "sorting_warehouse": ("inventory",),
    "fleet_equipment": ("inventory",),
    "customer_service": (),
    "research": (),
    "lab_operations": ("inventory",),
    "safety_compliance": ("legal",),
    "front_office": (),
    "housekeeping": ("inventory",),
    "food_beverage": ("inventory",),
    "hotel_engineering": ("inventory",),
    "it_operations": ("operations",),
    "information_security": ("operations",),
    "asset_warehouse": ("inventory",),
    "film_production": (),
    "camera": (),
    "lighting": (),
    "props_warehouse": ("inventory",),
}

# Native-domain visibility is broader than raw-write ownership.  Operational
# departments may inspect inventory relevant to their work, while only the
# departments that own that master data can change it with governed SQL.
DB_DEPARTMENT_NATIVE_WRITE_DOMAINS: dict[str, tuple[str, ...]] = {
    "warehouse_ops": ("inventory",),
    "procurement": ("procurement",),
    "finance": ("finance",),
    "procurement_warehouse": ("procurement", "inventory"),
    "legal_compliance": ("legal",),
    "materials_warehouse": ("inventory",),
    "procurement_contracts": ("procurement", "legal"),
    "pharmacy_supplies": ("inventory",),
    "store_operations": ("inventory",),
    "warehouse_replenishment": ("inventory",),
    "sorting_warehouse": ("inventory",),
    "asset_warehouse": ("inventory",),
    "props_warehouse": ("inventory",),
    "hr_admin_compliance": ("legal",),
    "safety_compliance": ("legal",),
}

# Position permissions are the durable description of a job's actual business
# responsibility.  Keep the translation explicit: a new permission never
# acquires raw database scope merely because its name happens to contain a
# familiar word.
DB_PERMISSION_READ_DOMAINS: dict[str, frozenset[str]] = {
    "inventory": frozenset(
        {
            "inventory.read",
            "inventory.import",
            "inventory.inbound",
            "inventory.outbound",
            "inventory.adjust",
            "ledger.read",
            "ledger.write",
        }
    ),
    "finance": frozenset({"finance.read", "finance.write"}),
    "procurement": frozenset(
        {
            # use/approve are row-scoped workflow abilities shared by many
            # departments.  They must stay behind the procurement API and do
            # not imply whole-table SQL visibility.
            "procurement.workflow.admin",
            "procurement.workflow.external",
            "procurement.workflow.global.read",
            "procurement.workflow.global.act",
            "procurement.workflow.global.reassign",
        }
    ),
    # legal.manage is shared with finance/marketing/HR workflows.  Whole-table
    # legal SQL visibility comes from the explicit owning department map.
    "legal": frozenset(),
    "assets": frozenset(
        {
            "assets.read",
            "assets.manage",
            "asset_mgmt.read",
            "asset_mgmt.manage",
            "asset_mgmt.trade",
        }
    ),
    # ``operations`` is intentionally department-mapped only until a concrete
    # application permission and native table family are registered together.
    "operations": frozenset(),
}

# Raw write/schema scope has a higher bar than visibility.  These capabilities
# describe a manager who is already responsible for changing the corresponding
# business data.  ``is_manager`` is still required by :func:`_database_access`;
# an operator with the same application permission remains business-API-only.
DB_MANAGER_WRITE_CAPABILITY_DOMAINS: dict[str, frozenset[str]] = {
    "inventory": frozenset(
        {
            "inventory.import",
            "inventory.inbound",
            "inventory.outbound",
            "inventory.adjust",
            "ledger.write",
        }
    ),
    "finance": frozenset({"finance.write"}),
    "procurement": frozenset(
        {
            # Department-wide approval is shared by many supervisors and does
            # not make them procurement-data owners.  Administration/external
            # sourcing (or an explicit department ownership map) is required.
            "procurement.workflow.admin",
            "procurement.workflow.external",
            "procurement.workflow.global.act",
            "procurement.workflow.global.reassign",
        }
    ),
    # legal.manage is intentionally broad (finance, marketing and procurement
    # roles use the governed legal API).  Raw schema/write ownership therefore
    # comes only from the explicit department map above.
    "legal": frozenset(),
    "assets": frozenset({"assets.manage", "asset_mgmt.manage", "asset_mgmt.trade"}),
    "operations": frozenset(),
}


def _domains_for_permissions(
    permissions: Iterable[str],
    domain_capabilities: Mapping[str, Iterable[str]],
) -> set[str]:
    """Translate an explicit permission set through an explicit domain map."""

    permission_set = {
        str(permission).strip() for permission in (permissions or ()) if str(permission).strip()
    }
    return {
        domain
        for domain, capabilities in domain_capabilities.items()
        if permission_set.intersection(capabilities)
    }


def _database_access(
    department: str,
    role_name: str,
    is_manager: bool,
    permissions: Iterable[str],
    access_mode: Optional[str] = None,
) -> dict[str, Any]:
    """Return deterministic, duty-derived appointment DB access metadata."""

    if role_name == "系統管理員" and access_mode == "tenant_scoped":
        department_domain = f"department:{department}"
        return {
            "read": [department_domain],
            "write": [department_domain],
            "schema": [department_domain],
            "business_write": True,
            "source": "tenant_scoped_system_admin",
        }

    if role_name == "系統管理員":
        return {
            "read": ["*"],
            "write": ["*"],
            "schema": ["*"],
            "business_write": True,
            "source": "system_admin",
        }

    department_domain = f"department:{department}"
    if department == "management":
        # Executives may analyse the whole company, while raw writes and DDL
        # remain confined to management-owned extension objects.
        read_domains = set(DB_NATIVE_DOMAINS)
        read_domains.add(department_domain)
        write_domains = {department_domain} if is_manager else set()
        source = "executive"
    else:
        native_domains = set(DB_DEPARTMENT_NATIVE_DOMAINS.get(department, ()))
        native_domains.update(_domains_for_permissions(permissions, DB_PERMISSION_READ_DOMAINS))
        read_domains = native_domains | {department_domain}
        native_write_domains = set(DB_DEPARTMENT_NATIVE_WRITE_DOMAINS.get(department, ()))
        if is_manager:
            native_write_domains.update(
                _domains_for_permissions(permissions, DB_MANAGER_WRITE_CAPABILITY_DOMAINS)
            )
        write_domains = native_write_domains | {department_domain} if is_manager else set()
        source = "department_manager" if is_manager else "department_member"

    return {
        "read": sorted(read_domains),
        "write": sorted(write_domains),
        "schema": sorted(write_domains),
        "business_write": True,
        "source": source,
    }


def _permissions(*groups: Iterable[str]) -> tuple[str, ...]:
    return tuple(sorted({permission for group in groups for permission in group}))


_BASE_USER = _permissions(
    (
        "overview.read",
        "alerts.read",
        "ai.use",
        "cases.read",
        "cases.create",
        "cases.process",
        "records.read",
        "records.create",
        "tasks.read",
        "tasks.create",
    )
)
_BUSINESS_USER = _permissions(_BASE_USER, ("erp.read",))
_DEPARTMENT_MANAGER = _permissions(
    _BUSINESS_USER,
    (
        "reports.read",
        "approval.review",
        "permissions.delegate",
        "procurement.workflow.use",
        "procurement.workflow.approve",
        "cases.assign",
        "cases.close",
        "cases.analytics.read",
        "records.edit",
        "records.archive",
        "tasks.assign",
    ),
)
_INVENTORY_VIEWER = _permissions(
    _BASE_USER,
    ("inventory.read", "ledger.read", "gis.read"),
)
_INVENTORY_OPERATOR = _permissions(
    _INVENTORY_VIEWER,
    (
        "inventory.inbound",
        "inventory.outbound",
        "inventory.shipment",
        "ledger.write",
        "gis.locate",
        "procurement.workflow.use",
    ),
)
_RESEARCH_EDITOR = _permissions(("research.read", "research.write"))
_RESEARCH_REVIEWER = _permissions(_RESEARCH_EDITOR, ("research.review",))
_WAREHOUSE_MANAGER = _permissions(
    _INVENTORY_OPERATOR,
    (
        "inventory.import",
        "inventory.adjust",
        "approval.review",
        "reports.read",
        "audit.read",
        "ai.write",
        "gis.manage",
        "gis.ai_delegate",
        "procurement.workflow.approve",
        "permissions.delegate",
    ),
)
_PROCUREMENT_USER = _permissions(
    _BUSINESS_USER,
    ("inventory.read", "ledger.read", "procurement.workflow.use"),
)
_PROCUREMENT_WORKFLOW_OPERATOR = _permissions(
    ("procurement.workflow.use", "inventory.adjust"),
)
_PROCUREMENT_MANAGER = _permissions(
    _PROCUREMENT_USER,
    (
        "inventory.adjust",
        "reports.read",
        "approval.review",
        "procurement.workflow.approve",
        "procurement.workflow.external",
        "permissions.delegate",
    ),
)
_FINANCE_USER = _permissions(
    _BUSINESS_USER,
    ("finance.read", "finance.write", "reports.read"),
)
_FINANCE_MANAGER = _permissions(
    _FINANCE_USER,
    (
        "approval.review",
        "audit.read",
        "legal.manage",
        "permissions.delegate",
        "procurement.workflow.use",
        "procurement.workflow.approve",
    ),
)
_HR_USER = _permissions(
    _BUSINESS_USER,
    ("reports.read", "permissions.topology.read"),
)
_HR_MANAGER = _permissions(
    _HR_USER,
    (
        "approval.review",
        "permissions.delegate",
        "audit.read",
        "procurement.workflow.use",
        "procurement.workflow.approve",
    ),
)
_EXECUTIVE = _permissions(
    _DEPARTMENT_MANAGER,
    (
        "inventory.read",
        "ledger.read",
        "finance.read",
        "audit.read",
        "procurement.workflow.use",
        "procurement.workflow.approve",
        "procurement.workflow.global.read",
        "procurement.workflow.global.act",
        "procurement.workflow.global.reassign",
        "legal.manage",
        "assets.read",
        "asset_mgmt.read",
        "research.read",
        "research.review",
        "cases.all.manage",
        "cases.config.manage",
        "records.all.manage",
        "records.config.manage",
        "tasks.manage",
    ),
)
# System administrators may configure and inspect workflows, but a technical
# administrator is not a business approver.  Cross-department action and
# reassignment must come from the current executive position (or an explicit,
# auditable grant), never from the system-admin title itself.
_SYSTEM_ADMIN = tuple(
    sorted(
        BLUEPRINT_PERMISSION_KEYS
        - {
            "procurement.workflow.global.act",
            "procurement.workflow.global.reassign",
        }
    )
)
_CASE_DEPARTMENT_MANAGER = _permissions(
    (
        "cases.read",
        "cases.create",
        "cases.process",
        "cases.assign",
        "cases.close",
        "cases.analytics.read",
    )
)
_CASE_COMPANY_MANAGER = _permissions(
    _CASE_DEPARTMENT_MANAGER,
    ("cases.all.manage", "cases.config.manage"),
)

# BIU is a non-operational academic tenant.  These permission groups are kept
# deliberately separate from ``_BASE_USER`` and ``_DEPARTMENT_MANAGER`` so a
# legal-education position never inherits warehouse, procurement, finance or
# contract/seal capabilities.
_BIU_MEMBER = _permissions(
    (
        "overview.read",
        "ai.use",
        "cases.read",
        "records.read",
        "tasks.read",
    )
)
_BIU_DIRECT_CONTRIBUTOR = _permissions(
    _BIU_MEMBER,
    ("tasks.create", "records.create"),
)
_BIU_CONTRIBUTOR = _permissions(
    _BIU_MEMBER,
    ("tasks.create", "records.create", "records.edit"),
)
_BIU_CASE_ACTOR = _permissions(
    _BIU_CONTRIBUTOR,
    ("cases.process",),
)
_BIU_CASE_ADMINISTRATOR = _permissions(
    _BIU_CASE_ACTOR,
    (
        "cases.create",
        "cases.assign",
        "cases.close",
        "cases.analytics.read",
        "records.archive",
        "tasks.assign",
        "audit.read",
    ),
)
_BIU_ARCHIVE_REVIEWER = _permissions(
    _BIU_CONTRIBUTOR,
    ("records.archive", "audit.read"),
)
_BIU_ACADEMIC_GOVERNANCE = _permissions(
    _BIU_MEMBER,
    (
        "cases.analytics.read",
        "records.config.manage",
        "tasks.manage",
        "users.manage",
        "permissions.topology.read",
        "permissions.topology.manage",
        "permissions.delegate",
        "audit.read",
    ),
)
_BIU_SYSTEM_ADMIN = _permissions(
    _BIU_ACADEMIC_GOVERNANCE,
    _BIU_CASE_ADMINISTRATOR,
    _BIU_ARCHIVE_REVIEWER,
    (
        "cases.all.manage",
        "cases.config.manage",
        "records.all.manage",
        "records.cli.manage",
        "settings.manage",
    ),
)

BIU_TEMPLATE_KEY = "biu_legal_ethics_case_lab"
BIU_ENTRY_MODES = frozenset({"direct", "application", "exam", "appointment"})
BIU_CATALOG_VISIBILITIES = frozenset({"public", "locked", "hidden"})
BIU_PERMISSION_TIERS = frozenset({"P0", "P1", "P2", "P3", "P4", "P5"})
BIU_QUICK_REGISTRATION_TIERS = frozenset({"P0", "P1"})
BIU_QUICK_REGISTRATION_ALLOWED_PERMISSIONS = frozenset(
    {
        # Quick entry may use only the row-scoped academic collaboration surface.
        # Keeping this as a positive allowlist prevents a future template edit from
        # silently turning open registration into an unrelated tenant capability.
        "overview.read",
        "ai.use",
        "cases.read",
        "records.read",
        "records.create",
        "tasks.read",
        "tasks.create",
    }
)
BIU_DIRECT_ENTRY_FORBIDDEN_PERMISSIONS = frozenset(
    {
        "ai.write",
        "audit.read",
        "cases.process",
        "cases.assign",
        "cases.close",
        "cases.config.manage",
        "cases.all.manage",
        "records.archive",
        "records.config.manage",
        "records.all.manage",
        "records.cli.manage",
        "tasks.assign",
        "tasks.manage",
        "users.manage",
        "permissions.topology.manage",
        "permissions.delegate",
        "settings.manage",
    }
)

# Warehouse 2.0 navigation rules, in the exact order used by the live shell.
# Keeping the permission rule beside the id lets industry defaults be derived
# from capability families instead of repeating a navigation list on every one
# of the 176 built-in positions.
V2_NAV_MODULE_RULES = (
    ("tasks", ("tasks.read",), ()),
    ("dashboard", ("overview.read",), ()),
    ("inventory", ("inventory.read",), ()),
    ("inbound", ("inventory.read", "inventory.inbound"), ()),
    ("outbound", ("inventory.read", "inventory.outbound"), ()),
    ("shipments", ("inventory.read",), ()),
    ("alerts", ("alerts.read",), ()),
    ("stocktake", ("inventory.read",), ()),
    ("erp", ("erp.read",), ()),
    ("finance", ("finance.read",), ()),
    ("assets", (), ("assets.read", "asset_mgmt.read")),
    ("research", (), ("research.read", "research.write", "research.review")),
    ("procurement", ("procurement.workflow.use",), ()),
    ("legal", ("legal.manage",), ()),
    ("gis", ("gis.read",), ()),
    ("reports", ("reports.read",), ()),
    (
        "perms",
        (),
        (
            "permissions.topology.read",
            "users.manage",
            "permissions.topology.manage",
            "settings.manage",
        ),
    ),
    ("logs", ("audit.read",), ()),
    ("cases", (), ("cases.read", "records.read")),
    ("civilization", ("overview.read",), ()),
    ("settings", ("settings.manage",), ()),
    ("terminal", ("terminal.use",), ()),
)
V2_NAV_MODULE_IDS = frozenset(rule[0] for rule in V2_NAV_MODULE_RULES)
_DEFAULT_ENABLED_MODULES = tuple(rule[0] for rule in V2_NAV_MODULE_RULES)


def nav_modules_for_permissions(permission_keys: Iterable[str]) -> list[str]:
    """Return the Warehouse 2.0 modules unlocked by ``permission_keys``.

    Unknown permission keys are harmless and ignored.  The returned order is
    deterministic and always matches :data:`V2_NAV_MODULE_RULES`.
    """
    permissions = {
        str(permission).strip() for permission in (permission_keys or ()) if str(permission).strip()
    }
    modules: list[str] = []
    for module_id, required_all, required_any in V2_NAV_MODULE_RULES:
        if not set(required_all).issubset(permissions):
            continue
        if required_any and not permissions.intersection(required_any):
            continue
        modules.append(module_id)
    return modules


def _department(
    code: str,
    name: str,
    description: str,
    *,
    parent: Optional[str] = "company",
    unit_type: str = "department",
) -> dict[str, Any]:
    return {
        "code": code,
        "name": name,
        "parent": parent,
        "type": unit_type,
        "description": description,
    }


def _company(name: str = "本公司") -> dict[str, Any]:
    return _department(
        "company",
        name,
        "公司組織根節點；實際公司名稱由租戶資料覆蓋。",
        parent=None,
        unit_type="company",
    )


def _position(
    code: str,
    name: str,
    department: str,
    role_name: str,
    level: int,
    is_manager: bool,
    *permission_groups: Iterable[str],
    database_access_mode: Optional[str] = None,
    automatic_task_grants: bool = True,
) -> dict[str, Any]:
    automatic_case_permissions = (
        _CASE_COMPANY_MANAGER if level >= 9 else _CASE_DEPARTMENT_MANAGER if is_manager else ()
    )
    automatic_task_permissions = ()
    if automatic_task_grants:
        automatic_task_permissions = (
            ("tasks.read", "tasks.create", "tasks.assign", "tasks.manage")
            if level >= 9
            else ("tasks.read", "tasks.create", "tasks.assign")
            if is_manager
            else ("tasks.read", "tasks.create")
        )
    permissions = _permissions(
        *permission_groups,
        automatic_case_permissions,
        automatic_task_permissions,
    )
    position = {
        "code": code,
        "name": name,
        "department": department,
        "role_name": role_name,
        "level": level,
        "is_manager": is_manager,
        "permissions": list(permissions),
        "database_access": _database_access(
            department,
            role_name,
            is_manager,
            permissions,
            database_access_mode,
        ),
    }
    if database_access_mode is not None:
        position["database_access_mode"] = database_access_mode
    return position


def _biu_department(
    code: str,
    name: str,
    name_en: str,
    description: str,
    *,
    parent: Optional[str] = "company",
    unit_type: str = "department",
) -> dict[str, Any]:
    """Build a BIU department with the bilingual public-catalogue identity.

    ``code`` is deliberately shared by the public website, blueprint and
    ``erp_org_units.unit_code``.  Keeping the English display name as metadata
    avoids introducing a second website-only department catalogue.
    """

    department = _department(
        code,
        name,
        description,
        parent=parent,
        unit_type=unit_type,
    )
    department["name_en"] = name_en
    return department


_BIU_ENTRY_DEFAULTS: dict[str, dict[str, Any]] = {
    "direct": {
        "visibility": "public",
        "requirements": ["注册 BIU 账户", "同意学术伦理与隐私规则"],
        "workflow_ref": None,
    },
    "application": {
        "visibility": "public",
        "requirements": ["注册 BIU 账户", "提交职位申请", "通过部门审核"],
        "workflow_ref": "biu_role_credential_application",
    },
    "exam": {
        "visibility": "locked",
        "requirements": ["注册 BIU 账户", "通过相关资格考试", "完成利益冲突声明"],
        "workflow_ref": "biu_role_credential_exam",
    },
    "appointment": {
        "visibility": "locked",
        "requirements": ["具备相关岗位经历", "通过学术治理机构任命"],
        "workflow_ref": "biu_role_appointment",
    },
}


def _biu_position(
    code: str,
    name: str,
    name_en: str,
    department: str,
    level: int,
    permission_tier: str,
    entry_mode: str,
    summary: str,
    *permission_groups: Iterable[str],
    is_manager: bool = False,
    visibility: Optional[str] = None,
    requirements: Optional[Iterable[str]] = None,
    workflow_ref: Optional[str] = None,
    case_roles: Iterable[str] = (),
    system_admin: bool = False,
    quick_registration: bool = False,
    guest_enabled: bool = False,
) -> dict[str, Any]:
    """Build one permanent BIU job and its 1:1 public catalogue metadata.

    Permanent positions describe a participant's long-lived academic job.
    ``case_roles`` are discovery hints only; a concrete role is still assigned
    separately for each case and never grants permissions by itself.
    """

    if entry_mode not in _BIU_ENTRY_DEFAULTS:
        raise ValueError(f"unknown BIU entry mode {entry_mode!r}")
    defaults = _BIU_ENTRY_DEFAULTS[entry_mode]
    role_name = "系統管理員" if system_admin else f"BIU · {name}"
    position = _position(
        code,
        name,
        department,
        role_name,
        level,
        is_manager,
        *permission_groups,
        database_access_mode="tenant_scoped" if system_admin else None,
        # BIU declares each academic task capability explicitly.  Automatic
        # Warehouse task grants would make a future public position broader
        # than its reviewed quick-registration allowlist.
        automatic_task_grants=False,
    )
    resolved_workflow = defaults["workflow_ref"] if workflow_ref is None else workflow_ref
    position.update(
        {
            "name_en": name_en,
            "permission_tier": permission_tier,
            "public_entry": {
                "mode": entry_mode,
                "visibility": visibility or str(defaults["visibility"]),
                "summary": summary,
                "requirements": list(
                    defaults["requirements"] if requirements is None else requirements
                ),
                "workflow_ref": resolved_workflow,
                # These flags are authorization policy, not UI inference.  A
                # public client may display them, but only the exact BIU
                # service re-resolves and enforces them against live RBAC.
                "quick_registration": bool(quick_registration),
                "guest_enabled": bool(guest_enabled),
            },
            "case_roles": list(case_roles),
        }
    )
    return position


def _blueprint(
    key: str,
    name: str,
    description: str,
    departments: list[dict[str, Any]],
    positions: list[dict[str, Any]],
    *,
    enabled_modules: Iterable[str] = _DEFAULT_ENABLED_MODULES,
    admin_position_code: Optional[str] = None,
) -> dict[str, Any]:
    if admin_position_code is None:
        admin_positions = [p for p in positions if p.get("role_name") == "系統管理員"]
        if len(admin_positions) != 1:
            raise ValueError(f"blueprint {key!r} must define exactly one 系統管理員 position")
        admin_position_code = str(admin_positions[0]["code"])
    return {
        "key": key,
        "name": name,
        "description": description,
        "schema_version": BLUEPRINT_SCHEMA_VERSION,
        "revision": BLUEPRINT_DATA_VERSION,
        "departments": departments,
        "positions": positions,
        "admin_position_code": admin_position_code,
        "enabled_modules": list(enabled_modules),
    }


_BLUEPRINTS: dict[str, dict[str, Any]] = {}


_BLUEPRINTS["generic_warehouse"] = _blueprint(
    "generic_warehouse",
    "通用倉儲",
    "適用於一般企業的採購、出入庫、盤點、財務與行政協作。",
    [
        _company(),
        _department("management", "管理層", "公司決策、跨部門審批與經營分析。"),
        _department("warehouse_ops", "倉儲運營", "收貨、上架、出庫、盤點與庫位管理。"),
        _department("procurement", "採購", "需求匯總、詢比價、招標與供應商協作。"),
        _department("finance", "財務", "會計核算、資金、預算與財務報表。"),
        _department("hr_admin", "人事行政", "人員、權限申請與公司行政。"),
    ],
    [
        _position("general_manager", "總經理", "management", "總經理", 9, True, _EXECUTIVE),
        _position(
            "deputy_general_manager", "副總經理", "management", "副總經理", 8, True, _EXECUTIVE
        ),
        _position(
            "system_admin", "系統管理員", "management", "系統管理員", 10, True, _SYSTEM_ADMIN
        ),
        _position(
            "warehouse_manager",
            "倉儲主管",
            "warehouse_ops",
            "倉儲主管",
            6,
            True,
            _WAREHOUSE_MANAGER,
        ),
        _position(
            "warehouse_clerk",
            "出入庫管理員",
            "warehouse_ops",
            "出入庫管理員",
            3,
            False,
            _INVENTORY_OPERATOR,
        ),
        _position(
            "inventory_auditor",
            "盤點員",
            "warehouse_ops",
            "盤點員",
            3,
            False,
            _INVENTORY_VIEWER,
            ("inventory.adjust", "audit.read"),
        ),
        _position(
            "procurement_manager",
            "採購主管",
            "procurement",
            "採購主管",
            6,
            True,
            _PROCUREMENT_MANAGER,
        ),
        _position(
            "buyer",
            "採購專員",
            "procurement",
            "採購專員",
            4,
            False,
            _PROCUREMENT_USER,
            _PROCUREMENT_WORKFLOW_OPERATOR,
        ),
        _position("finance_manager", "財務主管", "finance", "財務主管", 7, True, _FINANCE_MANAGER),
        _position("accountant", "會計", "finance", "會計", 4, False, _FINANCE_USER),
        _position(
            "hr_admin_manager", "人事行政主管", "hr_admin", "人事行政主管", 6, True, _HR_MANAGER
        ),
        _position(
            "hr_admin_specialist", "人事行政專員", "hr_admin", "人事行政專員", 3, False, _HR_USER
        ),
    ],
)


_BLUEPRINTS["hotel_homestay"] = _blueprint(
    "hotel_homestay",
    "酒店民宿",
    "覆蓋前臺、房務、餐飲、工程、採購倉儲、財務與人事行政的酒店組織。",
    [
        _company(),
        _department("management", "管理層", "酒店經營決策、服務品質與跨部門協調。"),
        _department("front_office", "前臺", "預訂、入住退房、賓客服務與交班。"),
        _department("housekeeping", "房務", "客房清潔、布草、迷你吧與房態協作。"),
        _department("food_beverage", "餐飲", "餐廳、宴會、後廚與餐飲物資管理。"),
        _department("hotel_engineering", "工程", "設施設備巡檢、維修與工程備件管理。"),
        _department("procurement_warehouse", "採購倉儲", "採購、收貨、庫存、發料與供應商協作。"),
        _department("finance", "財務", "酒店收入、應收應付、成本、預算與報表。"),
        _department("hr_admin", "人事行政", "招聘、排班支持、培訓與行政管理。"),
    ],
    [
        _position(
            "hotel_general_manager", "酒店總經理", "management", "酒店總經理", 9, True, _EXECUTIVE
        ),
        _position(
            "hotel_deputy_general_manager",
            "酒店副總經理",
            "management",
            "酒店副總經理",
            8,
            True,
            _EXECUTIVE,
        ),
        _position(
            "hotel_system_admin", "系統管理員", "management", "系統管理員", 10, True, _SYSTEM_ADMIN
        ),
        _position(
            "front_office_manager",
            "前臺經理",
            "front_office",
            "前臺經理",
            6,
            True,
            _DEPARTMENT_MANAGER,
        ),
        _position("receptionist", "前臺接待", "front_office", "前臺接待", 3, False, _BUSINESS_USER),
        _position(
            "housekeeping_manager",
            "房務經理",
            "housekeeping",
            "房務經理",
            6,
            True,
            _INVENTORY_VIEWER,
            _DEPARTMENT_MANAGER,
        ),
        _position(
            "room_attendant",
            "客房服務員",
            "housekeeping",
            "客房服務員",
            2,
            False,
            _INVENTORY_VIEWER,
            ("inventory.outbound",),
        ),
        _position(
            "food_beverage_manager",
            "餐飲經理",
            "food_beverage",
            "餐飲經理",
            6,
            True,
            _INVENTORY_VIEWER,
            _DEPARTMENT_MANAGER,
        ),
        _position(
            "hotel_restaurant_storekeeper",
            "餐飲庫管員",
            "food_beverage",
            "餐飲庫管員",
            3,
            False,
            _INVENTORY_OPERATOR,
        ),
        _position(
            "hotel_engineering_manager",
            "工程經理",
            "hotel_engineering",
            "工程經理",
            6,
            True,
            _INVENTORY_VIEWER,
            _DEPARTMENT_MANAGER,
        ),
        _position(
            "maintenance_technician",
            "維修技師",
            "hotel_engineering",
            "維修技師",
            3,
            False,
            _INVENTORY_VIEWER,
            ("inventory.outbound", "gis.locate"),
        ),
        _position(
            "hotel_supply_manager",
            "採購倉儲經理",
            "procurement_warehouse",
            "採購倉儲經理",
            6,
            True,
            _WAREHOUSE_MANAGER,
            _PROCUREMENT_MANAGER,
        ),
        _position(
            "hotel_buyer",
            "採購專員",
            "procurement_warehouse",
            "酒店採購專員",
            4,
            False,
            _PROCUREMENT_USER,
            _PROCUREMENT_WORKFLOW_OPERATOR,
        ),
        _position(
            "hotel_warehouse_clerk",
            "倉庫管理員",
            "procurement_warehouse",
            "酒店倉庫管理員",
            3,
            False,
            _INVENTORY_OPERATOR,
        ),
        _position(
            "hotel_finance_manager",
            "財務經理",
            "finance",
            "酒店財務經理",
            7,
            True,
            _FINANCE_MANAGER,
        ),
        _position("hotel_accountant", "會計", "finance", "酒店會計", 4, False, _FINANCE_USER),
        _position(
            "hotel_hr_manager", "人事行政經理", "hr_admin", "酒店人事行政經理", 6, True, _HR_MANAGER
        ),
        _position(
            "hotel_hr_specialist",
            "人事行政專員",
            "hr_admin",
            "酒店人事行政專員",
            3,
            False,
            _HR_USER,
        ),
    ],
)


_BLUEPRINTS["power_system"] = _blueprint(
    "power_system",
    "電力系統",
    "適用於發電、輸配電與電網企業的營銷、生產運維、調度安全、物資、財務、法務、研究技術與行政組織。",
    [
        _company(),
        _department("management", "管理層", "企業決策、安全生產責任與跨部門審批。"),
        _department("marketing_customer", "營銷與客戶服務", "市場、用戶服務、合同與業務協調。"),
        _department("production_maintenance", "生產運維", "輸變電設備運行、巡檢、檢修與缺陷處置。"),
        _department("dispatch_safety", "調度與安全", "運行調度、安全監督、兩票與應急管理。"),
        _department(
            "procurement_warehouse", "採購倉儲", "招標採購、供應商、備品備件與工器具管理。"
        ),
        _department("finance", "財務", "預算、資金、核算、成本與財務監督。"),
        _department("legal_compliance", "法務合規", "合同、訴訟、牌照、履約與合規風險。"),
        _department("research_technology", "研究與技術", "技術監督、科研、標準與數字化研究。"),
        _department("hr_admin", "人事行政", "組織人事、培訓、行政與綜合保障。"),
    ],
    [
        _position(
            "grid_general_manager", "總經理", "management", "電力企業總經理", 9, True, _EXECUTIVE
        ),
        _position(
            "grid_deputy_general_manager",
            "副總經理",
            "management",
            "電力企業副總經理",
            8,
            True,
            _EXECUTIVE,
        ),
        _position(
            "grid_system_admin", "系統管理員", "management", "系統管理員", 10, True, _SYSTEM_ADMIN
        ),
        _position(
            "marketing_manager",
            "營銷主管",
            "marketing_customer",
            "營銷主管",
            6,
            True,
            _DEPARTMENT_MANAGER,
            ("legal.manage",),
        ),
        _position(
            "customer_specialist",
            "客戶服務專員",
            "marketing_customer",
            "客戶服務專員",
            3,
            False,
            _BUSINESS_USER,
        ),
        _position(
            "power_production_manager",
            "生產運維主管",
            "production_maintenance",
            "生產運維主管",
            7,
            True,
            _WAREHOUSE_MANAGER,
            _DEPARTMENT_MANAGER,
        ),
        _position(
            "grid_maintenance_technician",
            "檢修運維人員",
            "production_maintenance",
            "檢修運維人員",
            4,
            False,
            _INVENTORY_VIEWER,
            ("inventory.outbound", "gis.locate", "ledger.write"),
        ),
        _position(
            "dispatch_safety_manager",
            "調度安全主管",
            "dispatch_safety",
            "調度安全主管",
            7,
            True,
            _DEPARTMENT_MANAGER,
            ("gis.read", "gis.manage", "audit.read", "inventory.read", "ledger.read"),
        ),
        _position(
            "dispatch_operator",
            "調度值班員",
            "dispatch_safety",
            "調度值班員",
            4,
            False,
            _BUSINESS_USER,
            ("gis.read", "audit.read"),
        ),
        _position(
            "grid_supply_manager",
            "採購倉儲主管",
            "procurement_warehouse",
            "電力採購倉儲主管",
            7,
            True,
            _WAREHOUSE_MANAGER,
            _PROCUREMENT_MANAGER,
        ),
        _position(
            "grid_buyer",
            "採購專員",
            "procurement_warehouse",
            "電力採購專員",
            4,
            False,
            _PROCUREMENT_USER,
            _PROCUREMENT_WORKFLOW_OPERATOR,
        ),
        _position(
            "grid_warehouse_clerk",
            "物資庫管員",
            "procurement_warehouse",
            "電力物資庫管員",
            3,
            False,
            _INVENTORY_OPERATOR,
        ),
        _position(
            "grid_finance_manager", "財務主管", "finance", "電力財務主管", 7, True, _FINANCE_MANAGER
        ),
        _position("grid_accountant", "會計", "finance", "電力會計", 4, False, _FINANCE_USER),
        _position(
            "legal_manager",
            "法務合規主管",
            "legal_compliance",
            "法務合規主管",
            7,
            True,
            _DEPARTMENT_MANAGER,
            ("legal.manage", "audit.read"),
        ),
        _position(
            "legal_specialist",
            "法務專員",
            "legal_compliance",
            "法務專員",
            4,
            False,
            _BUSINESS_USER,
            ("legal.manage",),
        ),
        _position(
            "research_director",
            "研究技術主管",
            "research_technology",
            "研究技術主管",
            7,
            True,
            _DEPARTMENT_MANAGER,
            ("inventory.read", "ledger.read"),
        ),
        _position(
            "research_engineer",
            "研究工程師",
            "research_technology",
            "研究工程師",
            4,
            False,
            _BUSINESS_USER,
            ("inventory.read", "ledger.read"),
        ),
        _position(
            "grid_hr_manager", "人事行政主管", "hr_admin", "電力人事行政主管", 6, True, _HR_MANAGER
        ),
        _position(
            "grid_hr_specialist", "人事行政專員", "hr_admin", "電力人事行政專員", 3, False, _HR_USER
        ),
    ],
)


_BLUEPRINTS["manufacturing_factory"] = _blueprint(
    "manufacturing_factory",
    "製造工廠",
    "適用於生產、品質、設備、物料與供應鏈協同的製造企業。",
    [
        _company(),
        _department("management", "管理層", "工廠經營、生產安全與跨部門決策。"),
        _department("manufacturing_production", "生產製造", "生產計劃、工序執行與在製品流轉。"),
        _department("quality", "品質管理", "來料、過程、成品檢驗與品質追溯。"),
        _department("equipment", "設備工程", "設備、模具、量檢具與維修備件。"),
        _department("procurement_warehouse", "採購倉儲", "原料採購、收發存與供應商管理。"),
        _department("finance", "財務", "成本核算、資金、預算與經營報表。"),
        _department("hr_admin", "人事行政", "人員、培訓、安全行政與後勤。"),
    ],
    [
        _position("factory_general_manager", "廠長", "management", "工廠廠長", 9, True, _EXECUTIVE),
        _position(
            "factory_deputy_director", "副廠長", "management", "工廠副廠長", 8, True, _EXECUTIVE
        ),
        _position(
            "factory_system_admin",
            "系統管理員",
            "management",
            "系統管理員",
            10,
            True,
            _SYSTEM_ADMIN,
        ),
        _position(
            "manufacturing_production_manager",
            "生產主管",
            "manufacturing_production",
            "製造生產主管",
            6,
            True,
            _DEPARTMENT_MANAGER,
            _INVENTORY_VIEWER,
        ),
        _position(
            "production_operator",
            "生產領料員",
            "manufacturing_production",
            "生產領料員",
            3,
            False,
            _INVENTORY_VIEWER,
            ("inventory.outbound", "ledger.write"),
        ),
        _position(
            "quality_manager",
            "品質主管",
            "quality",
            "製造品質主管",
            6,
            True,
            _DEPARTMENT_MANAGER,
            ("inventory.read", "ledger.read", "audit.read"),
        ),
        _position(
            "quality_inspector",
            "品質檢驗員",
            "quality",
            "品質檢驗員",
            3,
            False,
            _INVENTORY_VIEWER,
            ("audit.read",),
        ),
        _position(
            "manufacturing_equipment_manager",
            "設備主管",
            "equipment",
            "設備工程主管",
            6,
            True,
            _DEPARTMENT_MANAGER,
            _INVENTORY_VIEWER,
        ),
        _position(
            "equipment_technician",
            "設備維修技師",
            "equipment",
            "設備維修技師",
            3,
            False,
            _INVENTORY_VIEWER,
            ("inventory.outbound", "gis.locate"),
        ),
        _position(
            "factory_supply_manager",
            "採購倉儲主管",
            "procurement_warehouse",
            "製造採購倉儲主管",
            7,
            True,
            _WAREHOUSE_MANAGER,
            _PROCUREMENT_MANAGER,
        ),
        _position(
            "factory_buyer",
            "採購專員",
            "procurement_warehouse",
            "製造採購專員",
            4,
            False,
            _PROCUREMENT_USER,
            _PROCUREMENT_WORKFLOW_OPERATOR,
        ),
        _position(
            "factory_warehouse_clerk",
            "物料庫管員",
            "procurement_warehouse",
            "製造物料庫管員",
            3,
            False,
            _INVENTORY_OPERATOR,
        ),
        _position(
            "factory_finance_manager",
            "財務主管",
            "finance",
            "製造財務主管",
            7,
            True,
            _FINANCE_MANAGER,
        ),
        _position(
            "cost_accountant", "成本會計", "finance", "製造成本會計", 4, False, _FINANCE_USER
        ),
        _position(
            "factory_hr_manager",
            "人事行政主管",
            "hr_admin",
            "製造人事行政主管",
            6,
            True,
            _HR_MANAGER,
        ),
        _position(
            "factory_hr_specialist",
            "人事行政專員",
            "hr_admin",
            "製造人事行政專員",
            3,
            False,
            _HR_USER,
        ),
    ],
)


_BLUEPRINTS["construction_site"] = _blueprint(
    "construction_site",
    "建築工程",
    "適用於工程項目、施工技術、安全品質、材料與合同協同。",
    [
        _company(),
        _department("management", "管理層", "企業及項目經營決策與重大審批。"),
        _department("project_management", "項目管理", "進度、現場協調、分包與工作任務。"),
        _department("construction_engineering", "工程技術", "施工方案、技術交底、變更與竣工資料。"),
        _department("safety_quality", "安全品質", "安全巡檢、品質驗收與風險整改。"),
        _department("materials_warehouse", "材料倉儲", "建材、周轉料、機具與現場倉庫。"),
        _department("procurement_contracts", "採購合同", "招標採購、合同與供應商履約。"),
        _department("finance", "財務", "項目成本、資金、預算與結算。"),
        _department("hr_admin", "人事行政", "項目人員、行政與後勤保障。"),
    ],
    [
        _position(
            "construction_general_manager",
            "總經理",
            "management",
            "工程企業總經理",
            9,
            True,
            _EXECUTIVE,
        ),
        _position(
            "construction_deputy_general_manager",
            "副總經理",
            "management",
            "工程企業副總經理",
            8,
            True,
            _EXECUTIVE,
        ),
        _position(
            "construction_system_admin",
            "系統管理員",
            "management",
            "系統管理員",
            10,
            True,
            _SYSTEM_ADMIN,
        ),
        _position(
            "project_manager",
            "項目經理",
            "project_management",
            "工程項目經理",
            7,
            True,
            _DEPARTMENT_MANAGER,
            _INVENTORY_VIEWER,
            ("audit.read",),
        ),
        _position(
            "site_coordinator",
            "現場協調員",
            "project_management",
            "工程現場協調員",
            4,
            False,
            _BUSINESS_USER,
            ("gis.read",),
        ),
        _position(
            "construction_engineering_manager",
            "技術負責人",
            "construction_engineering",
            "工程技術負責人",
            7,
            True,
            _DEPARTMENT_MANAGER,
            ("gis.read",),
        ),
        _position(
            "site_engineer",
            "施工工程師",
            "construction_engineering",
            "施工工程師",
            4,
            False,
            _BUSINESS_USER,
            ("gis.read", "inventory.read"),
        ),
        _position(
            "safety_quality_manager",
            "安全品質主管",
            "safety_quality",
            "安全品質主管",
            7,
            True,
            _DEPARTMENT_MANAGER,
            ("audit.read", "gis.read", "inventory.read"),
        ),
        _position(
            "safety_inspector",
            "安全員",
            "safety_quality",
            "工程安全員",
            4,
            False,
            _BUSINESS_USER,
            ("audit.read", "gis.read"),
        ),
        _position(
            "materials_manager",
            "材料主管",
            "materials_warehouse",
            "工程材料主管",
            6,
            True,
            _WAREHOUSE_MANAGER,
        ),
        _position(
            "site_storekeeper",
            "現場庫管員",
            "materials_warehouse",
            "工程現場庫管員",
            3,
            False,
            _INVENTORY_OPERATOR,
        ),
        _position(
            "contracts_manager",
            "採購合同主管",
            "procurement_contracts",
            "工程採購合同主管",
            7,
            True,
            _PROCUREMENT_MANAGER,
            ("legal.manage",),
        ),
        _position(
            "construction_buyer",
            "採購專員",
            "procurement_contracts",
            "工程採購專員",
            4,
            False,
            _PROCUREMENT_USER,
            _PROCUREMENT_WORKFLOW_OPERATOR,
        ),
        _position(
            "construction_finance_manager",
            "財務主管",
            "finance",
            "工程財務主管",
            7,
            True,
            _FINANCE_MANAGER,
        ),
        _position(
            "project_accountant", "項目會計", "finance", "工程項目會計", 4, False, _FINANCE_USER
        ),
        _position(
            "construction_hr_manager",
            "人事行政主管",
            "hr_admin",
            "工程人事行政主管",
            6,
            True,
            _HR_MANAGER,
        ),
        _position(
            "construction_hr_specialist",
            "人事行政專員",
            "hr_admin",
            "工程人事行政專員",
            3,
            False,
            _HR_USER,
        ),
    ],
)


_BLUEPRINTS["restaurant_kitchen"] = _blueprint(
    "restaurant_kitchen",
    "餐飲後廚",
    "適用於門店服務、後廚、食品安全、採購倉儲與餐飲財務。",
    [
        _company(),
        _department("management", "管理層", "門店經營、食品安全與重大審批。"),
        _department("front_service", "前廳服務", "迎賓、點單、收銀與顧客服務。"),
        _department("kitchen", "後廚生產", "備料、烹飪、出品與廚房物料領用。"),
        _department("food_safety", "食品安全與品質", "驗收、留樣、效期與衛生檢查。"),
        _department("procurement_warehouse", "採購倉儲", "食材採購、收貨、冷藏與庫存管理。"),
        _department("finance", "財務", "門店收入、成本、應付與經營報表。"),
        _department("hr_admin", "人事行政", "招聘、排班支持、培訓與行政。"),
    ],
    [
        _position(
            "restaurant_general_manager", "店長", "management", "餐飲店長", 8, True, _EXECUTIVE
        ),
        _position(
            "restaurant_deputy_manager", "副店長", "management", "餐飲副店長", 7, True, _EXECUTIVE
        ),
        _position(
            "restaurant_system_admin",
            "系統管理員",
            "management",
            "系統管理員",
            10,
            True,
            _SYSTEM_ADMIN,
        ),
        _position(
            "front_service_manager",
            "前廳主管",
            "front_service",
            "餐飲前廳主管",
            6,
            True,
            _DEPARTMENT_MANAGER,
        ),
        _position(
            "service_staff", "服務員", "front_service", "餐飲服務員", 2, False, _BUSINESS_USER
        ),
        _position(
            "executive_chef",
            "廚師長",
            "kitchen",
            "廚師長",
            6,
            True,
            _DEPARTMENT_MANAGER,
            _INVENTORY_VIEWER,
        ),
        _position(
            "kitchen_receiver",
            "後廚領料員",
            "kitchen",
            "後廚領料員",
            3,
            False,
            _INVENTORY_VIEWER,
            ("inventory.outbound", "ledger.write"),
        ),
        _position(
            "food_safety_manager",
            "食品安全主管",
            "food_safety",
            "食品安全主管",
            6,
            True,
            _DEPARTMENT_MANAGER,
            ("inventory.read", "ledger.read", "audit.read"),
        ),
        _position(
            "food_safety_inspector",
            "食品安全員",
            "food_safety",
            "食品安全員",
            3,
            False,
            _INVENTORY_VIEWER,
            ("audit.read",),
        ),
        _position(
            "restaurant_supply_manager",
            "採購倉儲主管",
            "procurement_warehouse",
            "餐飲採購倉儲主管",
            6,
            True,
            _WAREHOUSE_MANAGER,
            _PROCUREMENT_MANAGER,
        ),
        _position(
            "restaurant_buyer",
            "採購專員",
            "procurement_warehouse",
            "餐飲採購專員",
            4,
            False,
            _PROCUREMENT_USER,
            _PROCUREMENT_WORKFLOW_OPERATOR,
        ),
        _position(
            "restaurant_kitchen_storekeeper",
            "倉庫管理員",
            "procurement_warehouse",
            "餐飲倉庫管理員",
            3,
            False,
            _INVENTORY_OPERATOR,
        ),
        _position(
            "restaurant_finance_manager",
            "財務主管",
            "finance",
            "餐飲財務主管",
            7,
            True,
            _FINANCE_MANAGER,
        ),
        _position("restaurant_accountant", "會計", "finance", "餐飲會計", 4, False, _FINANCE_USER),
        _position(
            "restaurant_hr_manager",
            "人事行政主管",
            "hr_admin",
            "餐飲人事行政主管",
            6,
            True,
            _HR_MANAGER,
        ),
        _position(
            "restaurant_hr_specialist",
            "人事行政專員",
            "hr_admin",
            "餐飲人事行政專員",
            3,
            False,
            _HR_USER,
        ),
    ],
)


_BLUEPRINTS["medical_clinic"] = _blueprint(
    "medical_clinic",
    "醫療診所",
    "適用於診療、護理、藥械、消毒設備、合規與財務管理。",
    [
        _company(),
        _department("management", "管理層", "診所經營、醫療品質與合規責任。"),
        _department("clinical", "臨床診療", "門診、醫療服務與臨床協作。"),
        _department("nursing", "護理", "護理服務、醫用耗材領用與交班。"),
        _department("pharmacy_supplies", "藥房與醫療物資", "藥品、耗材、批號、效期與收發存。"),
        _department("equipment_sterilization", "設備與消毒", "醫療設備、器械消毒、維保與校驗。"),
        _department("finance", "財務", "收費、結算、成本、應付與財務報表。"),
        _department("hr_admin_compliance", "人事行政與合規", "人員資質、行政、牌照與合規台賬。"),
    ],
    [
        _position(
            "clinic_director",
            "診所主任",
            "management",
            "診所主任",
            9,
            True,
            _EXECUTIVE,
            ("legal.manage",),
        ),
        _position(
            "clinic_deputy_director", "診所副主任", "management", "診所副主任", 8, True, _EXECUTIVE
        ),
        _position(
            "clinic_system_admin", "系統管理員", "management", "系統管理員", 10, True, _SYSTEM_ADMIN
        ),
        _position(
            "clinical_manager", "臨床負責人", "clinical", "臨床負責人", 7, True, _DEPARTMENT_MANAGER
        ),
        _position("doctor", "醫師", "clinical", "診所醫師", 5, False, _BUSINESS_USER),
        _position(
            "nursing_manager",
            "護理主管",
            "nursing",
            "診所護理主管",
            6,
            True,
            _DEPARTMENT_MANAGER,
            _INVENTORY_VIEWER,
        ),
        _position(
            "nurse",
            "護理人員",
            "nursing",
            "診所護理人員",
            3,
            False,
            _INVENTORY_VIEWER,
            ("inventory.outbound", "ledger.write"),
        ),
        _position(
            "pharmacy_manager",
            "藥房物資主管",
            "pharmacy_supplies",
            "藥房物資主管",
            7,
            True,
            _WAREHOUSE_MANAGER,
        ),
        _position(
            "pharmacy_storekeeper",
            "藥品物資管理員",
            "pharmacy_supplies",
            "藥品物資管理員",
            4,
            False,
            _INVENTORY_OPERATOR,
            _PROCUREMENT_WORKFLOW_OPERATOR,
        ),
        _position(
            "clinic_equipment_manager",
            "設備消毒主管",
            "equipment_sterilization",
            "醫療設備消毒主管",
            6,
            True,
            _DEPARTMENT_MANAGER,
            _INVENTORY_VIEWER,
        ),
        _position(
            "sterilization_technician",
            "消毒設備技師",
            "equipment_sterilization",
            "消毒設備技師",
            3,
            False,
            _INVENTORY_VIEWER,
            ("inventory.outbound", "gis.locate"),
        ),
        _position(
            "clinic_finance_manager",
            "財務主管",
            "finance",
            "診所財務主管",
            7,
            True,
            _FINANCE_MANAGER,
        ),
        _position(
            "clinic_accountant", "會計收費員", "finance", "診所會計收費員", 4, False, _FINANCE_USER
        ),
        _position(
            "clinic_admin_manager",
            "人事行政合規主管",
            "hr_admin_compliance",
            "診所人事行政合規主管",
            7,
            True,
            _HR_MANAGER,
            ("legal.manage",),
        ),
        _position(
            "clinic_admin_specialist",
            "人事行政專員",
            "hr_admin_compliance",
            "診所人事行政專員",
            3,
            False,
            _HR_USER,
        ),
    ],
)


_BLUEPRINTS["retail_store"] = _blueprint(
    "retail_store",
    "零售門店",
    "適用於門店運營、商品、補貨倉儲、財務與人事行政。",
    [
        _company(),
        _department("management", "管理層", "門店經營、指標與跨部門審批。"),
        _department("store_operations", "門店運營", "顧客服務、收銀、陳列執行與日常運營。"),
        _department("merchandising", "商品管理", "商品策略、價格、促銷與供應協同。"),
        _department("warehouse_replenishment", "倉儲補貨", "收貨、後倉、補貨、調撥與盤點。"),
        _department("finance", "財務", "營業款、對賬、成本與經營報表。"),
        _department("hr_admin", "人事行政", "招聘、排班支持、培訓與行政。"),
    ],
    [
        _position("retail_general_manager", "店長", "management", "零售店長", 8, True, _EXECUTIVE),
        _position(
            "retail_deputy_manager", "副店長", "management", "零售副店長", 7, True, _EXECUTIVE
        ),
        _position(
            "retail_system_admin", "系統管理員", "management", "系統管理員", 10, True, _SYSTEM_ADMIN
        ),
        _position(
            "operations_manager",
            "門店運營主管",
            "store_operations",
            "零售運營主管",
            6,
            True,
            _DEPARTMENT_MANAGER,
            _INVENTORY_VIEWER,
        ),
        _position(
            "store_associate",
            "門店員工",
            "store_operations",
            "零售門店員工",
            2,
            False,
            _INVENTORY_VIEWER,
            ("inventory.outbound",),
        ),
        _position(
            "merchandising_manager",
            "商品主管",
            "merchandising",
            "零售商品主管",
            6,
            True,
            _PROCUREMENT_MANAGER,
        ),
        _position(
            "merchandiser",
            "商品專員",
            "merchandising",
            "零售商品專員",
            4,
            False,
            _PROCUREMENT_USER,
            _PROCUREMENT_WORKFLOW_OPERATOR,
        ),
        _position(
            "replenishment_manager",
            "倉儲補貨主管",
            "warehouse_replenishment",
            "零售倉儲補貨主管",
            6,
            True,
            _WAREHOUSE_MANAGER,
        ),
        _position(
            "retail_storekeeper",
            "收貨補貨員",
            "warehouse_replenishment",
            "零售收貨補貨員",
            3,
            False,
            _INVENTORY_OPERATOR,
        ),
        _position(
            "retail_finance_manager",
            "財務主管",
            "finance",
            "零售財務主管",
            7,
            True,
            _FINANCE_MANAGER,
        ),
        _position(
            "retail_accountant", "門店會計", "finance", "零售門店會計", 4, False, _FINANCE_USER
        ),
        _position(
            "retail_hr_manager",
            "人事行政主管",
            "hr_admin",
            "零售人事行政主管",
            6,
            True,
            _HR_MANAGER,
        ),
        _position(
            "retail_hr_specialist",
            "人事行政專員",
            "hr_admin",
            "零售人事行政專員",
            3,
            False,
            _HR_USER,
        ),
    ],
)


_BLUEPRINTS["logistics_express"] = _blueprint(
    "logistics_express",
    "物流快遞",
    "適用於調度、分揀倉儲、運輸設備、客服、財務與行政管理。",
    [
        _company(),
        _department("management", "管理層", "物流網絡經營、服務品質與重大審批。"),
        _department("operations_dispatch", "運營調度", "線路、班次、運力與異常調度。"),
        _department("sorting_warehouse", "分揀倉儲", "收貨、分揀、周轉容器與作業物資管理。"),
        _department("fleet_equipment", "車隊與設備", "車輛、搬運設備、維保與備件。"),
        _department("customer_service", "客戶服務", "客戶查詢、服務異常與商務協作。"),
        _department("finance", "財務", "運費結算、成本、資金與財務報表。"),
        _department("hr_admin", "人事行政", "人員、班次支持、培訓與行政。"),
    ],
    [
        _position(
            "logistics_general_manager",
            "總經理",
            "management",
            "物流企業總經理",
            9,
            True,
            _EXECUTIVE,
        ),
        _position(
            "logistics_deputy_general_manager",
            "副總經理",
            "management",
            "物流企業副總經理",
            8,
            True,
            _EXECUTIVE,
        ),
        _position(
            "logistics_system_admin",
            "系統管理員",
            "management",
            "系統管理員",
            10,
            True,
            _SYSTEM_ADMIN,
        ),
        _position(
            "dispatch_manager",
            "運營調度主管",
            "operations_dispatch",
            "物流運營調度主管",
            7,
            True,
            _DEPARTMENT_MANAGER,
            ("gis.read", "gis.manage", "audit.read"),
        ),
        _position(
            "dispatcher",
            "調度員",
            "operations_dispatch",
            "物流調度員",
            4,
            False,
            _BUSINESS_USER,
            ("gis.read",),
        ),
        _position(
            "sorting_manager",
            "分揀倉儲主管",
            "sorting_warehouse",
            "物流分揀倉儲主管",
            6,
            True,
            _WAREHOUSE_MANAGER,
        ),
        _position(
            "sorting_storekeeper",
            "分揀庫管員",
            "sorting_warehouse",
            "物流分揀庫管員",
            3,
            False,
            _INVENTORY_OPERATOR,
            _PROCUREMENT_WORKFLOW_OPERATOR,
        ),
        _position(
            "fleet_manager",
            "車隊設備主管",
            "fleet_equipment",
            "物流車隊設備主管",
            6,
            True,
            _DEPARTMENT_MANAGER,
            _INVENTORY_VIEWER,
            ("gis.read", "gis.locate"),
        ),
        _position(
            "fleet_technician",
            "設備維修員",
            "fleet_equipment",
            "物流設備維修員",
            3,
            False,
            _INVENTORY_VIEWER,
            ("inventory.outbound", "gis.locate"),
        ),
        _position(
            "customer_service_manager",
            "客服主管",
            "customer_service",
            "物流客服主管",
            6,
            True,
            _DEPARTMENT_MANAGER,
        ),
        _position(
            "customer_service_agent",
            "客服專員",
            "customer_service",
            "物流客服專員",
            3,
            False,
            _BUSINESS_USER,
        ),
        _position(
            "logistics_finance_manager",
            "財務主管",
            "finance",
            "物流財務主管",
            7,
            True,
            _FINANCE_MANAGER,
        ),
        _position(
            "logistics_accountant", "結算會計", "finance", "物流結算會計", 4, False, _FINANCE_USER
        ),
        _position(
            "logistics_hr_manager",
            "人事行政主管",
            "hr_admin",
            "物流人事行政主管",
            6,
            True,
            _HR_MANAGER,
        ),
        _position(
            "logistics_hr_specialist",
            "人事行政專員",
            "hr_admin",
            "物流人事行政專員",
            3,
            False,
            _HR_USER,
        ),
    ],
)


_BLUEPRINTS["research_lab"] = _blueprint(
    "research_lab",
    "實驗室科研",
    "適用於課題研究、實驗運行、安全合規、試劑儀器與科研採購。",
    [
        _company(),
        _department("management", "管理層", "科研方向、資源分配與重大安全責任。"),
        _department("research", "研究中心", "研究課題、研究方案、課題負責人、研究人員與成果管理。"),
        _department(
            "lab_research_technology",
            "科研中心",
            "科研技術、方法開發、技術驗證、工程轉化與技術協作。",
        ),
        _department("lab_operations", "實驗室", "實驗運行、儀器、試劑耗材與預約借還。"),
        _department("safety_compliance", "安全合規", "危化品、實驗安全、資質與審計。"),
        _department("procurement_warehouse", "採購倉儲", "科研採購、供應商、試劑及物資庫存。"),
        _department("finance", "財務", "課題預算、報銷、資金與財務報表。"),
        _department("hr_admin", "人事行政", "科研人員、訪客、培訓與行政保障。"),
    ],
    [
        _position("lab_general_manager", "總經理", "management", "總經理", 9, True, _EXECUTIVE),
        _position(
            "lab_deputy_general_manager", "副總經理", "management", "副總經理", 8, True, _EXECUTIVE
        ),
        _position(
            "lab_system_admin", "系統管理員", "management", "系統管理員", 10, True, _SYSTEM_ADMIN
        ),
        _position(
            "research_center_director",
            "研究中心主任",
            "research",
            "研究中心主任",
            8,
            True,
            _DEPARTMENT_MANAGER,
            _INVENTORY_VIEWER,
            _RESEARCH_REVIEWER,
        ),
        _position(
            "research_center_deputy_director",
            "研究中心副主任",
            "research",
            "研究中心副主任",
            7,
            True,
            _DEPARTMENT_MANAGER,
            _INVENTORY_VIEWER,
            _RESEARCH_REVIEWER,
        ),
        _position(
            "principal_investigator",
            "課題負責人",
            "research",
            "課題負責人",
            6,
            True,
            _DEPARTMENT_MANAGER,
            _INVENTORY_VIEWER,
            _RESEARCH_REVIEWER,
        ),
        _position(
            "researcher",
            "研究員",
            "research",
            "研究員",
            4,
            False,
            _INVENTORY_VIEWER,
            _RESEARCH_EDITOR,
            ("inventory.outbound", "ledger.write"),
        ),
        _position(
            "research_assistant",
            "助理研究員",
            "research",
            "助理研究員",
            3,
            False,
            _INVENTORY_VIEWER,
            _RESEARCH_EDITOR,
        ),
        _position(
            "scientific_research_center_director",
            "科研中心主任",
            "lab_research_technology",
            "科研中心主任",
            8,
            True,
            _DEPARTMENT_MANAGER,
            _INVENTORY_VIEWER,
            _RESEARCH_REVIEWER,
        ),
        _position(
            "scientific_research_center_deputy_director",
            "科研中心副主任",
            "lab_research_technology",
            "科研中心副主任",
            7,
            True,
            _DEPARTMENT_MANAGER,
            _INVENTORY_VIEWER,
            _RESEARCH_REVIEWER,
        ),
        _position(
            "research_technology_manager",
            "科研技術主管",
            "lab_research_technology",
            "科研技術主管",
            6,
            True,
            _DEPARTMENT_MANAGER,
            _INVENTORY_VIEWER,
            _RESEARCH_REVIEWER,
        ),
        _position(
            "lab_research_engineer",
            "科研工程師",
            "lab_research_technology",
            "科研工程師",
            4,
            False,
            _INVENTORY_VIEWER,
            _RESEARCH_EDITOR,
            ("inventory.outbound", "ledger.write"),
        ),
        _position(
            "technical_researcher",
            "技術研究員",
            "lab_research_technology",
            "技術研究員",
            4,
            False,
            _INVENTORY_VIEWER,
            _RESEARCH_EDITOR,
        ),
        _position(
            "lab_director",
            "實驗室主任",
            "lab_operations",
            "實驗室主任",
            8,
            True,
            _DEPARTMENT_MANAGER,
            _INVENTORY_VIEWER,
        ),
        _position(
            "lab_deputy_director",
            "實驗室副主任",
            "lab_operations",
            "實驗室副主任",
            7,
            True,
            _DEPARTMENT_MANAGER,
            _INVENTORY_VIEWER,
        ),
        _position(
            "lab_operations_manager",
            "實驗運行主管",
            "lab_operations",
            "實驗運行主管",
            6,
            True,
            _WAREHOUSE_MANAGER,
        ),
        _position(
            "instrument_technician",
            "儀器管理員",
            "lab_operations",
            "科研儀器管理員",
            4,
            False,
            _INVENTORY_OPERATOR,
        ),
        _position(
            "lab_safety_manager",
            "安全合規主管",
            "safety_compliance",
            "實驗室安全合規主管",
            7,
            True,
            _DEPARTMENT_MANAGER,
            ("inventory.read", "ledger.read", "audit.read", "legal.manage"),
        ),
        _position(
            "lab_safety_officer",
            "安全員",
            "safety_compliance",
            "實驗室安全員",
            4,
            False,
            _INVENTORY_VIEWER,
            ("audit.read", "legal.manage"),
        ),
        _position(
            "lab_supply_manager",
            "科研採購倉儲主管",
            "procurement_warehouse",
            "科研採購倉儲主管",
            6,
            True,
            _WAREHOUSE_MANAGER,
            _PROCUREMENT_MANAGER,
        ),
        _position(
            "lab_buyer",
            "科研採購專員",
            "procurement_warehouse",
            "科研採購專員",
            4,
            False,
            _PROCUREMENT_USER,
            _PROCUREMENT_WORKFLOW_OPERATOR,
        ),
        _position(
            "lab_storekeeper",
            "試劑物資管理員",
            "procurement_warehouse",
            "試劑物資管理員",
            3,
            False,
            _INVENTORY_OPERATOR,
        ),
        _position(
            "lab_finance_manager", "財務主管", "finance", "科研財務主管", 7, True, _FINANCE_MANAGER
        ),
        _position(
            "grant_accountant", "課題會計", "finance", "科研課題會計", 4, False, _FINANCE_USER
        ),
        _position(
            "lab_hr_manager", "人事行政主管", "hr_admin", "科研人事行政主管", 6, True, _HR_MANAGER
        ),
        _position(
            "lab_hr_specialist", "人事行政專員", "hr_admin", "科研人事行政專員", 3, False, _HR_USER
        ),
    ],
)


_BLUEPRINTS["it_office_asset"] = _blueprint(
    "it_office_asset",
    "IT 與辦公資產",
    "適用於 IT 運維、資訊安全、資產、採購、財務與人事行政。",
    [
        _company(),
        _department("management", "管理層", "企業經營、資訊治理與重大審批。"),
        _department("it_operations", "IT 運維", "終端、網絡、服務台與技術備件。"),
        _department("information_security", "資訊安全", "帳號、權限、安全基線與審計。"),
        _department("asset_warehouse", "資產與倉儲", "辦公設備、領用歸還、耗材與盤點。"),
        _department("procurement", "採購", "IT 與辦公採購、合同和供應商管理。"),
        _department("finance", "財務", "資產價值、預算、付款與財務報表。"),
        _department("hr_admin", "人事行政", "入離職協同、人員與辦公行政。"),
    ],
    [
        _position(
            "it_general_manager", "總經理", "management", "IT 資產企業總經理", 9, True, _EXECUTIVE
        ),
        _position(
            "it_deputy_general_manager",
            "副總經理",
            "management",
            "IT 資產企業副總經理",
            8,
            True,
            _EXECUTIVE,
        ),
        _position(
            "it_system_admin", "系統管理員", "management", "系統管理員", 10, True, _SYSTEM_ADMIN
        ),
        _position(
            "it_operations_manager",
            "IT 運維主管",
            "it_operations",
            "IT 運維主管",
            7,
            True,
            _DEPARTMENT_MANAGER,
            _INVENTORY_VIEWER,
            ("settings.manage", "terminal.use"),
        ),
        _position(
            "it_support_engineer",
            "IT 支持工程師",
            "it_operations",
            "IT 支持工程師",
            4,
            False,
            _INVENTORY_VIEWER,
            ("inventory.outbound", "gis.locate"),
        ),
        _position(
            "security_manager",
            "資訊安全主管",
            "information_security",
            "資訊安全主管",
            8,
            True,
            _DEPARTMENT_MANAGER,
            ("users.manage", "permissions.topology.manage", "audit.read", "settings.manage"),
        ),
        _position(
            "security_auditor",
            "資訊安全審計員",
            "information_security",
            "資訊安全審計員",
            5,
            False,
            _BUSINESS_USER,
            ("audit.read",),
        ),
        _position(
            "it_asset_manager",
            "資產倉儲主管",
            "asset_warehouse",
            "IT 資產倉儲主管",
            6,
            True,
            _WAREHOUSE_MANAGER,
            ("asset_mgmt.read", "asset_mgmt.manage"),
        ),
        _position(
            "it_asset_clerk",
            "資產管理員",
            "asset_warehouse",
            "IT 資產管理員",
            3,
            False,
            _INVENTORY_OPERATOR,
            ("asset_mgmt.read",),
        ),
        _position(
            "it_procurement_manager",
            "採購主管",
            "procurement",
            "IT 採購主管",
            6,
            True,
            _PROCUREMENT_MANAGER,
            ("legal.manage",),
        ),
        _position(
            "it_buyer",
            "採購專員",
            "procurement",
            "IT 採購專員",
            4,
            False,
            _PROCUREMENT_USER,
            _PROCUREMENT_WORKFLOW_OPERATOR,
        ),
        _position(
            "it_finance_manager",
            "財務主管",
            "finance",
            "IT 資產財務主管",
            7,
            True,
            _FINANCE_MANAGER,
            ("asset_mgmt.read",),
        ),
        _position(
            "it_accountant",
            "資產會計",
            "finance",
            "IT 資產會計",
            4,
            False,
            _FINANCE_USER,
            ("asset_mgmt.read",),
        ),
        _position(
            "it_hr_manager", "人事行政主管", "hr_admin", "IT 人事行政主管", 6, True, _HR_MANAGER
        ),
        _position(
            "it_hr_specialist", "人事行政專員", "hr_admin", "IT 人事行政專員", 3, False, _HR_USER
        ),
    ],
)


_BLUEPRINTS["film_equipment"] = _blueprint(
    "film_equipment",
    "影視器材",
    "適用於製片、攝影、燈光、道具器材、財務與劇組行政。",
    [
        _company(),
        _department("management", "管理層", "公司及項目經營、資源配置與重大審批。"),
        _department("film_production", "製片", "項目計劃、劇組協作、場地與供應商。"),
        _department("camera", "攝影", "機身、鏡頭、錄音及攝影器材借還。"),
        _department("lighting", "燈光", "燈具、電源、支架與現場器材借還。"),
        _department("props_warehouse", "道具器材倉儲", "道具、服裝、耗材、收發與盤點。"),
        _department("finance", "財務", "項目預算、費用、結算與財務報表。"),
        _department("hr_admin", "人事行政", "劇組人員、合同、檔期與行政保障。"),
    ],
    [
        _position(
            "film_general_manager", "總經理", "management", "影視企業總經理", 9, True, _EXECUTIVE
        ),
        _position(
            "film_deputy_general_manager",
            "副總經理",
            "management",
            "影視企業副總經理",
            8,
            True,
            _EXECUTIVE,
        ),
        _position(
            "film_system_admin", "系統管理員", "management", "系統管理員", 10, True, _SYSTEM_ADMIN
        ),
        _position(
            "producer",
            "製片主管",
            "film_production",
            "影視製片主管",
            7,
            True,
            _DEPARTMENT_MANAGER,
            _PROCUREMENT_MANAGER,
        ),
        _position(
            "production_coordinator",
            "製片協調",
            "film_production",
            "影視製片協調",
            4,
            False,
            _PROCUREMENT_USER,
            _PROCUREMENT_WORKFLOW_OPERATOR,
        ),
        _position(
            "camera_manager",
            "攝影器材主管",
            "camera",
            "影視攝影器材主管",
            6,
            True,
            _WAREHOUSE_MANAGER,
        ),
        _position(
            "camera_assistant",
            "攝影助理",
            "camera",
            "影視攝影助理",
            3,
            False,
            _INVENTORY_VIEWER,
            ("inventory.outbound", "ledger.write", "gis.locate"),
        ),
        _position(
            "lighting_manager",
            "燈光器材主管",
            "lighting",
            "影視燈光器材主管",
            6,
            True,
            _WAREHOUSE_MANAGER,
        ),
        _position(
            "lighting_assistant",
            "燈光助理",
            "lighting",
            "影視燈光助理",
            3,
            False,
            _INVENTORY_VIEWER,
            ("inventory.outbound", "ledger.write", "gis.locate"),
        ),
        _position(
            "props_manager",
            "道具倉儲主管",
            "props_warehouse",
            "影視道具倉儲主管",
            6,
            True,
            _WAREHOUSE_MANAGER,
        ),
        _position(
            "props_storekeeper",
            "道具器材管理員",
            "props_warehouse",
            "影視道具器材管理員",
            3,
            False,
            _INVENTORY_OPERATOR,
        ),
        _position(
            "film_finance_manager", "財務主管", "finance", "影視財務主管", 7, True, _FINANCE_MANAGER
        ),
        _position(
            "production_accountant", "項目會計", "finance", "影視項目會計", 4, False, _FINANCE_USER
        ),
        _position(
            "film_hr_manager",
            "人事行政主管",
            "hr_admin",
            "影視人事行政主管",
            6,
            True,
            _HR_MANAGER,
            ("legal.manage",),
        ),
        _position(
            "film_hr_specialist", "人事行政專員", "hr_admin", "影視人事行政專員", 3, False, _HR_USER
        ),
    ],
)


_BLUEPRINTS["biu_legal_ethics_case_lab"] = _blueprint(
    "biu_legal_ethics_case_lab",
    "BIU 法律伦理学术共同体",
    (
        "面向法律与伦理教育的 BIU 内部学术组织；覆盖案例发现、收录、律师工作、"
        "证据分析、多级审理、学术意见发布与归档；程序完成即进入档案。"
    ),
    [
        _company(),
        _biu_department(
            "management",
            "管理層",
            "Platform Administration",
            "仅负责租户技术配置；不作为公开学术职位部门。",
        ),
        _biu_department(
            "biu_academic_governance",
            "学术治理办公室",
            "Academic Governance Office",
            "维护学术标准、职位资格、伦理原则与组织规则。",
        ),
        _biu_department(
            "biu_open_participation",
            "开放参与中心",
            "Open Participation Center",
            "承接网站注册、入门学习与公开参与。",
        ),
        _biu_department(
            "biu_case_program",
            "案例项目中心",
            "Case Program Center",
            "统筹案例从发现、收录到发布和归档的学术流程。",
        ),
        _biu_department(
            "biu_case_discovery",
            "案例发现室",
            "Case Discovery Office",
            "发现公开来源并整理可供研究的案例线索。",
            parent="biu_case_program",
            unit_type="team",
        ),
        _biu_department(
            "biu_case_review",
            "案例审核室",
            "Case Review Office",
            "核查来源、隐私、伦理与案例收录条件。",
            parent="biu_case_program",
            unit_type="team",
        ),
        _biu_department(
            "biu_case_editorial",
            "案例编辑与发布室",
            "Case Editorial & Publication Office",
            "将获准案例整理为可供教学研究使用的版本。",
            parent="biu_case_program",
            unit_type="team",
        ),
        _biu_department(
            "biu_case_archive",
            "案件档案室",
            "Case Archive Office",
            "维护案件材料清单、版本关系、归档质量与检索信息。",
            parent="biu_case_program",
            unit_type="team",
        ),
        _biu_department(
            "biu_legal_practice_program",
            "法律实务项目中心",
            "Legal Practice Program Center",
            "组织律师、证据、协商与调解方向的学术工作。",
        ),
        _biu_department(
            "biu_attorney_program",
            "律师项目部",
            "Attorney Program",
            "开展原告、辩护、检方与上诉方向的法律分析。",
            parent="biu_legal_practice_program",
            unit_type="team",
        ),
        _biu_department(
            "biu_evidence_technology",
            "证据技术研究室",
            "Evidence & Technology Lab",
            "负责证据结构、证据开示、数字材料与 AI 伦理分析。",
            parent="biu_legal_practice_program",
            unit_type="team",
        ),
        _biu_department(
            "biu_mediation_program",
            "协商与调解中心",
            "Negotiation & Mediation Center",
            "研究协商、调解和非裁判式争议处理方法。",
            parent="biu_legal_practice_program",
            unit_type="team",
        ),
        _biu_department(
            "biu_adjudication_program",
            "审理研究项目中心",
            "Adjudication Studies Center",
            "组织初审、上诉与最终复核的分级学术程序。",
        ),
        _biu_department(
            "biu_trial_division",
            "初审部",
            "Trial Division",
            "负责事实争点、庭审秩序与初审意见。",
            parent="biu_adjudication_program",
            unit_type="team",
        ),
        _biu_department(
            "biu_appellate_division",
            "上诉审查部",
            "Appellate Division",
            "负责上诉理由、法律适用与初审程序复核。",
            parent="biu_adjudication_program",
            unit_type="team",
        ),
        _biu_department(
            "biu_final_review_panel",
            "最终复核委员会",
            "Final Review Panel",
            "对符合条件的案件进行最终学术复核并形成结论。",
            parent="biu_adjudication_program",
            unit_type="team",
        ),
    ],
    [
        _biu_position(
            "biu_system_admin",
            "系统管理员",
            "System Administrator",
            "management",
            10,
            "P5",
            "appointment",
            "维护 BIU 租户配置与技术安全，不参与公开职位选择。",
            _BIU_SYSTEM_ADMIN,
            is_manager=True,
            visibility="hidden",
            requirements=("由 BIU 平台所有者指定",),
            system_admin=True,
        ),
        _biu_position(
            "biu_academic_director",
            "学术项目主任",
            "Academic Program Director",
            "biu_academic_governance",
            8,
            "P4",
            "appointment",
            "维护学术标准、职位规则和跨部门项目质量。",
            _BIU_ACADEMIC_GOVERNANCE,
        ),
        _biu_position(
            "biu_registered_participant",
            "注册参与者",
            "Registered Participant",
            "biu_open_participation",
            1,
            "P0",
            "direct",
            "完成注册后参与学习、观察公开项目并申请进阶职位。",
            _BIU_MEMBER,
            case_roles=("observer",),
            quick_registration=True,
        ),
        _biu_position(
            "biu_case_observer",
            "案件观察员",
            "Case Observer",
            "biu_open_participation",
            2,
            "P0",
            "direct",
            "跟随获准公开的案件进度并记录学习笔记。",
            _BIU_MEMBER,
            case_roles=("observer",),
            quick_registration=True,
            guest_enabled=True,
        ),
        _biu_position(
            "biu_case_administrator",
            "案件程序管理员",
            "Case Administrator",
            "biu_case_program",
            6,
            "P3",
            "appointment",
            "建立案件、分配案件角色、维护程序节点并在归档后结案。",
            _BIU_CASE_ADMINISTRATOR,
            is_manager=True,
            case_roles=("case_administrator",),
        ),
        _biu_position(
            "biu_case_scout",
            "案例发现员",
            "Case Scout",
            "biu_case_discovery",
            2,
            "P1",
            "direct",
            "从公开来源发现具有法律与伦理研究价值的案例线索。",
            _BIU_DIRECT_CONTRIBUTOR,
            quick_registration=True,
            guest_enabled=True,
        ),
        _biu_position(
            "biu_public_record_researcher",
            "公开档案研究员",
            "Public Record Researcher",
            "biu_case_discovery",
            3,
            "P1",
            "application",
            "整理公开档案、来源说明和可验证引用。",
            _BIU_CONTRIBUTOR,
        ),
        _biu_position(
            "biu_case_intake_clerk",
            "案例收录书记员",
            "Case Intake Clerk",
            "biu_case_review",
            4,
            "P2",
            "application",
            "登记案例候选材料并协调来源、隐私和适格审查。",
            _BIU_CONTRIBUTOR,
            case_roles=("intake_clerk",),
        ),
        _biu_position(
            "biu_source_verification_analyst",
            "来源核查员",
            "Source Verification Analyst",
            "biu_case_review",
            4,
            "P2",
            "exam",
            "核对材料来源、版本、日期和引用链条。",
            _BIU_CONTRIBUTOR,
        ),
        _biu_position(
            "biu_ethics_privacy_reviewer",
            "法律伦理与隐私审查员",
            "Legal Ethics & Privacy Reviewer",
            "biu_case_review",
            5,
            "P3",
            "exam",
            "审查去标识化、隐私风险、研究伦理和发布边界。",
            _BIU_CONTRIBUTOR,
            case_roles=("ethics_reviewer",),
        ),
        _biu_position(
            "biu_case_eligibility_reviewer",
            "案例适格审查员",
            "Case Eligibility Reviewer",
            "biu_case_review",
            5,
            "P3",
            "exam",
            "判断案例是否满足学术价值、材料完整性和收录规则。",
            _BIU_CONTRIBUTOR,
        ),
        _biu_position(
            "biu_case_adaptation_editor",
            "案例改编编辑",
            "Case Adaptation Editor",
            "biu_case_editorial",
            4,
            "P1",
            "application",
            "在保持法律争点的前提下整理教学研究版本。",
            _BIU_CONTRIBUTOR,
        ),
        _biu_position(
            "biu_case_publication_editor",
            "案例发布编辑",
            "Case Publication Editor",
            "biu_case_editorial",
            4,
            "P2",
            "application",
            "检查公开版本的结构、引用、可读性与发布清单。",
            _BIU_CONTRIBUTOR,
        ),
        _biu_position(
            "biu_case_curator",
            "案例策展人",
            "Case Curator",
            "biu_case_editorial",
            5,
            "P3",
            "appointment",
            "按主题组织案例集合、导读和学习路径。",
            _BIU_CONTRIBUTOR,
        ),
        _biu_position(
            "biu_case_archivist",
            "案件档案员",
            "Case Archivist",
            "biu_case_archive",
            3,
            "P1",
            "application",
            "维护材料清单、命名、版本关系和检索信息。",
            _BIU_CONTRIBUTOR,
        ),
        _biu_position(
            "biu_archive_reviewer",
            "归档审查员",
            "Archive Reviewer",
            "biu_case_archive",
            5,
            "P3",
            "exam",
            "核对结案材料完整性并批准档案封存。",
            _BIU_ARCHIVE_REVIEWER,
            case_roles=("archive_reviewer",),
        ),
        _biu_position(
            "biu_legal_assistant",
            "法律助理",
            "Legal Assistant",
            "biu_attorney_program",
            2,
            "P1",
            "direct",
            "协助整理争点、时间线、引证和案件材料。",
            _BIU_DIRECT_CONTRIBUTOR,
            quick_registration=True,
            guest_enabled=True,
        ),
        _biu_position(
            "biu_plaintiff_attorney",
            "原告律师",
            "Plaintiff Attorney",
            "biu_attorney_program",
            4,
            "P2",
            "exam",
            "研究原告立场并形成事实、法律和救济论证。",
            _BIU_CONTRIBUTOR,
            case_roles=("plaintiff_attorney",),
            guest_enabled=True,
        ),
        _biu_position(
            "biu_defense_attorney",
            "辩护律师",
            "Defense Attorney",
            "biu_attorney_program",
            4,
            "P2",
            "exam",
            "研究辩护立场并形成事实、法律和程序论证。",
            _BIU_CONTRIBUTOR,
            case_roles=("defense_attorney",),
            guest_enabled=True,
        ),
        _biu_position(
            "biu_prosecution_attorney",
            "检方律师",
            "Prosecution Attorney",
            "biu_attorney_program",
            4,
            "P2",
            "exam",
            "研究检方立场并检验举证责任与程序正当性。",
            _BIU_CONTRIBUTOR,
            case_roles=("prosecution_attorney",),
        ),
        _biu_position(
            "biu_appellate_attorney",
            "上诉律师",
            "Appellate Attorney",
            "biu_attorney_program",
            5,
            "P2",
            "exam",
            "围绕可上诉问题形成书面理由和答辩意见。",
            _BIU_CONTRIBUTOR,
            case_roles=("appellate_attorney",),
        ),
        _biu_position(
            "biu_evidence_analyst",
            "证据分析员",
            "Evidence Analyst",
            "biu_evidence_technology",
            4,
            "P2",
            "exam",
            "构建证据目录并分析相关性、可靠性和证明关系。",
            _BIU_CONTRIBUTOR,
            case_roles=("evidence_analyst",),
            guest_enabled=True,
        ),
        _biu_position(
            "biu_discovery_specialist",
            "证据开示专员",
            "Discovery Specialist",
            "biu_evidence_technology",
            4,
            "P2",
            "exam",
            "组织证据开示请求、异议、披露记录和争议清单。",
            _BIU_CONTRIBUTOR,
            case_roles=("discovery_specialist",),
        ),
        _biu_position(
            "biu_digital_evidence_analyst",
            "数字证据分析员",
            "Digital Evidence Analyst",
            "biu_evidence_technology",
            4,
            "P2",
            "exam",
            "分析数字材料的来源、完整性、时间线和可解释性。",
            _BIU_CONTRIBUTOR,
            case_roles=("digital_evidence_analyst",),
        ),
        _biu_position(
            "biu_legal_ai_ethics_reviewer",
            "法律 AI 伦理审查员",
            "Legal AI Ethics Reviewer",
            "biu_evidence_technology",
            5,
            "P3",
            "exam",
            "审查 AI 辅助分析的偏差、可解释性、引用和责任边界。",
            _BIU_CONTRIBUTOR,
            case_roles=("ai_ethics_reviewer",),
        ),
        _biu_position(
            "biu_negotiation_facilitator",
            "协商引导员",
            "Negotiation Facilitator",
            "biu_mediation_program",
            3,
            "P1",
            "application",
            "帮助参与者澄清议题、利益和协商选项。",
            _BIU_CONTRIBUTOR,
            case_roles=("negotiation_facilitator",),
        ),
        _biu_position(
            "biu_mediator",
            "调解员",
            "Mediator",
            "biu_mediation_program",
            4,
            "P2",
            "exam",
            "主持结构化沟通并记录自愿形成的调解结果。",
            _BIU_CONTRIBUTOR,
            case_roles=("mediator",),
            guest_enabled=True,
        ),
        _biu_position(
            "biu_juror",
            "陪审员",
            "Juror",
            "biu_trial_division",
            2,
            "P1",
            "direct",
            "根据获准材料评估事实问题并提交独立意见。",
            _BIU_MEMBER,
            case_roles=("juror",),
            quick_registration=True,
            guest_enabled=True,
        ),
        _biu_position(
            "biu_court_clerk",
            "法庭书记员",
            "Court Clerk",
            "biu_trial_division",
            4,
            "P2",
            "application",
            "维护初审日程、提交清单、庭审记录和程序通知。",
            _BIU_CASE_ACTOR,
            case_roles=("court_clerk",),
        ),
        _biu_position(
            "biu_law_clerk",
            "法官助理",
            "Law Clerk",
            "biu_trial_division",
            4,
            "P2",
            "exam",
            "协助检索法律问题、整理争点并核对意见草稿。",
            _BIU_CASE_ACTOR,
            case_roles=("law_clerk",),
        ),
        _biu_position(
            "biu_trial_judge",
            "初审法官",
            "Trial Judge",
            "biu_trial_division",
            5,
            "P2",
            "exam",
            "主持初审程序、处理争议事项并形成初审意见。",
            _BIU_CASE_ACTOR,
            case_roles=("trial_judge",),
            guest_enabled=True,
        ),
        _biu_position(
            "biu_presiding_trial_judge",
            "首席初审法官",
            "Presiding Trial Judge",
            "biu_trial_division",
            6,
            "P2",
            "appointment",
            "协调合议工作、维护程序秩序并确认初审意见。",
            _BIU_CASE_ACTOR,
            case_roles=("presiding_trial_judge",),
        ),
        _biu_position(
            "biu_appellate_clerk",
            "上诉书记员",
            "Appellate Clerk",
            "biu_appellate_division",
            4,
            "P2",
            "exam",
            "管理上诉材料、审查范围、日程和意见版本。",
            _BIU_CASE_ACTOR,
            case_roles=("appellate_clerk",),
        ),
        _biu_position(
            "biu_appellate_judge",
            "上诉法官",
            "Appellate Judge",
            "biu_appellate_division",
            6,
            "P2",
            "exam",
            "审查初审记录、上诉理由和法律适用并形成意见。",
            _BIU_CASE_ACTOR,
            case_roles=("appellate_judge",),
        ),
        _biu_position(
            "biu_presiding_appellate_judge",
            "首席上诉法官",
            "Presiding Appellate Judge",
            "biu_appellate_division",
            7,
            "P2",
            "appointment",
            "协调上诉合议、处理意见分歧并确认复核范围。",
            _BIU_CASE_ACTOR,
            case_roles=("presiding_appellate_judge",),
        ),
        _biu_position(
            "biu_final_review_judge",
            "最终复核法官",
            "Final Review Judge",
            "biu_final_review_panel",
            7,
            "P2",
            "appointment",
            "对符合条件的案件进行最终复核并形成学术结论。",
            _BIU_CASE_ACTOR,
            case_roles=("final_review_judge",),
        ),
    ],
    enabled_modules=("tasks", "dashboard", "cases", "perms", "logs", "settings"),
)


# Public guest material is deliberately separate from the live CASE/RECORD
# catalogues.  Every item is fictional, contains no tenant row identifiers and
# can therefore be projected without ever opening a private case dossier.
_BIU_PUBLIC_TRAINING_CASES = (
    {
        "public_case_key": "library_window_promise",
        "case_no": "BIU-PUBLIC-001",
        "title": "图书馆窗边座位约定",
        "summary": "两支学习小组对共享阅览区的一项公开预约说明产生不同理解。",
        "matter_track": "civil_ethics",
        "difficulty": "foundation",
        "estimated_minutes": 8,
        "fictional": True,
        "learning_objectives": [
            "区分事实陈述、承诺与可执行规则",
            "识别双方共同认可与仍有争议的事实",
            "用中性语言形成可复核的学术结论",
        ],
        "roles": [
            {
                "role_key": "presiding_participant",
                "name": "主持席",
                "summary": "确认学术边界、整理争点并控制发言顺序。",
            },
            {
                "role_key": "claiming_side",
                "name": "主张方",
                "summary": "说明为何公开预约说明应当被遵守。",
            },
            {
                "role_key": "responding_side",
                "name": "回应方",
                "summary": "说明为何该说明只是协调建议而非确定承诺。",
            },
        ],
        "facts": [
            "案例完全虚构，不对应任何现实个人、学校或争议。",
            "一张公开说明写明窗边区域在周三下午保留给专题讨论。",
            "说明没有写明发布者权限，也没有写明违反后的处理方式。",
            "另一学习小组在同一时段到场，并主张公共区域应先到先用。",
        ],
        "issues": [
            "公开说明是否足以形成双方都应遵守的明确安排？",
            "发布权限、合理信赖与共享空间公平应如何衡量？",
        ],
        "hearing": {
            "title": "窗边座位学术听证",
            "steps": [
                {
                    "step_id": "scope",
                    "name": "确认边界",
                    "content": "主持席先确认这里只讨论虚构案例中的规则解释与伦理权衡。",
                    "prompt": "哪一项开场最符合 BIU 学术边界？",
                    "choices": [
                        {
                            "choice_id": "academic_only",
                            "name": "确认纯学术范围",
                            "content": "说明结论只用于本次学习，不产生任何外部效力。",
                            "feedback": "边界清楚，可以进入事实与争点整理。",
                            "next_step_id": "issues",
                        },
                        {
                            "choice_id": "promise_result",
                            "name": "先宣布胜方",
                            "content": "不听取材料，直接把说明视为最终决定。",
                            "feedback": "程序应先确认材料与争点；本练习仍继续，但需保持中立。",
                            "next_step_id": "issues",
                        },
                    ],
                },
                {
                    "step_id": "issues",
                    "name": "整理争点",
                    "content": "双方都承认说明存在，但对发布权限和约束效果意见不同。",
                    "prompt": "最适合作为核心争点的是哪一项？",
                    "choices": [
                        {
                            "choice_id": "authority_reliance",
                            "name": "权限与合理信赖",
                            "content": "审查发布者权限、文字明确程度及另一方是否合理信赖。",
                            "feedback": "该表述把共同事实与需要分析的问题分开了。",
                            "next_step_id": "close",
                        },
                        {
                            "choice_id": "group_popularity",
                            "name": "比较小组人气",
                            "content": "以哪个小组成员更多作为唯一判断标准。",
                            "feedback": "人数不是本案例给出的规则依据，应回到权限、文本与信赖。",
                            "next_step_id": "close",
                        },
                    ],
                },
                {
                    "step_id": "close",
                    "name": "形成意见",
                    "content": "主持席需要留下可复核、不过度延伸的学习结论。",
                    "prompt": "哪一种结语最合适？",
                    "choices": [
                        {
                            "choice_id": "qualified_conclusion",
                            "name": "附条件结论",
                            "content": "说明现有材料支持的判断、材料不足之处与改进预约规则的建议。",
                            "feedback": "结论区分了分析、限制与改进建议，本次听证完成。",
                            "next_step_id": None,
                        },
                        {
                            "choice_id": "external_order",
                            "name": "写成对外命令",
                            "content": "把学习意见写成对外命令。",
                            "feedback": "BIU 只形成学术意见，不产生任何外部效力。本次练习到此结束。",
                            "next_step_id": None,
                        },
                    ],
                },
            ],
        },
    },
    {
        "public_case_key": "shared_model_citation",
        "case_no": "BIU-PUBLIC-002",
        "title": "共享模型的引证争议",
        "summary": "一份团队研究笔记使用 AI 整理观点，却没有区分原始来源与模型生成摘要。",
        "matter_track": "legal_ai_ethics",
        "difficulty": "intermediate",
        "estimated_minutes": 10,
        "fictional": True,
        "learning_objectives": [
            "识别来源、摘要与推断的不同证据地位",
            "设计可追溯的引用和人工复核步骤",
            "讨论团队署名与更正责任",
        ],
        "roles": [
            {
                "role_key": "presiding_participant",
                "name": "主持席",
                "summary": "维护程序中立并确认待核查材料。",
            },
            {
                "role_key": "research_team",
                "name": "研究团队",
                "summary": "说明工具使用方式与已有人工核查。",
            },
            {
                "role_key": "ethics_reviewer",
                "name": "伦理审查席",
                "summary": "检验引用、可解释性与更正机制。",
            },
        ],
        "facts": [
            "案例、团队和资料名称均为虚构。",
            "研究笔记列出三条观点，其中两条只有模型摘要而无可定位来源。",
            "团队保留了提示词和修改记录，但未完成逐条来源核验。",
            "笔记尚未对外发布。",
        ],
        "issues": [
            "模型生成摘要能否替代可验证的原始引证？",
            "发布前需要怎样的人工复核、标注与更正记录？",
        ],
        "hearing": {
            "title": "AI 引证伦理审查会",
            "steps": [
                {
                    "step_id": "inventory",
                    "name": "材料盘点",
                    "content": "审查席先区分原文、人工摘要、模型摘要和团队推断。",
                    "prompt": "第一步应如何处理三条观点？",
                    "choices": [
                        {
                            "choice_id": "classify_sources",
                            "name": "逐条标注来源类型",
                            "content": "为每条观点标明原始来源、处理方式与复核状态。",
                            "feedback": "分类建立了可追溯起点，可以继续设计核查。",
                            "next_step_id": "verification",
                        },
                        {
                            "choice_id": "trust_fluent_text",
                            "name": "依文字流畅度判断",
                            "content": "只要表达自然，就假定引证正确。",
                            "feedback": "流畅度不能证明来源真实，仍必须逐条核验。",
                            "next_step_id": "verification",
                        },
                    ],
                },
                {
                    "step_id": "verification",
                    "name": "设计复核",
                    "content": "两条观点目前无法从笔记直接定位到原始材料。",
                    "prompt": "发布前最稳妥的步骤是什么？",
                    "choices": [
                        {
                            "choice_id": "hold_and_verify",
                            "name": "暂停发布并核验",
                            "content": "找到原始材料、保存定位信息，并由另一名成员复核。",
                            "feedback": "这同时处理了可追溯性与独立复核。",
                            "next_step_id": "responsibility",
                        },
                        {
                            "choice_id": "publish_disclaimer_only",
                            "name": "只加免责声明",
                            "content": "不核验来源，仅注明使用过 AI 后立即发布。",
                            "feedback": "透明标注有价值，但不能替代对核心引证的核验。",
                            "next_step_id": "responsibility",
                        },
                    ],
                },
                {
                    "step_id": "responsibility",
                    "name": "确认责任",
                    "content": "团队要决定由谁确认最终版本并如何保留更正记录。",
                    "prompt": "哪项安排更符合责任可追溯原则？",
                    "choices": [
                        {
                            "choice_id": "named_review_and_log",
                            "name": "实名复核与更正日志",
                            "content": "指定最终复核人，保存版本、来源与后续更正记录。",
                            "feedback": "责任与变更都可追溯，本次审查完成。",
                            "next_step_id": None,
                        },
                        {
                            "choice_id": "tool_is_responsible",
                            "name": "把责任交给工具",
                            "content": "团队不承担复核责任，全部归因于模型。",
                            "feedback": "工具不能承担团队的学术责任；本次练习到此结束。",
                            "next_step_id": None,
                        },
                    ],
                },
            ],
        },
    },
)


def get_biu_public_training_cases() -> list[dict[str, Any]]:
    """Return isolated, fictional guest fixtures for the BIU public site."""

    return deepcopy(list(_BIU_PUBLIC_TRAINING_CASES))


# BIU newcomer guidance is deliberately non-diagnostic.  The axes describe
# preferred ways of working inside this academic programme; they are not
# personality, aptitude, employment or legal-qualification findings.  Scores
# remain server-side so a public client cannot forge a preferred position.
BIU_GUIDANCE_AXES = (
    {
        "axis_id": "analysis",
        "name": "分析推理",
        "description": "从事实、规则与争点之间寻找清晰关系。",
    },
    {
        "axis_id": "evidence",
        "name": "证据辨析",
        "description": "关注来源、可靠性、完整性与引用链条。",
    },
    {
        "axis_id": "advocacy",
        "name": "立场表达",
        "description": "把一方观点组织成准确、可回应的论证。",
    },
    {
        "axis_id": "facilitation",
        "name": "沟通协调",
        "description": "帮助不同参与者听见彼此并推进对话。",
    },
    {
        "axis_id": "procedure",
        "name": "程序组织",
        "description": "维护步骤、期限、版本与材料秩序。",
    },
    {
        "axis_id": "judgment",
        "name": "独立判断",
        "description": "在不确定信息中保持中立、克制与责任意识。",
    },
)

_BIU_GUIDE_QUESTIONS = (
    {
        "question_id": "first_move",
        "prompt": "收到一份材料凌乱的新案例时，你更想先做哪件事？",
        "options": (
            {
                "option_id": "trace_sources",
                "label": "逐项核对来源、日期与版本",
                "scores": {"evidence": 2, "procedure": 1},
            },
            {
                "option_id": "frame_issue",
                "label": "先写出核心争点与双方可能立场",
                "scores": {"analysis": 2, "advocacy": 1},
            },
        ),
    },
    {
        "question_id": "disagreement",
        "prompt": "两位参与者对同一事实产生分歧时，你更自然的反应是？",
        "options": (
            {
                "option_id": "clarify_interests",
                "label": "分别澄清他们真正关心的问题",
                "scores": {"facilitation": 2, "judgment": 1},
            },
            {
                "option_id": "compare_support",
                "label": "比较各自陈述获得了哪些材料支持",
                "scores": {"evidence": 2, "analysis": 1},
            },
        ),
    },
    {
        "question_id": "best_output",
        "prompt": "完成一段工作后，哪种成果更让你有成就感？",
        "options": (
            {
                "option_id": "clear_argument",
                "label": "一份逻辑紧密、能够回应反方的意见",
                "scores": {"advocacy": 2, "analysis": 1},
            },
            {
                "option_id": "clean_record",
                "label": "一套任何人都能复核的完整记录",
                "scores": {"procedure": 2, "evidence": 1},
            },
        ),
    },
    {
        "question_id": "hearing_role",
        "prompt": "在一次结构化听证中，你更愿意承担哪类任务？",
        "options": (
            {
                "option_id": "ask_questions",
                "label": "提出问题，辨认尚未解释的矛盾",
                "scores": {"analysis": 2, "judgment": 1},
            },
            {
                "option_id": "keep_process",
                "label": "维护顺序、时间和每个人的发言机会",
                "scores": {"procedure": 2, "facilitation": 1},
            },
        ),
    },
    {
        "question_id": "uncertain_material",
        "prompt": "一份关键材料看起来可信，但出处仍不完整，你会倾向于？",
        "options": (
            {
                "option_id": "hold_conclusion",
                "label": "暂缓结论并标明目前的不确定性",
                "scores": {"judgment": 2, "evidence": 1},
            },
            {
                "option_id": "test_both_sides",
                "label": "分别检验采用与不采用它会怎样影响论证",
                "scores": {"analysis": 2, "advocacy": 1},
            },
        ),
    },
    {
        "question_id": "group_stall",
        "prompt": "小组讨论陷入重复时，你更愿意怎样推进？",
        "options": (
            {
                "option_id": "common_ground",
                "label": "总结共识、分歧和下一步可谈的选项",
                "scores": {"facilitation": 2, "procedure": 1},
            },
            {
                "option_id": "strongest_claim",
                "label": "找出双方最强主张并逐一检验",
                "scores": {"advocacy": 2, "analysis": 1},
            },
        ),
    },
    {
        "question_id": "detail_attention",
        "prompt": "阅读长篇案卷时，你通常更容易注意到什么？",
        "options": (
            {
                "option_id": "version_gaps",
                "label": "日期、版本、附件和引用之间的缺口",
                "scores": {"evidence": 2, "procedure": 1},
            },
            {
                "option_id": "reasoning_gaps",
                "label": "结论与理由之间没有说清楚的跳跃",
                "scores": {"analysis": 2, "judgment": 1},
            },
        ),
    },
    {
        "question_id": "ethical_tension",
        "prompt": "公开价值与个人隐私发生张力时，你更重视哪种做法？",
        "options": (
            {
                "option_id": "least_exposure",
                "label": "先寻找能够完成研究的最小披露方式",
                "scores": {"judgment": 2, "evidence": 1},
            },
            {
                "option_id": "transparent_process",
                "label": "建立明确规则并记录每一步取舍理由",
                "scores": {"procedure": 2, "facilitation": 1},
            },
        ),
    },
    {
        "question_id": "preferred_pace",
        "prompt": "面对有期限的任务，你更喜欢哪种节奏？",
        "options": (
            {
                "option_id": "structured_milestones",
                "label": "拆成节点，逐项确认责任人与完成条件",
                "scores": {"procedure": 2, "facilitation": 1},
            },
            {
                "option_id": "deep_focus",
                "label": "集中研究最关键的问题，再形成明确观点",
                "scores": {"analysis": 2, "advocacy": 1},
            },
        ),
    },
)


# Every public non-appointment BIU position has an explicit, reviewed fit
# profile.  The API intersects these codes with the live Warehouse catalogue;
# this map can explain a live role but can never make a stale role selectable.
BIU_GUIDANCE_POSITION_PROFILES = {
    "biu_registered_participant": ("judgment", "procedure"),
    "biu_case_observer": ("analysis", "judgment"),
    "biu_case_scout": ("evidence", "analysis"),
    "biu_public_record_researcher": ("evidence", "procedure"),
    "biu_case_intake_clerk": ("procedure", "evidence"),
    "biu_source_verification_analyst": ("evidence", "analysis"),
    "biu_ethics_privacy_reviewer": ("judgment", "evidence"),
    "biu_case_eligibility_reviewer": ("judgment", "analysis", "procedure"),
    "biu_case_adaptation_editor": ("analysis", "advocacy"),
    "biu_case_publication_editor": ("procedure", "advocacy"),
    "biu_case_archivist": ("procedure", "evidence"),
    "biu_archive_reviewer": ("procedure", "judgment"),
    "biu_legal_assistant": ("analysis", "procedure"),
    "biu_plaintiff_attorney": ("advocacy", "analysis"),
    "biu_defense_attorney": ("advocacy", "evidence"),
    "biu_prosecution_attorney": ("advocacy", "judgment", "evidence"),
    "biu_appellate_attorney": ("analysis", "advocacy", "procedure"),
    "biu_evidence_analyst": ("evidence", "analysis"),
    "biu_discovery_specialist": ("evidence", "procedure"),
    "biu_digital_evidence_analyst": ("evidence", "analysis", "procedure"),
    "biu_legal_ai_ethics_reviewer": ("judgment", "analysis", "evidence"),
    "biu_negotiation_facilitator": ("facilitation", "advocacy"),
    "biu_mediator": ("facilitation", "judgment"),
    "biu_juror": ("judgment", "evidence"),
    "biu_court_clerk": ("procedure", "facilitation"),
    "biu_law_clerk": ("analysis", "procedure"),
    "biu_trial_judge": ("judgment", "analysis", "procedure"),
    "biu_appellate_clerk": ("procedure", "analysis"),
    "biu_appellate_judge": ("analysis", "judgment", "procedure"),
}


def _biu_exam_question(question_id, prompt, options, correct, explanation):
    return {
        "question_id": question_id,
        "prompt": prompt,
        "options": tuple({"option_id": option_id, "label": label} for option_id, label in options),
        "correct_option_id": correct,
        "explanation": explanation,
    }


_BIU_EXAM_BANKS = {
    "record_integrity": {
        "title": "材料完整性预备能力测验",
        "threshold_percent": 75,
        "questions": (
            _biu_exam_question(
                "ri_source",
                "引用一份公开材料前，最先应确认什么？",
                (
                    ("a", "它是否支持自己的结论"),
                    ("b", "来源、版本、日期与取得路径"),
                    ("c", "文字是否足够简短"),
                    ("d", "是否已有其他人转发"),
                ),
                "b",
                "可复核的来源、版本、日期和取得路径是材料进入研究记录的基础。",
            ),
            _biu_exam_question(
                "ri_conflict",
                "两份材料对同一日期记载不一致，适当做法是？",
                (
                    ("a", "选择更符合预期的一份"),
                    ("b", "删除其中一份"),
                    ("c", "保留两份并记录差异与核查状态"),
                    ("d", "把日期改成相同"),
                ),
                "c",
                "应保存冲突本身及核查状态，避免用未经说明的编辑制造确定性。",
            ),
            _biu_exam_question(
                "ri_minimum",
                "判断案例材料是否足以进入下一阶段时，最重要的是？",
                (
                    ("a", "材料数量越多越好"),
                    ("b", "核心争点具有可核查事实和明确来源"),
                    ("c", "标题足够吸引人"),
                    ("d", "已经形成一致结论"),
                ),
                "b",
                "适格性关注能否围绕争点进行可复核研究，而不是材料数量或预设结论。",
            ),
            _biu_exam_question(
                "ri_version",
                "档案封存前发现附件有新版本，应怎样处理？",
                (
                    ("a", "直接覆盖旧文件"),
                    ("b", "忽略新版本"),
                    ("c", "保留版本关系并重新核对清单"),
                    ("d", "只修改文件名"),
                ),
                "c",
                "版本关系和完整清单必须可追溯，不能以覆盖方式隐藏变化。",
            ),
            _biu_exam_question(
                "ri_gap",
                "无法补齐一项非核心材料时，最佳记录方式是？",
                (
                    ("a", "假定它不存在"),
                    ("b", "不提及缺口"),
                    ("c", "明确标注缺失、影响与已采取的核查步骤"),
                    ("d", "用相似材料替代且不说明"),
                ),
                "c",
                "透明记录缺失及其影响，比制造表面完整更符合学术诚信。",
            ),
        ),
    },
    "ethical_review": {
        "title": "法律伦理与技术责任预备能力测验",
        "threshold_percent": 75,
        "questions": (
            _biu_exam_question(
                "er_minimize",
                "研究目标可以用较少个人信息完成时，应选择？",
                (
                    ("a", "仍保留全部信息"),
                    ("b", "最小必要范围并说明处理理由"),
                    ("c", "把信息复制到更多位置"),
                    ("d", "只要公开过就不再评估"),
                ),
                "b",
                "公开可见不等于可以无限使用；应遵循最小必要和目的限制。",
            ),
            _biu_exam_question(
                "er_reidentify",
                "去掉姓名后仍可由罕见经历识别当事人，应如何处理？",
                (
                    ("a", "已经删除姓名，所以无需处理"),
                    ("b", "进一步泛化或移除可组合识别线索"),
                    ("c", "增加更多细节"),
                    ("d", "仅更换字体"),
                ),
                "b",
                "去标识化需考虑信息组合后的重新识别风险，而不只是姓名字段。",
            ),
            _biu_exam_question(
                "er_ai_citation",
                "AI 给出一条看似准确但无法找到原文的引用，应怎样做？",
                (
                    ("a", "直接采用"),
                    ("b", "改写后采用"),
                    ("c", "独立核查；无法验证则不作为依据"),
                    ("d", "让 AI 重复生成"),
                ),
                "c",
                "AI 输出不能代替来源核查；无法验证的引用不应进入论证依据。",
            ),
            _biu_exam_question(
                "er_bias",
                "AI 分析对某一群体持续给出不利标签，第一步应是？",
                (
                    ("a", "认为模型必然中立"),
                    ("b", "检查数据、指标和输出差异并暂停高风险使用"),
                    ("c", "隐藏标签"),
                    ("d", "扩大自动化范围"),
                ),
                "b",
                "应先识别偏差来源和影响，在完成审查前限制高风险用途。",
            ),
            _biu_exam_question(
                "er_accountability",
                "团队使用 AI 辅助形成意见，最终责任属于？",
                (
                    ("a", "AI 工具"),
                    ("b", "没有任何人"),
                    ("c", "负责复核与发布意见的人员和团队"),
                    ("d", "软件供应商自动承担全部责任"),
                ),
                "c",
                "工具不能承担学术与专业责任；人类复核、说明和发布责任必须明确。",
            ),
        ),
    },
    "legal_advocacy": {
        "title": "法律论证预备能力测验",
        "threshold_percent": 75,
        "questions": (
            _biu_exam_question(
                "la_issue",
                "构建一方论证的合适起点是？",
                (
                    ("a", "先写结论"),
                    ("b", "明确争点、适用规则、关键事实和所求结果"),
                    ("c", "忽略不利事实"),
                    ("d", "只引用最长的材料"),
                ),
                "b",
                "清晰论证应把争点、规则、事实与所求结果连接起来。",
            ),
            _biu_exam_question(
                "la_adverse",
                "发现一项明显不利于己方的材料时，应怎样做？",
                (
                    ("a", "删除它"),
                    ("b", "准确披露并解释其证明力或适用边界"),
                    ("c", "改变日期"),
                    ("d", "攻击材料提交者"),
                ),
                "b",
                "诚实处理不利材料并回应其意义，比隐藏材料更能形成可靠论证。",
            ),
            _biu_exam_question(
                "la_burden",
                "举证责任尚未满足时，哪种表述更恰当？",
                (
                    ("a", "把怀疑写成确定事实"),
                    ("b", "说明现有证据不足及仍需证明的事项"),
                    ("c", "要求读者自行补充"),
                    ("d", "假定对方必须证明一切"),
                ),
                "b",
                "应准确说明责任、证明标准和目前证据之间的缺口。",
            ),
            _biu_exam_question(
                "la_counter",
                "回应对方最强观点时，最佳方法是？",
                (
                    ("a", "换一个话题"),
                    ("b", "准确重述后以规则和材料回应"),
                    ("c", "只评价对方动机"),
                    ("d", "重复自己的结论"),
                ),
                "b",
                "先公平呈现对方观点，再针对理由和材料作答，才能形成有效回应。",
            ),
            _biu_exam_question(
                "la_remedy",
                "讨论可能结果时，应避免什么？",
                (
                    ("a", "说明不同前提下的结果"),
                    ("b", "区分主要与备选请求"),
                    ("c", "承诺一个材料无法支持的确定结果"),
                    ("d", "说明限制"),
                ),
                "c",
                "法律研究意见应说明条件与限制，不能把预测包装为保证。",
            ),
        ),
    },
    "evidence_analysis": {
        "title": "证据分析预备能力测验",
        "threshold_percent": 75,
        "questions": (
            _biu_exam_question(
                "ea_relevance",
                "一项材料与案件主题有关，是否就足以证明主张？",
                (
                    ("a", "是，相关即充分"),
                    ("b", "否，还需评估可靠性、证明方向与其他材料"),
                    ("c", "只看文件长度"),
                    ("d", "只看提交时间"),
                ),
                "b",
                "相关性只是起点，证明力还取决于可靠性、联系强度和整体材料。",
            ),
            _biu_exam_question(
                "ea_chain",
                "数字文件在多人之间传递后，首先应补充什么？",
                (
                    ("a", "更吸引人的文件名"),
                    ("b", "来源、取得方式、传递记录和完整性校验"),
                    ("c", "更多副本"),
                    ("d", "个人猜测"),
                ),
                "b",
                "数字材料需要可追溯的来源、处理链条和完整性信息。",
            ),
            _biu_exam_question(
                "ea_scope",
                "证据开示请求怎样更合适？",
                (
                    ("a", "要求所有可能资料"),
                    ("b", "围绕争点限定对象、时间和材料类型"),
                    ("c", "不说明目的"),
                    ("d", "只使用口头要求"),
                ),
                "b",
                "清晰且成比例的范围有助于获得相关材料并减少不必要披露。",
            ),
            _biu_exam_question(
                "ea_metadata",
                "截图与原始文件内容不同，适当做法是？",
                (
                    ("a", "只保留截图"),
                    ("b", "保留两者并核查元数据、生成方式和差异"),
                    ("c", "修改原始文件"),
                    ("d", "选择更清晰的一份"),
                ),
                "b",
                "应保留原始材料和派生材料，并解释生成与差异，避免证据链断裂。",
            ),
            _biu_exam_question(
                "ea_inference",
                "时间上先后发生的两件事，是否足以证明因果关系？",
                (
                    ("a", "一定足以"),
                    ("b", "不一定，还需检验其他解释和支持材料"),
                    ("c", "取决于标题"),
                    ("d", "只要间隔很短就足以"),
                ),
                "b",
                "时间顺序可以提供线索，但不能单独排除其他原因。",
            ),
        ),
    },
    "mediation": {
        "title": "调解沟通预备能力测验",
        "threshold_percent": 75,
        "questions": (
            _biu_exam_question(
                "me_neutral",
                "调解员听到一方强烈陈述后，应首先？",
                (
                    ("a", "立即裁定谁对"),
                    ("b", "复述关切并给另一方同等表达机会"),
                    ("c", "替一方提出主张"),
                    ("d", "结束沟通"),
                ),
                "b",
                "调解重在中立地澄清关切并维持平等参与，而不是替代裁判。",
            ),
            _biu_exam_question(
                "me_interest",
                "从立场转向利益，指的是？",
                (
                    ("a", "要求放弃观点"),
                    ("b", "探索某项要求背后希望解决的问题"),
                    ("c", "隐藏分歧"),
                    ("d", "决定结果"),
                ),
                "b",
                "理解要求背后的需要，有助于发现双方可以讨论的选项。",
            ),
            _biu_exam_question(
                "me_voluntary",
                "一方表示尚未理解方案却被催促同意，应怎样处理？",
                (
                    ("a", "继续催促"),
                    ("b", "暂停并确认理解、选择和自愿性"),
                    ("c", "代替其签署"),
                    ("d", "删掉异议"),
                ),
                "b",
                "调解结果必须建立在理解与自愿之上，不能用程序压力替代同意。",
            ),
            _biu_exam_question(
                "me_confidentiality",
                "讨论中出现敏感信息时，适当做法是？",
                (
                    ("a", "立即公开"),
                    ("b", "依既定规则确认使用范围并作必要记录"),
                    ("c", "转发给无关人员"),
                    ("d", "假定没有边界"),
                ),
                "b",
                "信息使用范围应由明确规则和参与者理解共同约束。",
            ),
            _biu_exam_question(
                "me_record",
                "形成结果记录时应包括？",
                (
                    ("a", "模糊口号"),
                    ("b", "具体事项、条件、责任人与未解决问题"),
                    ("c", "调解员个人胜负评价"),
                    ("d", "未讨论的新义务"),
                ),
                "b",
                "清晰记录已同意事项及未解决问题，才能忠实反映沟通过程。",
            ),
        ),
    },
    "trial_reasoning": {
        "title": "初审研究与判断预备能力测验",
        "threshold_percent": 75,
        "questions": (
            _biu_exam_question(
                "tr_record",
                "形成初审意见时，事实基础应来自？",
                (
                    ("a", "未提交的传闻"),
                    ("b", "获准记录中可识别、可核查的材料"),
                    ("c", "个人经验替代材料"),
                    ("d", "网络评论数量"),
                ),
                "b",
                "意见应建立在获准记录之上，并让事实依据可以被复核。",
            ),
            _biu_exam_question(
                "tr_both",
                "双方对关键规则提出不同解释时，应怎样写意见？",
                (
                    ("a", "只复制一方"),
                    ("b", "公平呈现主要解释并说明采纳理由"),
                    ("c", "忽略规则"),
                    ("d", "不写理由"),
                ),
                "b",
                "可理解的判断需要回应主要论点并公开说明推理路径。",
            ),
            _biu_exam_question(
                "tr_conflict",
                "发现自己与参与者存在可能影响中立的关系，应？",
                (
                    ("a", "隐瞒"),
                    ("b", "及时披露并依规则评估是否回避"),
                    ("c", "让参与者猜测"),
                    ("d", "删除记录"),
                ),
                "b",
                "利益冲突应透明披露并依既定程序处理。",
            ),
            _biu_exam_question(
                "tr_uncertainty",
                "材料不足以支持确定事实时，应？",
                (
                    ("a", "补写想象内容"),
                    ("b", "说明证明不足及其对结论的影响"),
                    ("c", "提高语气强度"),
                    ("d", "改变证明标准"),
                ),
                "b",
                "判断者必须正视不确定性，而不能用措辞替代证据。",
            ),
            _biu_exam_question(
                "tr_scope",
                "处理一个未由双方充分讨论的新问题时，较适当的是？",
                (
                    ("a", "直接作不利结论"),
                    ("b", "给予适当通知与回应机会"),
                    ("c", "仅私下询问一方"),
                    ("d", "隐藏问题来源"),
                ),
                "b",
                "程序公平要求受影响参与者知道问题并获得合理回应机会。",
            ),
        ),
    },
    "appellate_review": {
        "title": "上诉审查预备能力测验",
        "threshold_percent": 75,
        "questions": (
            _biu_exam_question(
                "ar_scope",
                "上诉审查的第一项程序任务通常是？",
                (
                    ("a", "重新收集所有事实"),
                    ("b", "确认可审查问题、记录范围和适用标准"),
                    ("c", "直接宣布结果"),
                    ("d", "忽略初审意见"),
                ),
                "b",
                "审查范围和标准决定上诉机构能够处理什么以及如何处理。",
            ),
            _biu_exam_question(
                "ar_preserve",
                "某项理由在初审记录中没有提出，审查时应？",
                (
                    ("a", "自动视为已提出"),
                    ("b", "依规则分析是否保留、放弃或属于例外"),
                    ("c", "删除初审记录"),
                    ("d", "只看理由是否有趣"),
                ),
                "b",
                "上诉审查应明确处理保留与例外问题，不能绕开程序历史。",
            ),
            _biu_exam_question(
                "ar_error",
                "发现初审理由有错误，是否必然改变结果？",
                (
                    ("a", "必然"),
                    ("b", "不一定，还需分析错误是否影响结果"),
                    ("c", "从不影响"),
                    ("d", "只由篇幅决定"),
                ),
                "b",
                "需要区分错误存在与错误是否具有结果影响。",
            ),
            _biu_exam_question(
                "ar_deference",
                "审查事实判断与法律问题时应？",
                (
                    ("a", "始终使用同一标准"),
                    ("b", "依问题类型采用相应审查标准并说明"),
                    ("c", "只看最终结论"),
                    ("d", "由个人偏好决定"),
                ),
                "b",
                "不同问题可能适用不同审查强度，意见应公开说明所用标准。",
            ),
            _biu_exam_question(
                "ar_disposition",
                "上诉意见的处理结果应当？",
                (
                    ("a", "只写胜负"),
                    ("b", "说明维持、撤销、变更或发回的范围与理由"),
                    ("c", "加入未讨论的新事实"),
                    ("d", "省略后续步骤"),
                ),
                "b",
                "清楚的处理范围和理由能让后续程序知道哪些事项已经解决。",
            ),
        ),
    },
}


_BIU_EXAM_CORRECT_SLOT_PLAN = {
    "record_integrity": (1, 3, 0, 2, 0),
    "ethical_review": (2, 0, 3, 1, 0),
    "legal_advocacy": (3, 1, 0, 2, 1),
    "evidence_analysis": (0, 2, 1, 3, 1),
    "mediation": (1, 3, 2, 0, 2),
    "trial_reasoning": (2, 0, 3, 1, 2),
    "appellate_review": (3, 1, 0, 2, 3),
}


def _biu_exam_bank_with_balanced_slots(bank_id, bank):
    """Keep answer ids stable while balancing their visible option slots."""

    questions = tuple(bank.get("questions") or ())
    slots = _BIU_EXAM_CORRECT_SLOT_PLAN.get(bank_id) or ()
    if len(slots) != len(questions):
        raise ValueError(f"BIU exam slot plan does not cover {bank_id}")
    balanced_questions = []
    for question, target_slot in zip(questions, slots):
        options = list(question.get("options") or ())
        correct_option = next(
            option
            for option in options
            if option.get("option_id") == question.get("correct_option_id")
        )
        remaining = [option for option in options if option is not correct_option]
        if not (0 <= target_slot <= len(remaining)):
            raise ValueError(f"BIU exam slot plan is invalid for {bank_id}")
        remaining.insert(target_slot, correct_option)
        balanced_questions.append({**question, "options": tuple(remaining)})
    return {**bank, "questions": tuple(balanced_questions)}


_BIU_EXAM_BANKS = {
    bank_id: _biu_exam_bank_with_balanced_slots(bank_id, bank)
    for bank_id, bank in _BIU_EXAM_BANKS.items()
}


BIU_EXAM_POSITION_BANKS = {
    "biu_source_verification_analyst": "record_integrity",
    "biu_ethics_privacy_reviewer": "ethical_review",
    "biu_case_eligibility_reviewer": "record_integrity",
    "biu_archive_reviewer": "record_integrity",
    "biu_plaintiff_attorney": "legal_advocacy",
    "biu_defense_attorney": "legal_advocacy",
    "biu_prosecution_attorney": "legal_advocacy",
    "biu_appellate_attorney": "legal_advocacy",
    "biu_evidence_analyst": "evidence_analysis",
    "biu_discovery_specialist": "evidence_analysis",
    "biu_digital_evidence_analyst": "evidence_analysis",
    "biu_legal_ai_ethics_reviewer": "ethical_review",
    "biu_mediator": "mediation",
    "biu_law_clerk": "trial_reasoning",
    "biu_trial_judge": "trial_reasoning",
    "biu_appellate_clerk": "appellate_review",
    "biu_appellate_judge": "appellate_review",
}


def get_biu_guide_definition() -> dict[str, Any]:
    """Return the internal, scored newcomer guide definition."""

    return {
        "guide_id": "biu_role_compass_v1",
        "axes": deepcopy(list(BIU_GUIDANCE_AXES)),
        "questions": deepcopy(list(_BIU_GUIDE_QUESTIONS)),
    }


def get_biu_guidance_position_profiles() -> dict[str, tuple[str, ...]]:
    """Return reviewed axis affinities keyed by permanent BIU position."""

    return deepcopy(BIU_GUIDANCE_POSITION_PROFILES)


def get_biu_exam_bank(position_code: str) -> Optional[dict[str, Any]]:
    """Return one internal answer-key bank for an exact BIU exam position."""

    bank_id = BIU_EXAM_POSITION_BANKS.get(str(position_code or "").strip())
    bank = _BIU_EXAM_BANKS.get(bank_id) if bank_id else None
    if bank is None:
        return None
    return {"bank_id": bank_id, **deepcopy(bank)}


def _biu_learning_identifier(value: Any) -> bool:
    text = str(value or "")
    return (
        1 <= len(text) <= 80
        and text[0] in "abcdefghijklmnopqrstuvwxyz"
        and all(character in "abcdefghijklmnopqrstuvwxyz0123456789_" for character in text)
    )


def _validate_biu_learning_definitions(
    position_by_code: Mapping[str, Mapping[str, Any]],
    prefix: str,
) -> list[str]:
    """Validate the non-authorizing guide and preparatory assessment SSOT."""

    errors: list[str] = []
    axes: dict[str, Mapping[str, Any]] = {}
    if not isinstance(BIU_GUIDANCE_AXES, (list, tuple)) or not (4 <= len(BIU_GUIDANCE_AXES) <= 8):
        errors.append(f"{prefix}.biu_guidance.axes: expected 4 to 8 axes")
    else:
        for index, axis in enumerate(BIU_GUIDANCE_AXES):
            item_prefix = f"{prefix}.biu_guidance.axes[{index}]"
            if not isinstance(axis, Mapping):
                errors.append(f"{item_prefix}: expected a mapping")
                continue
            axis_id = axis.get("axis_id")
            if not _biu_learning_identifier(axis_id):
                errors.append(f"{item_prefix}.axis_id: invalid identifier")
                continue
            axis_id = str(axis_id)
            if axis_id in axes:
                errors.append(f"{prefix}.biu_guidance.axes: duplicate id {axis_id!r}")
            axes[axis_id] = axis
            for field in ("name", "description"):
                if not _non_empty_string(axis.get(field)):
                    errors.append(f"{item_prefix}.{field}: must be a non-empty string")

    guide = get_biu_guide_definition()
    questions = guide.get("questions")
    if not isinstance(questions, (list, tuple)) or not (8 <= len(questions) <= 10):
        errors.append(f"{prefix}.biu_guidance.questions: expected 8 to 10 questions")
        questions = []
    question_ids: set[str] = set()
    for index, question in enumerate(questions):
        item_prefix = f"{prefix}.biu_guidance.questions[{index}]"
        if not isinstance(question, Mapping):
            errors.append(f"{item_prefix}: expected a mapping")
            continue
        question_id = question.get("question_id")
        if not _biu_learning_identifier(question_id):
            errors.append(f"{item_prefix}.question_id: invalid identifier")
        elif str(question_id) in question_ids:
            errors.append(f"{prefix}.biu_guidance.questions: duplicate id {question_id!r}")
        else:
            question_ids.add(str(question_id))
        if not _non_empty_string(question.get("prompt")):
            errors.append(f"{item_prefix}.prompt: must be a non-empty string")
        options = question.get("options")
        if not isinstance(options, (list, tuple)) or len(options) != 2:
            errors.append(f"{item_prefix}.options: expected exactly two options")
            continue
        option_ids: set[str] = set()
        for option_index, option in enumerate(options):
            option_prefix = f"{item_prefix}.options[{option_index}]"
            if not isinstance(option, Mapping):
                errors.append(f"{option_prefix}: expected a mapping")
                continue
            option_id = option.get("option_id")
            if not _biu_learning_identifier(option_id):
                errors.append(f"{option_prefix}.option_id: invalid identifier")
            elif str(option_id) in option_ids:
                errors.append(f"{item_prefix}.options: duplicate id {option_id!r}")
            else:
                option_ids.add(str(option_id))
            if not _non_empty_string(option.get("label")):
                errors.append(f"{option_prefix}.label: must be a non-empty string")
            scores = option.get("scores")
            if not isinstance(scores, Mapping) or not scores:
                errors.append(f"{option_prefix}.scores: expected a non-empty mapping")
                continue
            unknown_axes = set(scores).difference(axes)
            if unknown_axes:
                errors.append(f"{option_prefix}.scores: unknown axes {sorted(unknown_axes)!r}")
            if any(type(score) is not int or not (1 <= score <= 3) for score in scores.values()):
                errors.append(f"{option_prefix}.scores: values must be integers from 1 to 3")

    expected_profiles = {
        code
        for code, position in position_by_code.items()
        if isinstance(position.get("public_entry"), Mapping)
        and position["public_entry"].get("mode") in {"direct", "application", "exam"}
        and position["public_entry"].get("visibility") != "hidden"
    }
    actual_profiles = set(BIU_GUIDANCE_POSITION_PROFILES)
    if actual_profiles != expected_profiles:
        errors.append(
            f"{prefix}.biu_guidance.position_profiles: expected exact public "
            f"non-appointment coverage; missing={sorted(expected_profiles - actual_profiles)!r}, "
            f"extra={sorted(actual_profiles - expected_profiles)!r}"
        )
    for code, affinity in BIU_GUIDANCE_POSITION_PROFILES.items():
        item_prefix = f"{prefix}.biu_guidance.position_profiles[{code!r}]"
        if not isinstance(affinity, (list, tuple)) or not (2 <= len(affinity) <= 3):
            errors.append(f"{item_prefix}: expected two or three axes")
            continue
        if len(affinity) != len(set(affinity)):
            errors.append(f"{item_prefix}: contains duplicate axes")
        unknown_axes = set(affinity).difference(axes)
        if unknown_axes:
            errors.append(f"{item_prefix}: unknown axes {sorted(unknown_axes)!r}")

    expected_exam_positions = {
        code
        for code, position in position_by_code.items()
        if isinstance(position.get("public_entry"), Mapping)
        and position["public_entry"].get("mode") == "exam"
    }
    actual_exam_positions = set(BIU_EXAM_POSITION_BANKS)
    if actual_exam_positions != expected_exam_positions:
        errors.append(
            f"{prefix}.biu_exams.position_banks: expected exact exam-position "
            f"coverage; missing={sorted(expected_exam_positions - actual_exam_positions)!r}, "
            f"extra={sorted(actual_exam_positions - expected_exam_positions)!r}"
        )
    used_banks = set(BIU_EXAM_POSITION_BANKS.values())
    defined_banks = set(_BIU_EXAM_BANKS)
    if used_banks != defined_banks:
        errors.append(
            f"{prefix}.biu_exams.banks: missing={sorted(used_banks - defined_banks)!r}, "
            f"unused={sorted(defined_banks - used_banks)!r}"
        )
    for bank_id, bank in _BIU_EXAM_BANKS.items():
        item_prefix = f"{prefix}.biu_exams.banks[{bank_id!r}]"
        if not _biu_learning_identifier(bank_id):
            errors.append(f"{item_prefix}: invalid bank identifier")
        if not isinstance(bank, Mapping):
            errors.append(f"{item_prefix}: expected a mapping")
            continue
        if not _non_empty_string(bank.get("title")):
            errors.append(f"{item_prefix}.title: must be a non-empty string")
        threshold = bank.get("threshold_percent")
        if type(threshold) is not int or not (60 <= threshold <= 100):
            errors.append(f"{item_prefix}.threshold_percent: expected integer from 60 to 100")
        bank_questions = bank.get("questions")
        if not isinstance(bank_questions, (list, tuple)) or not (4 <= len(bank_questions) <= 12):
            errors.append(f"{item_prefix}.questions: expected 4 to 12 questions")
            continue
        bank_question_ids: set[str] = set()
        for question_index, question in enumerate(bank_questions):
            question_prefix = f"{item_prefix}.questions[{question_index}]"
            if not isinstance(question, Mapping):
                errors.append(f"{question_prefix}: expected a mapping")
                continue
            question_id = question.get("question_id")
            if not _biu_learning_identifier(question_id):
                errors.append(f"{question_prefix}.question_id: invalid identifier")
            elif str(question_id) in bank_question_ids:
                errors.append(f"{item_prefix}.questions: duplicate id {question_id!r}")
            else:
                bank_question_ids.add(str(question_id))
            if not _non_empty_string(question.get("prompt")):
                errors.append(f"{question_prefix}.prompt: must be a non-empty string")
            if not _non_empty_string(question.get("explanation")):
                errors.append(f"{question_prefix}.explanation: must be a non-empty string")
            options = question.get("options")
            if not isinstance(options, (list, tuple)) or not (3 <= len(options) <= 5):
                errors.append(f"{question_prefix}.options: expected 3 to 5 options")
                continue
            option_ids: set[str] = set()
            for option_index, option in enumerate(options):
                option_prefix = f"{question_prefix}.options[{option_index}]"
                if not isinstance(option, Mapping):
                    errors.append(f"{option_prefix}: expected a mapping")
                    continue
                option_id = option.get("option_id")
                if not _biu_learning_identifier(option_id):
                    errors.append(f"{option_prefix}.option_id: invalid identifier")
                elif str(option_id) in option_ids:
                    errors.append(f"{question_prefix}.options: duplicate id {option_id!r}")
                else:
                    option_ids.add(str(option_id))
                if not _non_empty_string(option.get("label")):
                    errors.append(f"{option_prefix}.label: must be a non-empty string")
            if question.get("correct_option_id") not in option_ids:
                errors.append(f"{question_prefix}.correct_option_id: unknown option")

    return errors


# Keep this public catalogue immutable.  It matches INDUSTRY_TEMPLATES in
# ai_service.py; changing the order does not change blueprint semantics.
INDUSTRY_BLUEPRINT_KEYS = (
    "generic_warehouse",
    "power_system",
    "manufacturing_factory",
    "construction_site",
    "restaurant_kitchen",
    "medical_clinic",
    "retail_store",
    "logistics_express",
    "research_lab",
    "hotel_homestay",
    "it_office_asset",
    "film_equipment",
    "biu_legal_ethics_case_lab",
)


class BlueprintValidationError(ValueError):
    """Raised by :func:`assert_valid_blueprints` with every validation error."""

    def __init__(self, errors: Iterable[str]):
        self.errors = tuple(errors)
        super().__init__("invalid industry organisation blueprints:\n- " + "\n- ".join(self.errors))


def _require_schema_version(schema_version: int) -> None:
    if schema_version != BLUEPRINT_SCHEMA_VERSION:
        raise ValueError(
            f"unsupported blueprint schema version {schema_version!r}; "
            f"supported version is {BLUEPRINT_SCHEMA_VERSION}"
        )


def get_blueprint(
    template_key: str,
    *,
    schema_version: int = BLUEPRINT_SCHEMA_VERSION,
    fallback_to_generic: bool = False,
) -> dict[str, Any]:
    """Return an isolated blueprint for ``template_key``.

    Unknown keys fail closed by default.  Migration/import callers that need
    legacy behaviour may explicitly request the generic fallback.
    """

    _require_schema_version(schema_version)
    key = str(template_key or "").strip()
    blueprint = _BLUEPRINTS.get(key)
    if blueprint is None and fallback_to_generic:
        blueprint = _BLUEPRINTS[DEFAULT_BLUEPRINT_KEY]
    if blueprint is None:
        raise KeyError(f"unknown industry organisation blueprint: {key!r}")
    return deepcopy(blueprint)


def get_all_blueprints(
    *, schema_version: int = BLUEPRINT_SCHEMA_VERSION
) -> dict[str, dict[str, Any]]:
    """Return a deep-copied mapping containing every industry blueprint."""

    _require_schema_version(schema_version)
    return {key: deepcopy(_BLUEPRINTS[key]) for key in INDUSTRY_BLUEPRINT_KEYS}


def list_blueprints(*, schema_version: int = BLUEPRINT_SCHEMA_VERSION) -> list[dict[str, Any]]:
    """Return deep-copied catalogue metadata without the large organisation lists."""

    _require_schema_version(schema_version)
    return [
        {
            "key": key,
            "name": _BLUEPRINTS[key]["name"],
            "description": _BLUEPRINTS[key]["description"],
            "schema_version": _BLUEPRINTS[key]["schema_version"],
            "revision": _BLUEPRINTS[key]["revision"],
            "department_count": len(_BLUEPRINTS[key]["departments"]),
            "position_count": len(_BLUEPRINTS[key]["positions"]),
        }
        for key in INDUSTRY_BLUEPRINT_KEYS
    ]


def _blueprint_value(blueprint_or_key: Any) -> Mapping[str, Any]:
    if isinstance(blueprint_or_key, str):
        return get_blueprint(blueprint_or_key)
    if not isinstance(blueprint_or_key, Mapping):
        raise TypeError("blueprint must be a template key or mapping")
    return blueprint_or_key


def blueprint_nav_defaults(blueprint_or_key: Any) -> dict[str, list[str]]:
    """Derive each position's default navigation from its permissions.

    The industry-level ``enabled_modules`` list is an additional feature
    boundary.  A position can never acquire a module that the selected
    blueprint has disabled, even if its role contains the matching capability.
    """
    blueprint = _blueprint_value(blueprint_or_key)
    enabled = set(blueprint.get("enabled_modules") or V2_NAV_MODULE_IDS)
    return {
        str(position["code"]): [
            module_id
            for module_id in nav_modules_for_permissions(position.get("permissions") or ())
            if module_id in enabled
        ]
        for position in blueprint.get("positions") or ()
    }


def blueprint_nav_ceilings(blueprint_or_key: Any) -> dict[str, list[str]]:
    """Return each department's subtree navigation ceiling.

    Every position contributes its derived default to its own department and
    all ancestors.  This keeps a parent broad enough for every child while
    still giving leaf departments a least-privilege industry preset.
    """
    blueprint = _blueprint_value(blueprint_or_key)
    parent_by_code = {
        str(department["code"]): str(department.get("parent") or "company")
        for department in blueprint.get("departments") or ()
        if department.get("type") != "company"
    }
    ceilings: dict[str, set[str]] = {
        str(department["code"]): set() for department in blueprint.get("departments") or ()
    }
    ceilings.setdefault("company", set())
    defaults = blueprint_nav_defaults(blueprint)
    for position in blueprint.get("positions") or ():
        modules = set(defaults.get(str(position["code"]), ()))
        cursor = str(position["department"])
        visited: set[str] = set()
        while cursor and cursor not in visited:
            visited.add(cursor)
            ceilings.setdefault(cursor, set()).update(modules)
            if cursor == "company":
                break
            cursor = parent_by_code.get(cursor, "company")
    order = {module_id: index for index, module_id in enumerate(_DEFAULT_ENABLED_MODULES)}
    return {
        code: sorted(modules, key=lambda module_id: order[module_id])
        for code, modules in ceilings.items()
    }


def blueprint_permission_ceilings(blueprint_or_key: Any) -> dict[str, list[str]]:
    """Derive department permission envelopes from the positions they contain.

    The template does not encode a second, hand-maintained policy table.  A
    department receives the union of the reviewed job capabilities in its
    subtree, and every ancestor receives the same contribution.  This keeps
    the preset explainable and prevents department and position rules from
    silently drifting apart.
    """
    blueprint = _blueprint_value(blueprint_or_key)
    parent_by_code = {
        str(department["code"]): str(department.get("parent") or "company")
        for department in blueprint.get("departments") or ()
        if department.get("type") != "company"
    }
    ceilings: dict[str, set[str]] = {
        str(department["code"]): set() for department in blueprint.get("departments") or ()
    }
    ceilings.setdefault("company", set())
    for position in blueprint.get("positions") or ():
        permissions = {
            str(permission)
            for permission in position.get("permissions") or ()
            if str(permission).strip()
        }
        cursor = str(position["department"])
        visited: set[str] = set()
        while cursor and cursor not in visited:
            visited.add(cursor)
            ceilings.setdefault(cursor, set()).update(permissions)
            if cursor == "company":
                break
            cursor = parent_by_code.get(cursor, "company")
    return {code: sorted(permissions) for code, permissions in ceilings.items()}


def _normalise_blueprint_input(
    blueprints: Optional[Any], errors: list[str]
) -> list[tuple[str, Any]]:
    if blueprints is None:
        return [(key, _BLUEPRINTS[key]) for key in INDUSTRY_BLUEPRINT_KEYS]
    if isinstance(blueprints, Mapping):
        # Also accept one blueprint, not only a key -> blueprint mapping.
        if "departments" in blueprints and "positions" in blueprints:
            key = str(blueprints.get("key") or "<missing-key>")
            return [(key, blueprints)]
        return [(str(key), value) for key, value in blueprints.items()]
    if isinstance(blueprints, (list, tuple)):
        result: list[tuple[str, Any]] = []
        for index, value in enumerate(blueprints):
            if isinstance(value, Mapping):
                key = str(value.get("key") or f"<index-{index}>")
            else:
                key = f"<index-{index}>"
            result.append((key, value))
        return result
    errors.append("blueprints: expected a mapping, list, tuple, single blueprint, or None")
    return []


def _non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def validate_blueprints(
    blueprints: Optional[Any] = None,
    allowed_permissions: Optional[Iterable[str]] = None,
) -> list[str]:
    """Validate blueprints and return all errors (an empty list means valid).

    ``allowed_permissions`` may be the service's live permission set, including
    newly installed capabilities.  When omitted, the safe built-in blueprint
    permission catalogue is used.
    """

    errors: list[str] = []
    items = _normalise_blueprint_input(blueprints, errors)
    allowed = set(BLUEPRINT_PERMISSION_KEYS if allowed_permissions is None else allowed_permissions)
    seen_blueprint_keys: set[str] = set()
    global_position_owners: dict[str, str] = {}
    global_department_names: dict[str, tuple[str, str]] = {}

    for input_key, blueprint in items:
        prefix = f"blueprint[{input_key!r}]"
        if input_key in seen_blueprint_keys:
            errors.append(f"{prefix}: duplicate blueprint key")
        seen_blueprint_keys.add(input_key)
        if not isinstance(blueprint, Mapping):
            errors.append(f"{prefix}: expected a mapping")
            continue

        declared_key = blueprint.get("key")
        if not _non_empty_string(declared_key):
            errors.append(f"{prefix}.key: must be a non-empty string")
        elif str(declared_key) != input_key:
            errors.append(f"{prefix}.key: declared key {declared_key!r} does not match mapping key")
        if blueprint.get("schema_version") != BLUEPRINT_SCHEMA_VERSION:
            errors.append(
                f"{prefix}.schema_version: expected {BLUEPRINT_SCHEMA_VERSION}, "
                f"got {blueprint.get('schema_version')!r}"
            )
        if not _non_empty_string(blueprint.get("revision")):
            errors.append(f"{prefix}.revision: must be a non-empty string")
        for field in ("name", "description"):
            if not _non_empty_string(blueprint.get(field)):
                errors.append(f"{prefix}.{field}: must be a non-empty string")

        departments = blueprint.get("departments")
        if not isinstance(departments, (list, tuple)):
            errors.append(f"{prefix}.departments: must be a list or tuple")
            departments = []
        department_codes: set[str] = set()
        parent_by_code: dict[str, Optional[str]] = {}
        company_count = 0
        for index, department in enumerate(departments):
            item_prefix = f"{prefix}.departments[{index}]"
            if not isinstance(department, Mapping):
                errors.append(f"{item_prefix}: expected a mapping")
                continue
            code = department.get("code")
            if not _non_empty_string(code):
                errors.append(f"{item_prefix}.code: must be a non-empty string")
                continue
            code = str(code)
            if code in department_codes:
                errors.append(f"{prefix}.departments: duplicate code {code!r}")
            department_codes.add(code)
            department_name = department.get("name")
            previous_department = global_department_names.get(code)
            if (
                previous_department
                and previous_department[0] != input_key
                and _non_empty_string(department_name)
                and previous_department[1] != str(department_name)
            ):
                errors.append(
                    f"{item_prefix}.code: {code!r} is also used by "
                    f"blueprint {previous_department[0]!r} for a different department"
                )
            elif _non_empty_string(department_name):
                global_department_names.setdefault(code, (input_key, str(department_name)))
            parent = department.get("parent")
            if parent is not None and not _non_empty_string(parent):
                errors.append(f"{item_prefix}.parent: must be null or a non-empty string")
            parent_by_code[code] = str(parent) if _non_empty_string(parent) else None
            for field in ("name", "description"):
                if not _non_empty_string(department.get(field)):
                    errors.append(f"{item_prefix}.{field}: must be a non-empty string")
            if (
                input_key == BIU_TEMPLATE_KEY
                and not _non_empty_string(department.get("name_en"))
                and code != "company"
            ):
                errors.append(f"{item_prefix}.name_en: must be a non-empty string")
            unit_type = department.get("type")
            if unit_type not in VALID_DEPARTMENT_TYPES:
                errors.append(f"{item_prefix}.type: unknown department type {unit_type!r}")
            if unit_type == "company":
                company_count += 1
                if parent is not None:
                    errors.append(f"{item_prefix}.parent: company root must not have a parent")
        if company_count != 1:
            errors.append(f"{prefix}.departments: expected exactly one company root")
        for code, parent in parent_by_code.items():
            if parent is not None and parent not in department_codes:
                errors.append(
                    f"{prefix}.departments[{code!r}].parent: unknown department {parent!r}"
                )

        # Parent cycles would make an organisation tree impossible to seed.
        reported_cycles: set[frozenset[str]] = set()
        for start in parent_by_code:
            order: list[str] = []
            indexes: dict[str, int] = {}
            current: Optional[str] = start
            while current is not None and current in parent_by_code:
                if current in indexes:
                    cycle = frozenset(order[indexes[current] :])
                    if cycle and cycle not in reported_cycles:
                        errors.append(
                            f"{prefix}.departments: parent cycle involving "
                            + ", ".join(sorted(cycle))
                        )
                        reported_cycles.add(cycle)
                    break
                indexes[current] = len(order)
                order.append(current)
                current = parent_by_code[current]

        positions = blueprint.get("positions")
        if not isinstance(positions, (list, tuple)):
            errors.append(f"{prefix}.positions: must be a list or tuple")
            positions = []
        position_codes: set[str] = set()
        position_by_code: dict[str, Mapping[str, Any]] = {}
        for index, position in enumerate(positions):
            item_prefix = f"{prefix}.positions[{index}]"
            if not isinstance(position, Mapping):
                errors.append(f"{item_prefix}: expected a mapping")
                continue
            code = position.get("code")
            if not _non_empty_string(code):
                errors.append(f"{item_prefix}.code: must be a non-empty string")
                continue
            code = str(code)
            if code in position_codes:
                errors.append(f"{prefix}.positions: duplicate code {code!r}")
            position_codes.add(code)
            previous_owner = global_position_owners.get(code)
            if previous_owner and previous_owner != input_key:
                errors.append(
                    f"{item_prefix}.code: {code!r} is already used by "
                    f"blueprint {previous_owner!r}; position codes must be globally unique"
                )
            else:
                global_position_owners.setdefault(code, input_key)
            position_by_code[code] = position
            for field in ("name", "role_name"):
                if not _non_empty_string(position.get(field)):
                    errors.append(f"{item_prefix}.{field}: must be a non-empty string")
            department = position.get("department")
            if not _non_empty_string(department) or department not in department_codes:
                errors.append(f"{item_prefix}.department: unknown department {department!r}")
            level = position.get("level")
            if type(level) is not int or not 1 <= level <= 10:
                errors.append(f"{item_prefix}.level: must be an integer from 1 to 10")
            if type(position.get("is_manager")) is not bool:
                errors.append(f"{item_prefix}.is_manager: must be a boolean")

            database_access_mode = position.get("database_access_mode")
            if database_access_mode is not None and not (
                input_key == BIU_TEMPLATE_KEY
                and code == str(blueprint.get("admin_position_code") or "")
                and database_access_mode == "tenant_scoped"
            ):
                errors.append(
                    f"{item_prefix}.database_access_mode: tenant_scoped is reserved for the BIU system administrator"
                )

            database_access = position.get("database_access")
            if not isinstance(database_access, Mapping):
                errors.append(f"{item_prefix}.database_access: must be a mapping")
            else:
                access_domains: dict[str, set[str]] = {}
                for access_kind in ("read", "write", "schema"):
                    raw_domains = database_access.get(access_kind)
                    field_prefix = f"{item_prefix}.database_access.{access_kind}"
                    if not isinstance(raw_domains, (list, tuple)):
                        errors.append(f"{field_prefix}: must be a list or tuple")
                        continue
                    domain_list = list(raw_domains)
                    domains: set[str] = set()
                    duplicate_found = False
                    for domain in domain_list:
                        if not _non_empty_string(domain):
                            errors.append(f"{field_prefix}: contains an invalid domain")
                            continue
                        domain = str(domain)
                        if domain in domains:
                            duplicate_found = True
                        domains.add(domain)
                        own_department_domain = f"department:{department}"
                        if domain == "*":
                            if not (
                                position.get("role_name") == "系統管理員"
                                and code == str(blueprint.get("admin_position_code") or "")
                            ):
                                errors.append(
                                    f"{field_prefix}: wildcard is reserved for the designated 系統管理員 position"
                                )
                        elif domain not in DB_NATIVE_DOMAINS and domain != own_department_domain:
                            errors.append(
                                f"{field_prefix}: domain {domain!r} is outside the position's business scope"
                            )
                    if duplicate_found:
                        errors.append(f"{field_prefix}: contains duplicate domains")
                    access_domains[access_kind] = domains

                if database_access.get("business_write") is not True:
                    errors.append(f"{item_prefix}.database_access.business_write: must be true")
                if not _non_empty_string(database_access.get("source")):
                    errors.append(
                        f"{item_prefix}.database_access.source: must be a non-empty string"
                    )

                read_domains = access_domains.get("read", set())
                write_domains = access_domains.get("write", set())
                schema_domains = access_domains.get("schema", set())
                if not read_domains:
                    errors.append(f"{item_prefix}.database_access.read: must not be empty")
                if write_domains - read_domains:
                    errors.append(f"{item_prefix}.database_access.write: must be a subset of read")
                if schema_domains - write_domains:
                    errors.append(
                        f"{item_prefix}.database_access.schema: must be a subset of write"
                    )
                if position.get("is_manager") is True:
                    if not write_domains or not schema_domains:
                        errors.append(
                            f"{item_prefix}.database_access: managers require non-empty write and schema scopes"
                        )
                elif write_domains or schema_domains:
                    errors.append(
                        f"{item_prefix}.database_access: non-managers must not receive raw write or schema scopes"
                    )

                if _non_empty_string(department) and type(position.get("is_manager")) is bool:
                    expected_access = _database_access(
                        str(department),
                        str(position.get("role_name") or ""),
                        bool(position.get("is_manager")),
                        (
                            position.get("permissions") or ()
                            if isinstance(
                                position.get("permissions"),
                                (list, tuple, set, frozenset),
                            )
                            else ()
                        ),
                        (str(database_access_mode) if database_access_mode is not None else None),
                    )
                    for access_kind in ("read", "write", "schema"):
                        expected_domains = set(expected_access[access_kind])
                        if access_domains.get(access_kind, set()) != expected_domains:
                            errors.append(
                                f"{item_prefix}.database_access.{access_kind}: expected "
                                f"{sorted(expected_domains)!r}"
                            )
                    if database_access.get("source") != expected_access["source"]:
                        errors.append(
                            f"{item_prefix}.database_access.source: expected "
                            f"{expected_access['source']!r}"
                        )

            permissions = position.get("permissions")
            if not isinstance(permissions, (list, tuple, set, frozenset)):
                errors.append(f"{item_prefix}.permissions: must be a collection")
                continue
            permission_list = list(permissions)
            if len(permission_list) != len(set(permission_list)):
                errors.append(f"{item_prefix}.permissions: contains duplicate keys")
            for permission in permission_list:
                if not _non_empty_string(permission):
                    errors.append(f"{item_prefix}.permissions: contains an invalid permission key")
                elif permission not in allowed:
                    errors.append(f"{item_prefix}.permissions: unknown permission {permission!r}")

            if input_key == BIU_TEMPLATE_KEY:
                if not _non_empty_string(position.get("name_en")):
                    errors.append(f"{item_prefix}.name_en: must be a non-empty string")
                permission_tier = position.get("permission_tier")
                if permission_tier not in BIU_PERMISSION_TIERS:
                    errors.append(
                        f"{item_prefix}.permission_tier: unknown tier {permission_tier!r}"
                    )
                public_entry = position.get("public_entry")
                entry_mode: Any = None
                visibility: Any = None
                if not isinstance(public_entry, Mapping):
                    errors.append(f"{item_prefix}.public_entry: must be a mapping")
                else:
                    entry_mode = public_entry.get("mode")
                    visibility = public_entry.get("visibility")
                    quick_registration = public_entry.get("quick_registration")
                    guest_enabled = public_entry.get("guest_enabled")
                    if entry_mode not in BIU_ENTRY_MODES:
                        errors.append(
                            f"{item_prefix}.public_entry.mode: unknown mode {entry_mode!r}"
                        )
                    if visibility not in BIU_CATALOG_VISIBILITIES:
                        errors.append(
                            f"{item_prefix}.public_entry.visibility: unknown visibility {visibility!r}"
                        )
                    if not _non_empty_string(public_entry.get("summary")):
                        errors.append(
                            f"{item_prefix}.public_entry.summary: must be a non-empty string"
                        )
                    requirements = public_entry.get("requirements")
                    if not isinstance(requirements, (list, tuple)) or not requirements:
                        errors.append(
                            f"{item_prefix}.public_entry.requirements: must be a non-empty list or tuple"
                        )
                    elif any(not _non_empty_string(item) for item in requirements):
                        errors.append(
                            f"{item_prefix}.public_entry.requirements: contains an invalid item"
                        )
                    workflow_ref = public_entry.get("workflow_ref")
                    if entry_mode == "direct":
                        if workflow_ref is not None:
                            errors.append(
                                f"{item_prefix}.public_entry.workflow_ref: direct entry must not use a workflow"
                            )
                    elif entry_mode in BIU_ENTRY_MODES and not _non_empty_string(workflow_ref):
                        errors.append(
                            f"{item_prefix}.public_entry.workflow_ref: must be a non-empty string"
                        )
                    if type(quick_registration) is not bool:
                        errors.append(
                            f"{item_prefix}.public_entry.quick_registration: must be boolean"
                        )
                    elif quick_registration and (
                        entry_mode != "direct"
                        or visibility != "public"
                        or permission_tier not in BIU_QUICK_REGISTRATION_TIERS
                    ):
                        errors.append(
                            f"{item_prefix}.public_entry.quick_registration: "
                            "requires a public direct P0/P1 position"
                        )
                    if type(guest_enabled) is not bool:
                        errors.append(f"{item_prefix}.public_entry.guest_enabled: must be boolean")
                    elif guest_enabled and (
                        visibility == "hidden"
                        or code == str(blueprint.get("admin_position_code") or "")
                    ):
                        errors.append(
                            f"{item_prefix}.public_entry.guest_enabled: "
                            "hidden/system-administrator positions cannot be guest seats"
                        )

                case_roles = position.get("case_roles")
                if not isinstance(case_roles, (list, tuple)):
                    errors.append(f"{item_prefix}.case_roles: must be a list or tuple")
                else:
                    if len(case_roles) != len(set(case_roles)):
                        errors.append(f"{item_prefix}.case_roles: contains duplicates")
                    if any(not _non_empty_string(role) for role in case_roles):
                        errors.append(f"{item_prefix}.case_roles: contains an invalid role")

                if entry_mode == "direct":
                    if position.get("is_manager") is not False:
                        errors.append(
                            f"{item_prefix}.public_entry.mode: direct entry cannot be a manager"
                        )
                    if type(level) is int and level > 3:
                        errors.append(
                            f"{item_prefix}.level: direct entry must remain at level 3 or below"
                        )
                    forbidden = set(permission_list).intersection(
                        BIU_DIRECT_ENTRY_FORBIDDEN_PERMISSIONS
                    )
                    if forbidden:
                        errors.append(
                            f"{item_prefix}.permissions: direct entry contains privileged keys "
                            f"{sorted(forbidden)!r}"
                        )
                    if public_entry.get("quick_registration") and forbidden:
                        errors.append(
                            f"{item_prefix}.public_entry.quick_registration: "
                            "position permissions exceed the direct-entry boundary"
                        )
                    quick_registration_excess = set(permission_list).difference(
                        BIU_QUICK_REGISTRATION_ALLOWED_PERMISSIONS
                    )
                    if public_entry.get("quick_registration") and quick_registration_excess:
                        errors.append(
                            f"{item_prefix}.public_entry.quick_registration: "
                            "position permissions are outside the quick-entry allowlist "
                            f"{sorted(quick_registration_excess)!r}"
                        )

                if code == str(blueprint.get("admin_position_code") or ""):
                    if visibility != "hidden":
                        errors.append(
                            f"{item_prefix}.public_entry.visibility: system administrator must be hidden"
                        )
                    if entry_mode != "appointment":
                        errors.append(
                            f"{item_prefix}.public_entry.mode: system administrator must use appointment"
                        )

        admin_position_code = blueprint.get("admin_position_code")
        admin_position = position_by_code.get(str(admin_position_code))
        if not _non_empty_string(admin_position_code) or admin_position is None:
            errors.append(f"{prefix}.admin_position_code: unknown position {admin_position_code!r}")
        else:
            if admin_position.get("department") != "management":
                errors.append(f"{prefix}.admin_position_code: position must belong to 'management'")
            if admin_position.get("is_manager") is not True:
                errors.append(f"{prefix}.admin_position_code: position must have is_manager=true")
            if admin_position.get("role_name") != "系統管理員":
                errors.append(
                    f"{prefix}.admin_position_code: position must retain role_name '系統管理員'"
                )
            if (
                input_key == BIU_TEMPLATE_KEY
                and admin_position.get("database_access_mode") != "tenant_scoped"
            ):
                errors.append(
                    f"{prefix}.admin_position_code: BIU system administrator must use tenant_scoped database access"
                )

        if input_key == BIU_TEMPLATE_KEY:
            errors.extend(_validate_biu_learning_definitions(position_by_code, prefix))

        modules = blueprint.get("enabled_modules")
        if not isinstance(modules, (list, tuple, set, frozenset)):
            errors.append(f"{prefix}.enabled_modules: must be a collection")
        else:
            module_list = list(modules)
            if len(module_list) != len(set(module_list)):
                errors.append(f"{prefix}.enabled_modules: contains duplicate ids")
            for module_id in module_list:
                if module_id not in V2_NAV_MODULE_IDS:
                    errors.append(
                        f"{prefix}.enabled_modules: unknown WAREHOUSE OS 2.0 module {module_id!r}"
                    )

    return errors


def assert_valid_blueprints(
    blueprints: Optional[Any] = None,
    allowed_permissions: Optional[Iterable[str]] = None,
) -> bool:
    """Raise :class:`BlueprintValidationError` if any blueprint is invalid."""

    errors = validate_blueprints(blueprints, allowed_permissions)
    if errors:
        raise BlueprintValidationError(errors)
    return True


__all__ = [
    "BLUEPRINT_SCHEMA_VERSION",
    "BLUEPRINT_DATA_VERSION",
    "DEFAULT_BLUEPRINT_KEY",
    "BLUEPRINT_PERMISSION_KEYS",
    "VALID_DEPARTMENT_TYPES",
    "DB_NATIVE_DOMAINS",
    "DB_DEPARTMENT_NATIVE_DOMAINS",
    "DB_DEPARTMENT_NATIVE_WRITE_DOMAINS",
    "DB_PERMISSION_READ_DOMAINS",
    "DB_MANAGER_WRITE_CAPABILITY_DOMAINS",
    "V2_NAV_MODULE_RULES",
    "V2_NAV_MODULE_IDS",
    "BIU_TEMPLATE_KEY",
    "BIU_ENTRY_MODES",
    "BIU_CATALOG_VISIBILITIES",
    "BIU_PERMISSION_TIERS",
    "BIU_QUICK_REGISTRATION_TIERS",
    "BIU_QUICK_REGISTRATION_ALLOWED_PERMISSIONS",
    "BIU_DIRECT_ENTRY_FORBIDDEN_PERMISSIONS",
    "BIU_GUIDANCE_AXES",
    "BIU_GUIDANCE_POSITION_PROFILES",
    "BIU_EXAM_POSITION_BANKS",
    "get_biu_public_training_cases",
    "get_biu_guide_definition",
    "get_biu_guidance_position_profiles",
    "get_biu_exam_bank",
    "INDUSTRY_BLUEPRINT_KEYS",
    "BlueprintValidationError",
    "nav_modules_for_permissions",
    "blueprint_nav_defaults",
    "blueprint_nav_ceilings",
    "blueprint_permission_ceilings",
    "get_blueprint",
    "get_all_blueprints",
    "list_blueprints",
    "validate_blueprints",
    "assert_valid_blueprints",
]
