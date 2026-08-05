from __future__ import annotations

import argparse
import getpass
from uuid import uuid4

from sqlalchemy import text

from app.core.security import hash_password
from app.db.session import system_session, tenant_session
from app.services.templates import get_template_summary, provision_tenant_template


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create the first real Warehouse OS tenant administrator"
    )
    parser.add_argument("--tenant-slug", required=True)
    parser.add_argument("--tenant-name", required=True)
    parser.add_argument("--username", required=True)
    parser.add_argument("--display-name", required=True)
    parser.add_argument("--industry-template", default="generic_warehouse")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    password = getpass.getpass("Administrator password: ")
    confirmation = getpass.getpass("Repeat administrator password: ")
    if len(password) < 12:
        raise SystemExit("Password must contain at least 12 characters")
    if password != confirmation:
        raise SystemExit("Passwords do not match")

    tenant_id = uuid4()
    user_id = uuid4()
    template_key = args.industry_template.strip()
    if get_template_summary(template_key) is None:
        raise SystemExit(f"Unknown active industry template: {template_key}")
    with system_session() as session:
        existing = session.execute(
            text("SELECT 1 FROM iam.tenants WHERE slug = :slug"),
            {"slug": args.tenant_slug.strip().lower()},
        ).scalar_one_or_none()
        if existing:
            raise SystemExit("Tenant slug already exists")
        existing = session.execute(
            text("SELECT 1 FROM iam.users WHERE username = :username"),
            {"username": args.username.strip().lower()},
        ).scalar_one_or_none()
        if existing:
            raise SystemExit("Username already exists")
        session.execute(
            text(
                """
                INSERT INTO iam.tenants(id, slug, name, industry_template_key)
                VALUES (:id, :slug, :name, :industry_template_key)
                """
            ),
            {
                "id": tenant_id,
                "slug": args.tenant_slug.strip().lower(),
                "name": args.tenant_name.strip(),
                "industry_template_key": template_key,
            },
        )
        session.execute(
            text(
                """
                INSERT INTO iam.users(id, username, display_name, password_hash)
                VALUES (:id, :username, :display_name, :password_hash)
                """
            ),
            {
                "id": user_id,
                "username": args.username.strip().lower(),
                "display_name": args.display_name.strip(),
                "password_hash": hash_password(password),
            },
        )
    with tenant_session(tenant_id) as session:
        provisioned = provision_tenant_template(
            session,
            tenant_id=tenant_id,
            tenant_name=args.tenant_name.strip(),
            template_key=template_key,
        )
        session.execute(
            text(
                """
                INSERT INTO iam.memberships(
                  tenant_id, user_id, position_code, role_level, topology_level, topology_title
                )
                VALUES (:tenant_id, :user_id, :position_code, 10, 10, 'Owner')
                """
            ),
            {
                "tenant_id": tenant_id,
                "user_id": user_id,
                "position_code": provisioned["admin_position_code"],
            },
        )
        session.execute(
            text(
                """
                INSERT INTO audit.events(tenant_id, actor_user_id, event_type, payload)
                VALUES (:tenant_id, :user_id, 'tenant.bootstrap.completed', :payload::jsonb)
                """
            ),
            {
                "tenant_id": tenant_id,
                "user_id": user_id,
                "payload": f'{{"source":"bootstrap_admin","industry_template":"{template_key}"}}',
            },
        )
    tenant_slug = args.tenant_slug.strip().lower()
    username = args.username.strip().lower()
    print(f"Created tenant {tenant_slug} and administrator {username} with {template_key}")


if __name__ == "__main__":
    main()
