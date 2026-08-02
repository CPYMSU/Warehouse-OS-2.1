// 所有端點封裝 — 路徑/字段均對應現有後端,不新增任何後端接口。
import { apiGet, apiPost } from "./client";

// ---- 認證 ----
export const login = (username: string, password: string) =>
  apiPost("/api/auth/login", { username, password });
export const registerUser = (payload: Record<string, any>) =>
  apiPost("/api/auth/register", payload);
export const rolesForTenant = (tenant: string) =>
  apiGet(`/api/auth/roles?tenant=${encodeURIComponent(tenant)}`);
export const changePassword = (current_password: string, new_password: string) =>
  apiPost("/api/auth/change-password", { current_password, new_password });
export const logoutApi = () => apiPost("/api/auth/logout", {});

// ---- 公司/成員 ----
export const joinCompany = (slug: string) => apiPost("/api/companies/join", { slug });
export const applyCompany = (payload: Record<string, any>) => apiPost("/api/companies/apply", payload);
export const platformTemplates = () => apiGet("/api/platform/templates");

// ---- 啟動數據 / 通知 ----
export const getBootstrap = () => apiGet("/api/bootstrap");
export const notificationsSummary = () => apiGet("/api/notifications/summary");
export const markNotificationsSeen = (body: any) => apiPost("/api/notifications/seen", body);

// ---- ERP ----
export const erpOverview = () => apiGet("/api/erp/overview");
export const erpSetStatus = (docType: string, id: number | string, status: string) =>
  apiPost(`/api/erp/${docType}/${id}/status`, { status });

// ---- 財務 GL ----
export const glIncome = (period: string) => apiGet(`/api/erp/gl/income?period=${encodeURIComponent(period)}`);
export const glBalanceSheet = () => apiGet("/api/erp/gl/balance-sheet");
export const glCashflow = (period: string) => apiGet(`/api/erp/gl/cashflow?period=${encodeURIComponent(period)}`);
export const glAp = () => apiGet("/api/erp/gl/ap");
export const glAr = () => apiGet("/api/erp/gl/ar");
export const glAssets = () => apiGet("/api/erp/gl/assets");
export const glTax = (period: string) => apiGet(`/api/erp/gl/tax?period=${encodeURIComponent(period)}`);
export const glTrialBalance = () => apiGet("/api/erp/gl/trial-balance");
export const glVouchers = (limit = 40) => apiGet(`/api/erp/gl/vouchers?limit=${limit}`);

// ---- 預警 ----
export const alertsScan = () => apiPost("/api/alerts/scan", {});
export const alertAction = (id: string | number, action: "resolve" | "dismiss") =>
  apiPost(`/api/alerts/${id}/${action}`, {});

// ---- AI 協作 ----
export const collabPeople = () => apiGet("/api/collab/people");
export const collabMessages = (box = "all", status = "active", limit = 220) =>
  apiGet(`/api/collab/messages?box=${box}&status=${status}&limit=${limit}`);
export const collabIdeas = (scope = "active", limit = 80) =>
  apiGet(`/api/collab/ideas?scope=${scope}&limit=${limit}`);
export const collabSendMessage = (payload: Record<string, any>) =>
  apiPost("/api/collab/messages", payload);
export const collabMessageAct = (id: number | string, act: string) =>
  apiPost(`/api/collab/messages/${id}/${act}`, {});

// ---- AI 秘書會話恢復 ----
export const assistantBootstrap = (messageLimit = 80) =>
  apiGet(`/api/assistant/bootstrap?message_limit=${messageLimit}`);
