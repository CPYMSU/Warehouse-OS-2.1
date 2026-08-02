"""Deployment-manager entry point for verified HDD database migration."""

from __future__ import annotations

import argparse
import json
from uuid import UUID

from app.services.digital_asset_hosting import migrate_tenant_databases_to_hdd


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("migrate-tenant",))
    parser.add_argument("tenant_id")
    args = parser.parse_args()
    result = migrate_tenant_databases_to_hdd(UUID(args.tenant_id))
    print(json.dumps(result, ensure_ascii=False, default=str))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
