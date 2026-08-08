from datetime import date, datetime, timezone
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.api import civilization as civilization_api
from app.api.deps import ActorContext, current_actor
from app.core.security import hash_password
from app.db.session import system_session, tenant_session
from app.main import app
from app.services.civilization import (
    _can_delete,
    _clean_content,
    _clean_lenses,
    _clean_relations,
    _content_locale,
    _merge_content,
    _merged_lenses,
    _merged_localized,
    _merged_relations,
    _serialize,
    create_thought,
    get_thought,
    list_thoughts,
    save_draft,
    template_catalog,
)
from app.terminal.catalog import availability, entry_by_tool_name


def _actor(
    *,
    role_level: int = 5,
    permissions: frozenset[str] = frozenset(),
    template_key: str = "general",
) -> ActorContext:
    return ActorContext(
        user_id=uuid4(),
        tenant_id=uuid4(),
        tenant_slug="civilization-test",
        tenant_name="Civilization Test",
        industry_template_key=template_key,
        username="reader@example.test",
        display_name="Reader",
        role_level=role_level,
        topology_level=role_level,
        topology_title=None,
        permissions=permissions,
    )


def _database_actor() -> ActorContext:
    actor = _actor(role_level=10, permissions=frozenset({"settings.manage"}))
    with system_session() as session:
        session.execute(
            text(
                """
                INSERT INTO iam.tenants(id, slug, name, industry_template_key)
                VALUES (:id, :slug, :name, 'generic_warehouse')
                """
            ),
            {
                "id": actor.tenant_id,
                "slug": actor.tenant_slug,
                "name": actor.tenant_name,
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
                "id": actor.user_id,
                "username": actor.username,
                "display_name": actor.display_name,
                "password_hash": hash_password("test-password"),
            },
        )
    return actor


def _persisted_actor(slug: str, *, template_key: str = "generic_warehouse") -> ActorContext:
    tenant_id = uuid4()
    tenant_name = slug.replace("-", " ").title()
    with system_session() as session:
        existing = session.execute(
            text(
                """
                SELECT id, name, industry_template_key
                FROM iam.tenants WHERE slug = :slug
                """
            ),
            {"slug": slug},
        ).mappings().one_or_none()
        if existing is None:
            session.execute(
                text(
                    """
                    INSERT INTO iam.tenants(id, slug, name, industry_template_key)
                    VALUES (:id, :slug, :name, :template_key)
                    """
                ),
                {
                    "id": tenant_id,
                    "slug": slug,
                    "name": tenant_name,
                    "template_key": template_key,
                },
            )
        else:
            tenant_id = existing["id"]
            tenant_name = str(existing["name"])
            template_key = str(existing["industry_template_key"])
        actor = ActorContext(
            user_id=uuid4(),
            tenant_id=tenant_id,
            tenant_slug=slug,
            tenant_name=tenant_name,
            industry_template_key=template_key,
            username=f"{slug}-{uuid4().hex[:8]}@example.test",
            display_name=slug.title(),
            role_level=5,
            topology_level=5,
            topology_title=None,
            permissions=frozenset({"civilization.read", "civilization.write"}),
        )
        session.execute(
            text(
                """
                INSERT INTO iam.users(id, username, display_name, password_hash)
                VALUES (:id, :username, :display_name, :password_hash)
                """
            ),
            {
                "id": actor.user_id,
                "username": actor.username,
                "display_name": actor.display_name,
                "password_hash": hash_password("test-password"),
            },
        )
    return actor


def test_delete_policy_allows_creator_and_company_administrator() -> None:
    member = _actor()
    another_user = uuid4()

    assert _can_delete(member, member.user_id) is True
    assert _can_delete(member, another_user) is False
    assert _can_delete(_actor(role_level=10), another_user) is True
    assert _can_delete(_actor(permissions=frozenset({"settings.manage"})), another_user) is True
    assert _can_delete(_actor(role_level=10, template_key="civilization"), another_user) is False


def test_serialized_thought_exposes_exact_personal_ownership() -> None:
    owner = _actor(role_level=10)
    another_actor = _actor(role_level=10)
    now = datetime.now(timezone.utc)
    row = {
        "id": uuid4(),
        "tenant_id": owner.tenant_id,
        "stable_key": "thought-personal-note",
        "domain": "judgement",
        "title": {"zh": "读书笔记"},
        "prompt": {"zh": "一句摘要"},
        "thesis": {"zh": "我的思考"},
        "relations": [],
        "lenses": [],
        "occurred_on": date.today(),
        "display_order": 1,
        "source": "member",
        "created_by": owner.user_id,
        "created_at": now,
        "updated_at": now,
        "revision": 1,
        "template_key": "swiss_b_longform_v1",
        "published_content": {},
        "draft_content": None,
        "publication_status": "published",
        "published_revision": 1,
        "published_at": now,
        "public_share_enabled": False,
        "public_share_key": None,
        "public_shared_at": None,
    }

    assert _serialize(row, owner, number=1)["is_mine"] is True
    assert _serialize(row, another_actor, number=1)["is_mine"] is False


def test_lenses_are_validated_and_localized_for_storage() -> None:
    lenses = _clean_lenses(
        {"lenses": [{"name": "制度", "text": "先看約束，再看選擇。"}]},
        "zh",
    )

    assert lenses == [{"name": {"zh": "制度"}, "text": {"zh": "先看約束，再看選擇。"}}]
    assert _merged_localized({"en": "Question"}, "問題", "zh") == {
        "en": "Question",
        "zh": "問題",
    }
    assert _merged_lenses(
        [{"name": {"en": "System"}, "text": {"en": "Read constraints first."}}],
        lenses,
    ) == [
        {
            "name": {"en": "System", "zh": "制度"},
            "text": {"en": "Read constraints first.", "zh": "先看約束，再看選擇。"},
        }
    ]


def test_relations_are_editable_localized_and_preserve_the_other_language() -> None:
    relations = _clean_relations(
        {"relations": ["一種長期主義", "秩序與時間"]},
        "zh",
    )

    assert relations == [{"zh": "一種長期主義"}, {"zh": "秩序與時間"}]
    assert _merged_relations(
        [{"en": "A form of long-termism"}],
        relations[:1],
    ) == [{"en": "A form of long-termism", "zh": "一種長期主義"}]
    assert _clean_relations({"relations": []}, "zh") == []


def test_swiss_b_content_keeps_layout_and_localized_characters_separate() -> None:
    content = _clean_content(
        {
            "title": "人的成長",
            "short": "成長是網絡位置的改變。",
            "thesis": "因為你的存在，周圍世界更有秩序。",
            "eyebrow": "CIVILIZATION · QUESTION",
            "category_label": "JUDGEMENT",
            "sections": [
                {
                    "marker": "20",
                    "kicker": "ENTER THE NETWORK",
                    "heading": "進入網絡。",
                    "paragraphs": ["學習規則，積累能力。"],
                }
            ],
        },
        domain="judgement",
    )
    stored = _merge_content({}, content, "zh")

    assert stored["template_key"] == "swiss_b_longform_v1"
    assert _content_locale(stored, "zh")["sections"][0]["marker"] == "20"
    assert template_catalog(_actor())["templates"][0]["layout_locked"] is True
    assert "sections[].paragraphs[]" in template_catalog(_actor())["templates"][0]["editable_slots"]


def test_civilization_openapi_exposes_draft_publish_cli_and_revision_lifecycle() -> None:
    route_paths = {getattr(route, "path", "") for route in civilization_api.router.routes}

    assert "/api/civilization/templates" in route_paths
    assert "/api/civilization/cli/manifest" in route_paths
    assert "/api/civilization/api-keys" in route_paths
    assert "/api/civilization/thoughts/{thought_id}/draft" in route_paths
    assert "/api/civilization/thoughts/{thought_id}/preview" in route_paths
    assert "/api/civilization/thoughts/{thought_id}/publish" in route_paths
    assert "/api/civilization/thoughts/{thought_id}/share" in route_paths
    assert "/api/civilization/thoughts/{thought_id}/revisions" in route_paths
    assert "/api/civilization/thoughts/{thought_id}/revisions/{revision_no}/restore" in route_paths
    assert "/api/public/civilization/{share_key}" in route_paths
    assert "/civilization/p/{share_key}" in route_paths


def test_civilization_auto_runtime_genes_are_backed_by_native_routes() -> None:
    tool_names = (
        "civilization_api_key_issue",
        "civilization_api_keys_list",
        "civilization_api_key_revoke",
        "civilization_cli_show",
        "civilization_templates_list",
        "civilization_post_list",
        "civilization_post_observe",
        "civilization_post_delete",
        "civilization_post_create",
        "civilization_post_draft_update",
        "civilization_post_preview",
        "civilization_post_publish",
        "civilization_public_share_configure",
        "civilization_revisions_list",
        "civilization_post_restore",
        "civilization_lens_upsert",
    )

    for tool_name in tool_names:
        entry = entry_by_tool_name(tool_name)
        assert entry is not None
        assert availability(entry) == "active"

    for tool_name in ("civilization_post_create", "civilization_post_draft_update"):
        entry = entry_by_tool_name(tool_name)
        assert entry is not None
        relation_parameter = next(
            parameter for parameter in entry["params"] if parameter["dest"] == "body.relations"
        )
        assert relation_parameter["type"] == "array"


def test_civilization_routes_delegate_to_one_tenant_service(monkeypatch) -> None:
    actor = _actor()
    thought_id = uuid4()
    calls: list[tuple[str, object]] = []
    monkeypatch.setattr(
        civilization_api,
        "list_thoughts",
        lambda received: calls.append(("list", received)) or {"thoughts": []},
    )
    monkeypatch.setattr(
        civilization_api,
        "create_thought",
        lambda received, payload: (
            calls.append(("create", (received, payload)))
            or {"ok": True, "thought": {"id": str(thought_id)}}
        ),
    )
    monkeypatch.setattr(
        civilization_api,
        "delete_thought",
        lambda received, received_id: (
            calls.append(("delete", (received, received_id)))
            or {"ok": True, "deleted_id": str(received_id)}
        ),
    )
    monkeypatch.setattr(
        civilization_api,
        "update_thought",
        lambda received, received_id, payload: (
            calls.append(("update", (received, received_id, payload)))
            or {"ok": True, "thought": {"id": str(received_id), "revision": 2}}
        ),
    )
    monkeypatch.setattr(
        civilization_api,
        "configure_public_share",
        lambda received, received_id, payload: (
            calls.append(("share", (received, received_id, payload)))
            or {"ok": True, "thought": {"id": str(received_id), "revision": 3}}
        ),
    )
    app.dependency_overrides[current_actor] = lambda: actor
    client = TestClient(app)
    try:
        assert client.get("/api/civilization/thoughts").status_code == 200
        created = client.post(
            "/api/civilization/thoughts",
            json={"domain": "time", "title": "Question", "short": "Prompt", "thesis": "Thesis"},
        )
        assert created.status_code == 201
        updated = client.put(
            f"/api/civilization/thoughts/{thought_id}",
            json={
                "domain": "time",
                "title": "Question",
                "short": "Prompt",
                "thesis": "Thesis",
                "expected_revision": 1,
            },
        )
        assert updated.status_code == 200
        shared = client.put(
            f"/api/civilization/thoughts/{thought_id}/share",
            json={"expected_revision": 2, "enabled": True},
        )
        assert shared.status_code == 200
        assert client.delete(f"/api/civilization/thoughts/{thought_id}").status_code == 200
    finally:
        app.dependency_overrides.clear()

    assert [call[0] for call in calls] == ["list", "create", "update", "share", "delete"]
    assert calls[0][1] is actor
    assert calls[1][1][0] is actor
    assert calls[2][1][0:2] == (actor, thought_id)
    assert calls[3][1][0:2] == (actor, thought_id)
    assert calls[3][1][2] == {"expected_revision": 2, "enabled": True}
    assert calls[4][1] == (actor, thought_id)


@pytest.mark.integration
def test_direct_publish_stores_sql_null_draft_and_creates_revision() -> None:
    actor = _database_actor()
    app.dependency_overrides[current_actor] = lambda: actor
    client = TestClient(app)
    try:
        response = client.post(
            "/api/civilization/thoughts",
            json={
                "domain": "organization",
                "title": "关系与组织",
                "short": "直接发布不应留下草稿。",
                "thesis": "发布内容和草稿状态必须保持一致。",
                "publish": True,
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 201, response.text
    created = response.json()["thought"]
    assert created["publication_status"] == "published"
    assert created["published_revision"] == 1
    assert created["has_draft"] is False

    with tenant_session(actor.tenant_id) as session:
        stored = session.execute(
            text(
                """
                SELECT draft_content,
                       jsonb_typeof(published_content) AS published_type,
                       publication_status,
                       published_revision
                FROM civilization.thoughts
                WHERE id = :thought_id
                """
            ),
            {"thought_id": created["id"]},
        ).mappings().one()
        revision_count = session.execute(
            text(
                """
                SELECT count(*)
                FROM civilization.thought_revisions
                WHERE thought_id = :thought_id
                """
            ),
            {"thought_id": created["id"]},
        ).scalar_one()

    assert stored["draft_content"] is None
    assert stored["published_type"] == "object"
    assert stored["publication_status"] == "published"
    assert stored["published_revision"] == 1
    assert revision_count == 1


@pytest.mark.integration
def test_bonfire_published_feed_is_visible_but_read_only_in_every_company() -> None:
    bonfire = _persisted_actor("bonfire")
    civilization_company = _persisted_actor(
        f"civilization-reader-{uuid4().hex[:8]}", template_key="civilization"
    )
    another_company = _persisted_actor(f"civilization-other-{uuid4().hex[:8]}")

    platform_post = create_thought(
        bonfire,
        {
            "domain": "judgement",
            "title": "平台公共问题",
            "short": "Bonfire 发布后进入所有公司的文明信息流。",
            "thesis": "公共内容可阅读，但不能跨公司编辑。",
            "publish": True,
        },
    )["thought"]
    platform_draft = create_thought(
        bonfire,
        {
            "domain": "time",
            "title": "平台未发布草稿",
            "short": "其他公司不能读取。",
            "thesis": "草稿仍然属于 Bonfire。",
            "publish": False,
        },
    )["thought"]
    save_draft(
        bonfire,
        UUID(platform_post["id"]),
        {
            "expected_revision": platform_post["revision"],
            "domain": "time",
            "relations": ["尚未发布的关系"],
            "content": {
                "title": "尚未发布的新标题",
                "short": "这部分不能进入其他公司。",
                "thesis": "发布投影不能包含作者的新草稿。",
            },
        },
    )
    company_post = create_thought(
        civilization_company,
        {
            "domain": "organization",
            "title": "本公司的读书笔记",
            "short": "仅本公司成员读取。",
            "thesis": "普通公司发布不自动成为平台公共内容。",
            "publish": True,
        },
    )["thought"]

    reader_feed = list_thoughts(civilization_company)
    reader_items = {item["id"]: item for item in reader_feed["thoughts"]}
    assert set(reader_items) == {platform_post["id"], company_post["id"]}
    assert platform_draft["id"] not in reader_items
    assert reader_items[platform_post["id"]]["source_scope"] == "platform_public"
    assert reader_items[platform_post["id"]]["source_tenant"]["slug"] == "bonfire"
    assert reader_items[platform_post["id"]]["read_only_source"] is True
    assert reader_items[platform_post["id"]]["can_edit"] is False
    assert reader_items[platform_post["id"]]["domain"] == "judgement"
    assert reader_items[platform_post["id"]]["relations"] == []
    assert reader_items[platform_post["id"]]["draft_content"] is None
    assert (
        reader_items[platform_post["id"]]["content"]["locales"]["zh"]["title"]
        == "平台公共问题"
    )
    assert reader_items[company_post["id"]]["source_scope"] == "company"
    assert reader_feed["feed"] == {
        "scope": "platform_plus_company",
        "platform_source": "bonfire",
        "platform_count": 1,
        "company_count": 1,
    }
    assert get_thought(civilization_company, UUID(platform_post["id"]))["thought"][
        "read_only_source"
    ] is True
    with pytest.raises(HTTPException) as blocked_edit:
        save_draft(
            civilization_company,
            UUID(platform_post["id"]),
            {
                "expected_revision": platform_post["revision"],
                "content": {
                    "title": "不允许修改",
                    "short": "跨公司只读",
                    "thesis": "编辑必须留在来源公司。",
                },
            },
        )
    assert blocked_edit.value.status_code == 403

    other_feed_ids = {item["id"] for item in list_thoughts(another_company)["thoughts"]}
    assert other_feed_ids == {platform_post["id"]}
    assert company_post["id"] not in other_feed_ids


def test_public_civilization_page_is_auth_free_validated_and_metadata_safe(monkeypatch) -> None:
    calls: list[str] = []

    def public_post(share_key: str) -> dict[str, object]:
        calls.append(share_key)
        return {
            "schema": "warehouse.civilization.public-post.v1",
            "share_key": share_key,
            "domain": "judgement",
            "content": {
                "locales": {
                    "zh": {
                        "title": '<script>alert("unsafe")</script>',
                        "short": '秩序與連接 "公開"',
                    }
                }
            },
            "lenses": [],
            "date": "2026—08",
            "published_revision": 2,
            "shared_at": "2026-08-08T00:00:00+00:00",
            "updated_at": "2026-08-08T00:00:00+00:00",
            "public_path": f"/civilization/p/{share_key}",
        }

    monkeypatch.setattr(civilization_api, "get_public_thought", public_post)
    client = TestClient(app)

    api_response = client.get("/api/public/civilization/sharekey1234")
    page_response = client.get("/civilization/p/sharekey1234")

    assert api_response.status_code == 200
    assert api_response.json()["schema"] == "warehouse.civilization.public-post.v1"
    assert page_response.status_code == 200
    assert "<script>alert" not in page_response.text
    assert "&lt;script&gt;alert" in page_response.text
    assert "__SHARE_KEY__" not in page_response.text
    assert calls == ["sharekey1234", "sharekey1234"]
