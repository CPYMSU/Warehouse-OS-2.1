// 登錄態 — 全局 Context;token/當前公司 持久化(原生 SecureStore / web AsyncStorage)。
import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { storageGet, storageSet, storageDel } from "./storage";
import { configureClient, apiGet } from "../api/client";
import { login as loginApi, logoutApi } from "../api/endpoints";

const TOKEN_KEY = "warehouse_auth_token";
const TENANT_KEY = "warehouse_current_tenant";

export type Company = { slug: string; name: string; status: string; role?: string };
export type User = { id?: string; username?: string; display_name?: string; role_names?: string[] };

type AuthState = {
  ready: boolean;
  token: string;
  user: User | null;
  companies: Company[];
  tenant: string;
  isOwner: boolean;
  canApplyCompany: boolean;
  signIn: (username: string, password: string) => Promise<void>;
  signOut: () => void;
  switchCompany: (slug: string) => void;
  setSession: (data: any) => Promise<void>;
};

const Ctx = createContext<AuthState>({} as AuthState);

// 模塊級緩存,供 api client 同步讀取
let TOKEN = "";
let SLUG = "";

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [ready, setReady] = useState(false);
  const [token, setToken] = useState("");
  const [user, setUser] = useState<User | null>(null);
  const [companies, setCompanies] = useState<Company[]>([]);
  const [tenant, setTenant] = useState("");
  const [isOwner, setIsOwner] = useState(false);
  const [canApplyCompany, setCanApply] = useState(false);

  const clearLocal = useCallback(() => {
    TOKEN = ""; SLUG = "";
    setToken(""); setUser(null); setCompanies([]); setTenant("");
    setIsOwner(false); setCanApply(false);
    storageDel(TOKEN_KEY);
    storageDel(TENANT_KEY);
  }, []);

  // 配置 api client 的 token 提供者 + 401 處理
  useEffect(() => {
    configureClient(() => ({ token: TOKEN, slug: SLUG }), () => clearLocal());
  }, [clearLocal]);

  // 啟動:讀持久化 token,/api/auth/me 驗證
  useEffect(() => {
    (async () => {
      const t = (await storageGet(TOKEN_KEY)) || "";
      const s = (await storageGet(TENANT_KEY)) || "";
      if (t) {
        TOKEN = t; SLUG = s; setToken(t); setTenant(s);
        try {
          const me = await apiGet("/api/auth/me");
          const active = (me.companies || []).filter((c: Company) => c.status === "active");
          setUser(me.user || null); setCompanies(active);
          setIsOwner(!!me.is_platform_owner); setCanApply(!!me.can_apply_company);
          if (!s && active[0]) { SLUG = active[0].slug; setTenant(active[0].slug); storageSet(TENANT_KEY, SLUG); }
        } catch (_) { clearLocal(); }
      }
      setReady(true);
    })();
  }, [clearLocal]);

  const setSession = useCallback(async (data: any) => {
    const t = data.token || "";
    const active: Company[] = (data.companies || []).filter((c: Company) => c.status === "active");
    const slug = data.default_tenant || (active[0] && active[0].slug) || "";
    TOKEN = t; SLUG = slug;
    setToken(t); setUser(data.user || null); setCompanies(active); setTenant(slug);
    setIsOwner(!!data.is_platform_owner); setCanApply(!!data.can_apply_company);
    await storageSet(TOKEN_KEY, t);
    if (slug) await storageSet(TENANT_KEY, slug);
  }, []);

  const signIn = useCallback(async (username: string, password: string) => {
    const data = await loginApi(username, password);
    await setSession(data);
  }, [setSession]);

  const signOut = useCallback(() => {
    logoutApi().catch(() => {});
    clearLocal();
  }, [clearLocal]);

  const switchCompany = useCallback((slug: string) => {
    SLUG = slug; setTenant(slug);
    storageSet(TENANT_KEY, slug);
  }, []);

  const value = useMemo<AuthState>(() => ({
    ready, token, user, companies, tenant, isOwner, canApplyCompany,
    signIn, signOut, switchCompany, setSession,
  }), [ready, token, user, companies, tenant, isOwner, canApplyCompany, signIn, signOut, switchCompany, setSession]);

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
};

export const useAuth = () => useContext(Ctx);
export const currentToken = () => TOKEN;
export const currentSlug = () => SLUG;
