"""Layered context distillation for the shared Warehouse Intelligence Runtime.

The engine keeps the global map and exact working data separate.  It never
selects a command with string matching or role-level branches; model reasoning
chooses capability genes after observing the atlas, company authority world
and current goal.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import text

from app.db.session import tenant_session
from app.services.digital_asset_hosting import runtime_hosting_snapshot
from app.services.generic_data import resource_atlas
from app.services.organization import runtime_authority_snapshot
from app.terminal.catalog import (
    ai_capability_atlas,
    ai_capability_gene_index,
    ai_capability_genes,
)

if TYPE_CHECKING:
    from app.api.deps import ActorContext


def _conversation_uuid(value: str | None) -> UUID | None:
    if not value:
        return None
    try:
        return UUID(str(value))
    except (TypeError, ValueError):
        return None


def _recent_runtime_context(
    actor: ActorContext, conversation_id: str | None
) -> list[dict[str, object]]:
    conversation_uuid = _conversation_uuid(conversation_id)
    with tenant_session(actor.tenant_id) as session:
        condition = (
            "conversation_id = :conversation_id"
            if conversation_uuid is not None
            else "actor_user_id = :actor_user_id"
        )
        rows = (
            session.execute(
                text(
                    f"""
                    SELECT id, task, status, context_snapshot, created_at, updated_at
                    FROM secretariat.runs
                    WHERE {condition}
                    ORDER BY updated_at DESC
                    LIMIT 8
                    """
                ),
                {
                    "conversation_id": conversation_uuid,
                    "actor_user_id": actor.user_id,
                },
            )
            .mappings()
            .all()
        )
    return [
        {
            "run_id": str(row["id"]),
            "goal": row["task"],
            "status": row["status"],
            "distillation": (
                row["context_snapshot"].get("distillation")
                if isinstance(row["context_snapshot"], dict)
                else None
            ),
            "updated_at": row["updated_at"].isoformat(),
        }
        for row in rows
    ]


def _experience_memory(actor: ActorContext) -> list[dict[str, object]]:
    """Load owner-private and explicitly company-shared experience memory."""
    with tenant_session(actor.tenant_id) as session:
        rows = (
            session.execute(
                text(
                    """
                    SELECT source_type, source_id, content, metadata, updated_at
                    FROM (
                      SELECT
                        'layered_' || kind AS source_type,
                        id::text AS source_id,
                        content,
                        metadata || jsonb_build_object(
                          'scope', scope,
                          'confidence', confidence,
                          'salience', salience,
                          'memory_is_not_authority', true
                        ) AS metadata,
                        updated_at
                      FROM secretariat.memory_units
                      WHERE status = 'active'
                        AND (valid_to IS NULL OR valid_to > now())
                        AND (
                          (scope = 'private' AND owner_user_id = :actor_user_id)
                          OR scope = 'company'
                        )

                      UNION ALL

                      SELECT
                        chunk.source_type,
                        chunk.source_id,
                        chunk.content,
                        chunk.metadata || jsonb_build_object(
                          'scope', 'private',
                          'memory_is_not_authority', true
                        ),
                        chunk.updated_at
                      FROM secretariat.knowledge_chunks chunk
                      JOIN secretariat.runs run
                        ON run.id::text = chunk.source_id
                       AND run.actor_user_id = :actor_user_id
                      WHERE chunk.source_type IN (
                        'runtime_semantic_memory',
                        'runtime_episodic_memory',
                        'runtime_procedural_memory'
                      )
                    ) experience
                    ORDER BY updated_at DESC
                    LIMIT 12
                    """
                ),
                {"actor_user_id": actor.user_id},
            )
            .mappings()
            .all()
        )
    return [
        {
            "kind": (
                str(row["source_type"])
                .removeprefix("runtime_")
                .removesuffix("_memory")
                .removeprefix("layered_")
            ),
            "source_id": row["source_id"],
            "content": row["content"],
            "metadata": row["metadata"] if isinstance(row["metadata"], dict) else {},
            "updated_at": row["updated_at"].isoformat(),
        }
        for row in rows
    ]


def _company_micro_summary(actor: ActorContext) -> dict[str, object]:
    """Return the smallest useful tenant/authority view for top-level routing.

    The router needs to know what kind of company it is serving and whether a
    richer authority world exists.  It does not need every position,
    permission, employee or database grant before it has selected a domain.
    """
    with tenant_session(actor.tenant_id) as session:
        counts = session.execute(
            text(
                """
                SELECT
                  (SELECT COUNT(*)::integer
                   FROM iam.organizational_units WHERE active) AS departments,
                  (SELECT COUNT(*)::integer
                   FROM iam.position_profiles WHERE active) AS positions,
                  (SELECT COUNT(*)::integer
                   FROM iam.memberships WHERE active) AS people
                """
            )
        ).mappings().one()
    return {
        "company": {
            "slug": actor.tenant_slug,
            "name": actor.tenant_name,
            "industry_template_key": actor.industry_template_key,
        },
        "authority_counts": {
            "departments": int(counts["departments"]),
            "positions": int(counts["positions"]),
            "people": int(counts["people"]),
        },
        "current_actor": {
            "username": actor.username,
            "display_name": actor.display_name,
            "role_level": actor.role_level,
            "identity_count": len(actor.identities),
            "permission_count": len(actor.permissions),
            "identities": [
                {
                    "position_code": identity.position_code,
                    "name": identity.name,
                    "role_level": identity.role_level,
                    "appointment_type": identity.appointment_type,
                }
                for identity in actor.identities
            ],
        },
    }


def build_router_context(
    actor: ActorContext,
    goal: str,
    *,
    surface: str,
    conversation_id: str | None,
    context_mode: str = "balanced",
) -> dict[str, object]:
    """Build a compact first-pass context with dynamically expandable layers.

    Every capability domain remains visible to the company AI, while exact
    commands, authority topology, history and live data are deliberately lazy.
    This is the top of the hierarchical context funnel.
    """
    atlas = ai_capability_atlas()
    resources = resource_atlas(actor)
    gene_count = sum(int(item.get("gene_count") or 0) for item in atlas)
    return {
        "L0_permanent_world_map": {
            "world": "warehouse_os",
            "cognitive_cycle": [
                "route",
                "expand_domain",
                "expand_command_family",
                "select_exact_capability",
                "observe_live_data",
                "reflect",
                "replan_or_complete",
            ],
            "capability_atlas": atlas,
            "capability_gene_count": gene_count,
            "resource_atlas": resources,
            "resource_count": len(resources),
            "visibility": (
                "all capability domains are visible regardless of the current "
                "human's permissions; exact genes expand by model judgment"
            ),
            "expansion_protocol": {
                "capabilities": "domain_then_command_family_then_exact_gene",
                "resources": "resource_then_schema_then_exact_record",
                "company_context": [
                    "authority",
                    "hosting",
                    "operational_world",
                    "conversation_history",
                    "memory_index",
                ],
            },
        },
        "L1_current_company_and_people": {
            "company_summary": _company_micro_summary(actor),
            "company_authority_world": {"loaded": False},
            "hosted_application_world": {"loaded": False},
            "current_interaction": {
                "surface": surface,
                "conversation_id": conversation_id,
                "context_mode": context_mode,
            },
        },
        "L2_current_goal": {
            "raw_goal": goal,
            "understood_goal": None,
            "success_criteria": [],
            "uncertainties": [],
        },
        "L3_execution_working_set": {
            "expanded_domains": [],
            "expanded_families": [],
            "domain_capability_index": [],
            "selected_capability_genes": [],
            "exact_entities": [],
            "tool_results": [],
            "current_errors": [],
        },
        "L4_recent_context": {
            "loaded": False,
            "conversation_id": conversation_id,
            "available": bool(conversation_id),
        },
        "L5_experience_memory": {
            "loaded": False,
            "available": bool(conversation_id),
        },
        "L6_raw_world_pointers": {
            "data_scope": "current_tenant_only",
            "sources": [
                "structured_postgresql",
                "documents_and_knowledge",
                "events_and_runtime_records",
                "vector_and_experience_memory",
            ],
            "expansion_mode": "model_requested_and_goal_driven",
        },
    }


def expand_capability_domains(
    layers: dict[str, object],
    domains: list[str],
    *,
    family_keys: list[str] | None = None,
) -> list[dict[str, object]]:
    """Expose compact genes for model-selected domains and dynamic families."""
    known_domains = {
        str(item.get("domain"))
        for item in ai_capability_atlas()
        if item.get("domain")
    }
    selected_domains = list(
        dict.fromkeys(str(domain) for domain in domains if str(domain) in known_domains)
    )[:8]
    selected_domain_set = set(selected_domains)
    known_family_keys = {
        f"{gene.get('domain')}:{str(gene.get('command') or '').split(maxsplit=1)[0]}"
        for gene in ai_capability_gene_index()
        if str(gene.get("domain")) in selected_domain_set
    }
    selected_family_keys = list(
        dict.fromkeys(
            str(family)
            for family in (family_keys or [])
            if str(family) in known_family_keys
        )
    )[:16]
    selected_family_set = set(selected_family_keys)
    restrict_to_families = bool(family_keys)
    genes = []
    for gene in ai_capability_gene_index():
        domain = str(gene.get("domain"))
        family = str(gene.get("command") or "").split(maxsplit=1)[0]
        if domain not in selected_domain_set:
            continue
        if restrict_to_families and f"{domain}:{family}" not in selected_family_set:
            continue
        genes.append(gene)
    compact = [
        {
            "tool_name": gene["tool_name"],
            "domain": gene["domain"],
            "family": str(gene.get("command") or "").split(maxsplit=1)[0],
            "description": str(gene["description"])[:220],
            "availability": gene["availability"],
            "execution_kind": gene.get("execution_kind"),
            "mode": (
                "write_confirmation"
                if gene["confirmation_required"]
                else ("write_direct" if gene["writes"] else "read")
            ),
        }
        for gene in genes
    ]
    l3 = layers.get("L3_execution_working_set")
    if isinstance(l3, dict):
        existing_domains = [
            str(item) for item in l3.get("expanded_domains") or []
        ]
        l3["expanded_domains"] = list(
            dict.fromkeys([*existing_domains, *selected_domains])
        )
        existing_families = [
            str(item) for item in l3.get("expanded_families") or []
        ]
        l3["expanded_families"] = list(
            dict.fromkeys([*existing_families, *selected_family_keys])
        )
        existing = {
            str(item.get("tool_name")): item
            for item in l3.get("domain_capability_index") or []
            if isinstance(item, dict) and item.get("tool_name")
        }
        for item in compact:
            existing[str(item["tool_name"])] = item
        l3["domain_capability_index"] = list(existing.values())
        return list(l3["domain_capability_index"])
    return compact


def hydrate_company_authority(
    layers: dict[str, object], actor: ActorContext
) -> dict[str, object]:
    """Load the full current-tenant responsibility topology on demand."""
    authority = runtime_authority_snapshot(actor)
    l1 = layers.get("L1_current_company_and_people")
    if isinstance(l1, dict):
        l1["company_authority_world"] = authority
    return authority


def hydrate_hosting_world(
    layers: dict[str, object], actor: ActorContext
) -> dict[str, object]:
    """Load hosted-program/custody context only when model judgment asks for it."""
    hosting = runtime_hosting_snapshot(actor)
    l1 = layers.get("L1_current_company_and_people")
    if isinstance(l1, dict):
        l1["hosted_application_world"] = hosting
    return hosting


def hydrate_recent_context(
    layers: dict[str, object],
    actor: ActorContext,
    conversation_id: str | None,
) -> list[dict[str, object]]:
    recent = _recent_runtime_context(actor, conversation_id)
    layers["L4_recent_context"] = {
        "loaded": True,
        "conversation_id": conversation_id,
        "items": recent,
    }
    return recent


def hydrate_experience_memory(
    layers: dict[str, object], actor: ActorContext
) -> list[dict[str, object]]:
    memory = _experience_memory(actor)
    layers["L5_experience_memory"] = {
        "loaded": True,
        "items": memory,
    }
    return memory


def build_context_layers(
    actor: ActorContext,
    goal: str,
    *,
    surface: str,
    conversation_id: str | None,
) -> dict[str, object]:
    """Build L0-L6 without collapsing them into a flat prompt."""
    atlas = ai_capability_atlas()
    genes = ai_capability_gene_index()
    resources = resource_atlas(actor)
    # L0 is a discovery index, not a second copy of all expanded tool
    # contracts.  Every gene remains visible by name and meaning; exact
    # parameters, permissions and confirmation contracts are expanded into L3
    # only after model judgment selects a candidate.  This keeps each
    # cognitive phase below provider context/latency limits.
    gene_index = [
        [
            gene["tool_name"],
            gene["domain"],
            str(gene["description"])[:180],
            gene["availability"],
            "write" if gene["writes"] else "read",
        ]
        for gene in genes
    ]
    authority = runtime_authority_snapshot(actor)
    return {
        "L0_permanent_world_map": {
            "world": "warehouse_os",
            "cognitive_cycle": [
                "observe",
                "understand",
                "plan",
                "act",
                "reflect",
                "replan_or_complete",
            ],
            "capability_atlas": atlas,
            "capability_gene_count": len(genes),
            "resource_atlas": resources,
            "resource_count": len(resources),
            "capability_gene_index_mode": "all_genes_compact_exact_schema_on_selection",
            "capability_gene_index_columns": [
                "tool_name",
                "domain",
                "description",
                "availability",
                "mode",
            ],
            "capability_gene_index": gene_index,
        },
        "L1_current_company_and_people": {
            "company_authority_world": authority,
            "hosted_application_world": runtime_hosting_snapshot(actor),
            "current_interaction": {
                "surface": surface,
                "conversation_id": conversation_id,
                "actor": {
                    "username": actor.username,
                    "display_name": actor.display_name,
                    "identities": [
                        {
                            "position_code": identity.position_code,
                            "name": identity.name,
                            "role_level": identity.role_level,
                            "appointment_type": identity.appointment_type,
                        }
                        for identity in actor.identities
                    ],
                    "effective_permissions": sorted(actor.permissions),
                },
            },
        },
        "L2_current_goal": {
            "raw_goal": goal,
            "understood_goal": None,
            "success_criteria": [],
            "uncertainties": [],
        },
        "L3_execution_working_set": {
            "selected_capability_genes": [],
            "exact_entities": [],
            "tool_results": [],
            "current_errors": [],
        },
        "L4_recent_context": _recent_runtime_context(actor, conversation_id),
        "L5_experience_memory": _experience_memory(actor),
        "L6_raw_world_pointers": {
            "data_scope": "current_tenant_only",
            "sources": [
                "structured_postgresql",
                "documents_and_knowledge",
                "events_and_runtime_records",
                "vector_and_experience_memory",
            ],
            "expansion_mode": "capability_or_goal_driven",
        },
    }


def expand_selected_capabilities(
    layers: dict[str, object], tool_names: list[str]
) -> list[dict[str, object]]:
    """Expand only the genes selected by model judgment into the L3 work set."""
    expanded = ai_capability_genes(tool_names)
    l3 = layers["L3_execution_working_set"]
    if isinstance(l3, dict):
        l3["selected_capability_genes"] = expanded
    return expanded


def responsibility_for_genes(
    layers: dict[str, object], genes: list[dict[str, object]]
) -> dict[str, object]:
    """Connect selected ability requirements to responsible people and jobs."""
    l1 = layers.get("L1_current_company_and_people")
    authority = l1.get("company_authority_world") if isinstance(l1, dict) else {}
    index = authority.get("responsibility_index") if isinstance(authority, dict) else {}
    result: dict[str, object] = {}
    for gene in genes:
        schema = gene.get("schema") if isinstance(gene, dict) else {}
        tool_name = schema.get("name") if isinstance(schema, dict) else None
        if not tool_name:
            continue
        people: list[str] = []
        positions: list[str] = []
        for permission in gene.get("permission_any") or []:
            responsibility = index.get(str(permission), {}) if isinstance(index, dict) else {}
            people.extend(responsibility.get("people") or [])
            positions.extend(responsibility.get("positions") or [])
        result[str(tool_name)] = {
            "people": list(dict.fromkeys(people)),
            "positions": list(dict.fromkeys(positions)),
        }
    return result
