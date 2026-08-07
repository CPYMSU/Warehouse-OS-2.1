from uuid import uuid4

from fastapi.testclient import TestClient

from app.api import full_stack_identity
from app.api.compat import _audit_redact, _audit_redact_command
from app.api.deps import ActorContext, current_actor
from app.main import app
from app.services import integrations

EXPECTED_CONTRACTS = {
    ("GET", "/api/company/branding"),
    ("GET", "/api/runtime/preferences"),
    ("GET", "/api/runtime/world"),
    ("GET", "/api/runtime/skills"),
    ("GET", "/api/voice/status"),
    ("POST", "/api/voice/transcribe"),
    ("POST", "/api/voice/speak"),
    ("GET", "/api/alerts/watch"),
    ("GET", "/api/assets/portfolio"),
    ("GET", "/api/assets"),
    ("GET", "/api/digital-assets/listings"),
    ("GET", "/api/digital-assets/summary"),
    ("GET", "/api/digital-assets"),
    ("GET", "/api/digital-assets/common-market"),
    ("GET", "/api/digital-assets/trades"),
    ("GET", "/api/digital-assets/revenue"),
    ("GET", "/api/research/projects"),
    ("POST", "/api/research/projects"),
    ("GET", "/api/civilization/thoughts"),
    ("POST", "/api/civilization/thoughts"),
    ("PUT", "/api/civilization/thoughts/00000000-0000-0000-0000-000000000001"),
    ("DELETE", "/api/civilization/thoughts/00000000-0000-0000-0000-000000000001"),
    ("GET", "/api/tasks/meta"),
    ("GET", "/api/tasks"),
    ("POST", "/api/tasks"),
    ("PATCH", "/api/tasks/{task_id}"),
    ("POST", "/api/tasks/{task_id}/status"),
    ("DELETE", "/api/tasks/{task_id}"),
    ("GET", "/api/alerts/briefing"),
    ("GET", "/api/alerts"),
    ("GET", "/api/stocktake"),
    ("GET", "/api/erp/overview"),
    ("GET", "/api/erp/gl/income"),
    ("GET", "/api/erp/gl/ap"),
    ("GET", "/api/erp/gl/balance-sheet"),
    ("GET", "/api/erp/gl/ar"),
    ("GET", "/api/erp/finance/events"),
    ("GET", "/api/erp/gl/cashflow"),
    ("GET", "/api/erp/gl/vouchers"),
    ("GET", "/api/wf/my-instances"),
    ("GET", "/api/wf/workflows"),
    ("GET", "/api/tender/board"),
    ("GET", "/api/wf/inbox"),
    ("GET", "/api/tender/inbox"),
    ("GET", "/api/tender/my-bids"),
    ("GET", "/api/b2b/relations"),
    ("GET", "/api/tender/market"),
    ("GET", "/api/legal/overview"),
    ("GET", "/api/compliance/chain-check"),
    ("GET", "/api/audit/logs"),
    ("GET", "/api/audit/cli"),
    ("GET", "/api/ai/conversations"),
    ("GET", "/api/ai/conversation"),
    ("POST", "/api/records/search"),
    ("GET", "/api/records/meta"),
    ("GET", "/api/records/config"),
    ("POST", "/api/records/config/categories"),
    ("POST", "/api/records/config/types"),
    ("POST", "/api/records/config/categories/{category_key}/revisions"),
    ("POST", "/api/records/config/types/{type_key}/revisions"),
    ("POST", "/api/records/config/categories/{category_key}/disable"),
    ("POST", "/api/records/config/types/{type_key}/disable"),
    ("GET", "/api/settings"),
    ("GET", "/api/integrations/tavily"),
    ("GET", "/api/integrations/vision"),
    ("GET", "/api/integrations/voice"),
    ("GET", "/api/integrations/deepseek"),
    ("GET", "/api/nav"),
    ("GET", "/api/ai/health"),
    ("GET", "/api/prompts"),
    ("GET", "/api/permissions"),
    ("GET", "/api/memberships/pending"),
    ("POST", "/api/memberships/{request_id}/approve"),
    ("POST", "/api/memberships/{request_id}/reject"),
    ("GET", "/api/auth/registrations"),
    ("POST", "/api/auth/registrations/{request_id}/approve"),
    ("POST", "/api/auth/registrations/{request_id}/reject"),
    ("GET", "/api/assistant/bootstrap"),
    ("GET", "/api/browser-runtime/capabilities"),
    ("GET", "/api/browser-runtime/journeys"),
    ("POST", "/api/browser-runtime/journeys"),
    ("GET", "/api/browser-runtime/runs"),
    ("POST", "/api/browser-runtime/runs"),
    ("GET", "/api/lighthouse/devices"),
    ("POST", "/api/lighthouse/pairing-challenges"),
    ("POST", "/api/lighthouse/runs"),
}


def _contract_template(path: str) -> str:
    if path.startswith("/api/integrations/"):
        return "/api/integrations/{provider}"
    if path.startswith("/api/civilization/thoughts/"):
        return "/api/civilization/thoughts/{thought_id}"
    return path


def _supports_specific_contract(method: str, path: str) -> bool:
    """Validate the public OpenAPI contract, excluding the hidden API catch-all."""
    paths = app.openapi().get("paths", {})
    operations = paths.get(_contract_template(path), {})
    return method.lower() in operations


def test_error_log_contracts_are_published_in_openapi() -> None:
    missing = sorted(
        f"{method} {path}"
        for method, path in EXPECTED_CONTRACTS
        if not _supports_specific_contract(method, path)
    )

    published = sorted(app.openapi().get("paths", {}))
    assert missing == [], {"missing": missing, "published": published}


def test_error_log_contracts_hit_the_authenticated_api_not_a_static_fallback() -> None:
    client = TestClient(app)
    failures: dict[str, dict[str, object]] = {}

    for method, path in sorted(EXPECTED_CONTRACTS):
        response = client.request(method, path, json={} if method == "POST" else None)
        if response.status_code != 401:
            failures[f"{method} {path}"] = {
                "status": response.status_code,
                "content_type": response.headers.get("content-type"),
                "body": response.text[:300],
            }
        assert response.headers["X-Warehouse-Backend"] == "fastapi-postgresql"

    assert failures == {}


def test_unknown_api_never_falls_through_to_static_file_server() -> None:
    response = TestClient(app).post("/api/not-yet-migrated")

    assert response.status_code == 501
    assert response.headers["X-Warehouse-Backend"] == "fastapi-postgresql"
    assert response.json() == {
        "available": False,
        "status": "not_implemented",
        "reason": "api_contract_not_migrated",
        "path": "/api/not-yet-migrated",
    }


def _voice_actor(*, can_use_voice: bool) -> ActorContext:
    return ActorContext(
        user_id=uuid4(),
        tenant_id=uuid4(),
        tenant_slug="voice-test",
        tenant_name="Voice Test",
        industry_template_key="general",
        username="voice@example.test",
        display_name="Voice Tester",
        role_level=10,
        topology_level=10,
        topology_title=None,
        permissions=frozenset({"ai.use"} if can_use_voice else set()),
    )


def test_voice_routes_require_explicit_ai_use_and_return_real_media(monkeypatch) -> None:
    client = TestClient(app)
    app.dependency_overrides[current_actor] = lambda: _voice_actor(can_use_voice=False)
    try:
        denied = client.post(
            "/api/voice/transcribe",
            content=b"\x1aE\xdf\xa3" + b"\x00" * 508,
            headers={"Content-Type": "audio/webm"},
        )
        assert denied.status_code == 403

        app.dependency_overrides[current_actor] = lambda: _voice_actor(can_use_voice=True)
        monkeypatch.setattr(
            full_stack_identity,
            "transcribe_voice_audio",
            lambda *_args, **_kwargs: integrations.VoiceTranscription(
                "語音路由正常", "FunAudioLLM/SenseVoiceSmall", "route-trace"
            ),
        )
        transcribed = client.post(
            "/api/voice/transcribe",
            content=b"\x1aE\xdf\xa3" + b"\x00" * 508,
            headers={"Content-Type": "audio/webm"},
        )
        assert transcribed.status_code == 200
        assert transcribed.json()["text"] == "語音路由正常"
        assert transcribed.headers["cache-control"] == "no-store"

        monkeypatch.setattr(
            full_stack_identity,
            "synthesize_voice_speech",
            lambda *_args, **_kwargs: integrations.VoiceSpeech(
                b"ID3" + b"\x00" * 400,
                "audio/mpeg",
                "FunAudioLLM/CosyVoice2-0.5B",
                None,
            ),
        )
        spoken = client.post("/api/voice/speak", json={"text": "晚安"})
        assert spoken.status_code == 200
        assert spoken.headers["content-type"].startswith("audio/mpeg")
        assert len(spoken.content) > 200
    finally:
        app.dependency_overrides.clear()


def test_audit_contract_redacts_nested_credentials_and_command_arguments() -> None:
    assert _audit_redact(
        {
            "arguments": {
                "api_key": "live-secret",
                "workspace_key_id": "safe-identifier",
                "nested": [{"access_token": "bearer-secret"}],
            }
        }
    ) == {
        "arguments": {
            "api_key": "[REDACTED]",
            "workspace_key_id": "safe-identifier",
            "nested": [{"access_token": "[REDACTED]"}],
        }
    }
    assert _audit_redact_command("settings save --api-key live-secret --model safe") == (
        "settings save --api-key [REDACTED] --model safe"
    )
