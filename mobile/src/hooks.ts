import { useCallback, useEffect, useState } from "react";

// 簡單的異步數據 hook:loading/error/reload。隨依賴變化自動重取。
export function useAsync<T>(fn: () => Promise<T>, deps: any[] = []) {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const run = useCallback(() => {
    setLoading(true); setError("");
    fn().then(setData).catch((e: any) => setError(e?.message || String(e))).finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  useEffect(() => { run(); }, [run]);
  return { data, loading, error, reload: run };
}

export const fmtMoney = (n: number) => {
  const v = Number(n) || 0;
  if (Math.abs(v) >= 1e8) return (v / 1e8).toFixed(2) + " 億";
  if (Math.abs(v) >= 1e4) return (v / 1e4).toFixed(2) + " 萬";
  return v.toLocaleString("zh-Hant");
};
