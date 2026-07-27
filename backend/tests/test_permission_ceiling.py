from __future__ import annotations

from app.api.deps import _capped_position_permissions


def test_department_ceiling_clips_standard_position_but_not_l10() -> None:
    positions = [
        {
            "position_code": "operator",
            "department_code": "warehouse",
            "permissions": ["inventory.read", "inventory.adjust", "audit.read"],
        }
    ]
    units = [
        {
            "unit_code": "warehouse",
            "parent_unit_code": "company",
            "permission_ceiling_enabled": True,
            "permission_ceiling": ["inventory.read", "inventory.adjust"],
        },
        {
            "unit_code": "company",
            "parent_unit_code": None,
            "permission_ceiling_enabled": True,
            "permission_ceiling": ["inventory.read"],
        },
    ]

    standard, direct_ceiling = _capped_position_permissions(positions, units, role_level=6)
    assert standard == {"inventory.read"}
    assert direct_ceiling == {"inventory.read"}

    l10, l10_ceiling = _capped_position_permissions(positions, units, role_level=10)
    assert l10 == {"inventory.read", "inventory.adjust", "audit.read"}
    assert l10_ceiling is None
