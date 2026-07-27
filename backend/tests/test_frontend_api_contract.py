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


def _supports_specific_contract(method: str, path: str) -> bool:
    """Require a real contract route, not the generic /api catch-all."""
    for route in app.routes:
        if getattr(route, "path", None) == "/api/{path:path}":
            continue
        methods = getattr(route, "methods", set())
        path_regex = getattr(route, "path_regex", None)
        if method in methods and path_regex is not None and path_regex.fullmatch(path):
            return True
    return False


def test_error_log_contracts_are_registered_before_static_mount() -> None:
    missing = sorted(
        f"{method} {path}"
        for method, path in EXPECTED_CONTRACTS
        if not _supports_specific_contract(method, path)
    )

    assert missing == []


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
