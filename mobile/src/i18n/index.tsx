// 繁/簡切換 — 移植 web i18n.jsx 策略:源文為繁體,僅做「繁→簡」(多對一,平表正確),
// 不做歧義的「簡→繁」逆轉換(切回繁體=用繁體源文)。RN 無 DOM,故為純函數 + Context。
import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { CHAR_PACKED, PHRASES } from "./openccTable";

const STORE_KEY = "mk3-language";
export type Lang = "zh-Hant" | "zh-Hans";

const CHAR_MAP = (() => {
  const m = new Map<string, string>();
  for (let i = 0; i + 1 < CHAR_PACKED.length; i += 2) m.set(CHAR_PACKED[i], CHAR_PACKED[i + 1]);
  return m;
})();
const ALL_PHRASES = [...PHRASES].sort((a, b) => b[0].length - a[0].length);

const toSimplified = (text: string): string => {
  let out = text;
  for (const [trad, simp] of ALL_PHRASES) {
    if (out.indexOf(trad) === -1) continue;
    out = out.split(trad).join(simp);
  }
  let res = "";
  for (const ch of out) res += CHAR_MAP.get(ch) || ch;
  return res;
};

type Ctx = { lang: Lang; setLang: (l: Lang) => void; t: (s: string) => string };
const I18nContext = createContext<Ctx>({ lang: "zh-Hant", setLang: () => {}, t: (s) => s });

export const I18nProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [lang, setLangState] = useState<Lang>("zh-Hant");
  useEffect(() => {
    AsyncStorage.getItem(STORE_KEY).then((v) => { if (v === "zh-Hans" || v === "zh-Hant") setLangState(v); });
  }, []);
  const setLang = useCallback((l: Lang) => { setLangState(l); AsyncStorage.setItem(STORE_KEY, l); }, []);
  const t = useCallback((s: string) => (lang === "zh-Hans" && s ? toSimplified(s) : s), [lang]);
  const value = useMemo(() => ({ lang, setLang, t }), [lang, setLang, t]);
  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
};

export const useI18n = () => useContext(I18nContext);
