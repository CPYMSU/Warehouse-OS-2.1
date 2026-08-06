"""Shared action protocol for every Pages control surface.

The console, Auto Runtime and terminal all consume the same stable action keys
and native capability names.  Presentation clients only dispatch an action;
they do not encode business workflows in button-specific prompts.
"""

from __future__ import annotations

from typing import Any

ACTION_SCHEMA = "warehouse.pages-actions.v1"
ACTION_CONTEXT_SCHEMA = "warehouse.pages-action-context.v1"


def _action(
    action_key: str,
    *,
    label: str,
    description: str,
    icon: str,
    placement: str,
    invocation: dict[str, Any],
    enabled: bool = True,
    disabled_reason: str | None = None,
    effect: str = "read",
    confirmation_required: bool = False,
) -> dict[str, Any]:
    return {
        "action_key": action_key,
        "label": label,
        "description": description,
        "icon": icon,
        "placement": placement,
        "effect": effect,
        "enabled": enabled,
        "disabled_reason": disabled_reason if not enabled else None,
        "confirmation": {
            "required": confirmation_required,
            "mechanism": "capability_contract" if confirmation_required else "none",
        },
        "invocation": invocation,
    }


def _runtime_invocation(
    action_key: str,
    workspace_ref: str,
    *,
    goal: str,
    suggested_tools: list[str],
    deployment_id: str | None = None,
) -> dict[str, Any]:
    context: dict[str, Any] = {
        "schema": ACTION_CONTEXT_SCHEMA,
        "action_key": action_key,
        "workspace_ref": workspace_ref,
        "suggested_tool_names": suggested_tools,
    }
    if deployment_id:
        context["deployment_id"] = deployment_id
    return {
        "mode": "auto_runtime",
        "goal": goal,
        "display_text": goal.split("。", 1)[0],
        "action_context": context,
    }


def pages_action_catalog(
    *,
    workspace_ref: str,
    site: dict[str, Any],
    database: dict[str, Any],
    releases: list[dict[str, Any]],
    can_manage: bool,
) -> dict[str, Any]:
    """Build one state-aware action catalogue for Pages UI and AI clients."""

    permission_reason = None if can_manage else "asset_management_permission_required"
    database_count = int(database.get("count") or 0)
    browser = database.get("browser") if isinstance(database.get("browser"), dict) else {}
    browser_capable = database_count > 0
    site_config = site.get("config") if isinstance(site.get("config"), dict) else {}
    device_runtime = (
        site_config.get("device_runtime")
        if isinstance(site_config.get("device_runtime"), dict)
        else {}
    )
    device_enabled = bool(device_runtime.get("enabled"))
    items: list[dict[str, Any]] = [
        _action(
            "pages.status.refresh",
            label="重新整理",
            description="重新读取 Pages、发布、数据库与来源状态。",
            icon="refresh",
            placement="utility",
            invocation={"mode": "client", "client_action": "refresh"},
        ),
        _action(
            "pages.site.open",
            label="Warehouse OS 內訪問",
            description="打开当前已保留的 Warehouse OS Pages 入口。",
            icon="outbound",
            placement="entry",
            enabled=bool(site.get("url")),
            disabled_reason="pages_url_unavailable",
            invocation={
                "mode": "client",
                "client_action": "open_url",
                "url": site.get("url"),
            },
        ),
        _action(
            "pages.site.copy",
            label="複製網址",
            description="复制当前规范入口，不复制隔离 Runtime Origin。",
            icon="copy",
            placement="entry",
            enabled=bool(site.get("url")),
            disabled_reason="pages_url_unavailable",
            invocation={
                "mode": "client",
                "client_action": "copy_url",
                "url": site.get("url"),
            },
        ),
        _action(
            "pages.site.configure",
            label="網址與別名",
            description="先读取当前站点，再收集短名称；确认后由托管会话提交 Pages desired state。",
            icon="link",
            placement="primary",
            enabled=can_manage,
            disabled_reason=permission_reason,
            effect="mutation",
            confirmation_required=True,
            invocation=_runtime_invocation(
                "pages.site.configure",
                workspace_ref,
                goal=(
                    f"配置工作区「{workspace_ref}」的 Pages 网址与可选别名。"
                    "先读取当前 Pages 状态；若短名称尚未提供，只询问短名称。"
                    "确认后使用原生 Pages configure 能力在托管会话提交 desired_state.pages；"
                    "public_alias_enabled 未被明确要求时保持当前值。"
                    "若存在浏览器数据库项目，核对新的隔离 HTTPS Origin；"
                    "仅在 20 个来源已满时请求人工处理。"
                ),
                suggested_tools=[
                    "digital_market_pages_status",
                    "digital_market_pages_configure",
                    "digital_market_database_browser_access",
                ],
            ),
        ),
        _action(
            "pages.design.review",
            label="AI 改設計",
            description="读取当前不可变源的设计上下文和必要文件，再提出有证据的改版方案。",
            icon="sparkle",
            placement="primary",
            enabled=can_manage,
            disabled_reason=permission_reason,
            effect="proposal",
            confirmation_required=True,
            invocation=_runtime_invocation(
                "pages.design.review",
                workspace_ref,
                goal=(
                    f"审阅并改进工作区「{workspace_ref}」的 Pages 设计。"
                    "先读取 design context、compute_placement 与必要的非秘密文件，"
                    "说明哪些计算适合浏览器 JavaScript/TypeScript 或 WebAssembly，"
                    "哪些必须保留平台数据 API、按需函数或 Runtime，并提出有文件证据的建议；"
                    "用户确认后才建立新的不可变源版本、预览并激活，禁止原地修改当前 Release。"
                ),
                suggested_tools=[
                    "digital_market_pages_status",
                    "digital_market_pages_design",
                    "digital_market_pages_design_file",
                    "digital_market_hosting_start",
                ],
            ),
        ),
        _action(
            "pages.package.download",
            label="導出應用包",
            description=(
                "导出当前不可变源的静态网页、数据与同步契约、按需函数声明和 AI 设计文件；"
                "包内不注入平台密钥。"
            ),
            icon="outbound",
            placement="primary",
            enabled=bool(releases),
            disabled_reason="source_version_required",
            invocation={
                "mode": "client",
                "client_action": "open_url",
                "url": f"/api/workspaces/{workspace_ref}/pages/package/download",
            },
        ),
        _action(
            "pages.release.publish",
            label="發布新版",
            description="通过托管会话创建、验证并预览新的不可变发布。",
            icon="outbound",
            placement="primary",
            enabled=can_manage,
            disabled_reason=permission_reason,
            effect="mutation",
            confirmation_required=True,
            invocation=_runtime_invocation(
                "pages.release.publish",
                workspace_ref,
                goal=(
                    f"为工作区「{workspace_ref}」规划并发布新的 Pages Release。"
                    "先读取当前状态、design context 和源版本，再询问本次变更；"
                    "确认后通过托管会话建立不可变源、预览和健康验证，激活仍需治理确认。"
                ),
                suggested_tools=[
                    "digital_market_pages_status",
                    "digital_market_pages_design",
                    "digital_market_hosting_start",
                ],
            ),
        ),
        _action(
            "pages.device.runtime",
            label="設備運行" if device_enabled else "升級設備優先",
            description=(
                "读取 Local Agent、已验证源代码、静态前端、数据库 API 与按需回退状态。"
                if device_enabled
                else "迁移为静态前端直出、用户设备优先计算与平台按需回退。"
            ),
            icon="gear",
            placement="primary",
            enabled=bool(device_enabled or can_manage),
            disabled_reason=permission_reason,
            effect="read" if device_enabled else "mutation",
            confirmation_required=not device_enabled,
            invocation=_runtime_invocation(
                "pages.device.runtime",
                workspace_ref,
                goal=(
                    f"读取工作区「{workspace_ref}」的 Device Runtime、静态前端、"
                    "浏览器数据库 API 与 scale-to-zero 回退状态，不修改部署。"
                    if device_enabled
                    else (
                        f"把工作区「{workspace_ref}」升级为静态前端直出、用户设备 Local Agent "
                        "优先、平台 scale-to-zero 兜底。先读取迁移计划；确认后执行 Pages Device "
                        "Migration。只配置数据库浏览器安全 API，不执行数据库 schema 迁移。"
                    )
                ),
                suggested_tools=(
                    ["digital_market_pages_status", "digital_market_device_runtime"]
                    if device_enabled
                    else [
                        "digital_market_pages_device_plan",
                        "digital_market_pages_device_migrate",
                        "digital_market_device_runtime",
                    ]
                ),
            ),
        ),
        _action(
            "pages.database.browser_access",
            label="瀏覽器數據庫來源",
            description=(
                "核对隔离 Runtime 的精确 HTTPS Origin、规则与来源上限。"
                if browser.get("project_present")
                else "为已绑定数据库规划默认拒绝的浏览器安全入口。"
            ),
            icon="database",
            placement="database",
            enabled=bool(can_manage and browser_capable),
            disabled_reason=(
                permission_reason if not can_manage else "database_binding_required"
            ),
            effect="mutation",
            confirmation_required=True,
            invocation=_runtime_invocation(
                "pages.database.browser_access",
                workspace_ref,
                goal=(
                    f"检查工作区「{workspace_ref}」的 Pages 浏览器数据库安全入口。"
                    "读取当前项目与精确 Origins；需要变更时保持默认拒绝规则并提交治理确认。"
                    "不得使用通配 Origin，只有来源数量达到上限时才请求人工清理。"
                ),
                suggested_tools=[
                    "digital_market_pages_status",
                    "digital_market_database_browser_access",
                    "digital_market_database_browser_configure",
                ],
            ),
        ),
    ]
    for release in releases:
        if not release.get("rollback_eligible"):
            continue
        deployment_id = str(release.get("uuid") or "")
        if not deployment_id:
            continue
        items.append(
            _action(
                f"pages.release.activate:{deployment_id}",
                label="回滾至此",
                description="重新核对目标仍健康后，原子切换 Pages 活动发布指针。",
                icon="refresh",
                placement="release",
                enabled=can_manage,
                disabled_reason=permission_reason,
                effect="mutation",
                confirmation_required=True,
                invocation={
                    "mode": "typed_action",
                    "tool_name": "digital_market_pages_release_activate",
                    "arguments": {
                        "workspace": workspace_ref,
                        "deployment": deployment_id,
                    },
                    "query": "dm pages release activate",
                    "filter": "authorized",
                },
            )
        )
    return {
        "schema": ACTION_SCHEMA,
        "dispatcher": "warehouse.pages-action.v1",
        "state_source": f"/api/workspaces/{workspace_ref}/pages-console",
        "refresh_events": ["w2-agent-complete", "w2-business-action-complete"],
        "items": items,
    }
