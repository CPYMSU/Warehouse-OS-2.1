// API 客戶端 — 等價於 web 的 window.authFetch:加 Authorization + X-Tenant-Slug;401 觸發登出。
// 後端完全不改;原生無 CORS 限制,直連生產 https。
import Constants from "expo-constants";

// 後端地址:優先 EXPO_PUBLIC_API_BASE(Metro 構建期內聯,便於本地聯調),
// 其次 app.json extra.apiBase,最後默認生產。
export const API_BASE: string =
  process.env.EXPO_PUBLIC_API_BASE ||
  (Constants.expoConfig?.extra as any)?.apiBase ||
  "https://ncsyaikg.com";

type TokenProvider = () => { token: string; slug: string };
let provider: TokenProvider = () => ({ token: "", slug: "" });
let onUnauthorized: () => void = () => {};

export const configureClient = (p: TokenProvider, onAuthExpired: () => void) => {
  provider = p;
  onUnauthorized = onAuthExpired;
};

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

const buildHeaders = (extra?: Record<string, string>) => {
  const { token, slug } = provider();
  const h: Record<string, string> = { Accept: "application/json", ...(extra || {}) };
  if (token) h.Authorization = `Bearer ${token}`;
  if (slug) h["X-Tenant-Slug"] = slug;
  return h;
};

export async function apiGet<T = any>(path: string): Promise<T> {
  const res = await fetch(API_BASE + path, { headers: buildHeaders() });
  if (res.status === 401) { onUnauthorized(); throw new ApiError("登入已過期", 401); }
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new ApiError((data && data.error) || `HTTP ${res.status}`, res.status);
  return data as T;
}

export async function apiPost<T = any>(path: string, body?: any, isForm = false): Promise<T> {
  const headers = isForm ? buildHeaders() : buildHeaders({ "Content-Type": "application/json" });
  const res = await fetch(API_BASE + path, {
    method: "POST",
    headers,
    body: isForm ? body : JSON.stringify(body || {}),
  });
  if (res.status === 401) { onUnauthorized(); throw new ApiError("登入已過期", 401); }
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new ApiError((data && data.error) || `HTTP ${res.status}`, res.status);
  return data as T;
}
