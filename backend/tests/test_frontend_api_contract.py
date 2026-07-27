from fastapi.testclient import TestClient

from app.main import app

EXPECTED_CONTRACTS = {
    ("GET", "/api/company/branding"),
    ("GET", "/api/runtime/preferences"),
    ("GET", "/api/voice/status"),
    ("GET", "/api/alerts/watch"),
    ("GET", "/api/assets/portfolio"),
    ("GET", "/api/assets"),
    ("GET", "/api/digital-assets/listings"),
    ("GET", "/api/digital-assets/summary"),
    ("GET", "/api/digital-assets"),
    ("GET", "/api/digital-assets/common-market"),
    ("GET", "/api/digital-assets/trades"),
    ("GET", "/api/digital-assets/revenue"),
    ("GET", "/api/tasks/meta"),
    ("GET", "/api/tasks"),
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
    ("POST", "/api/records/search"),
    ("GET", "/api/records/meta"),
    ("GET", "/api/settings"),
    ("GET", "/api/integrations/tavily"),
    ("GET", "/api/integrations/vision"),
    ("GET", "/api/integrations/voice"),
    ("GET", "/api/integrations/deepseek"),
    ("GET", "/api/nav"),
    ("GET", "/api/ai/health"),
    ("GET", "/api/prompts"),
    ("GET", "/api/permissions"),
    ("GET", "/api/assistant/bootstrap"),
}


def _contract_template(path: str) -> str:
    if path.startswith("/api/integrations/"):
        return "/api/integrations/{provider}"
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
