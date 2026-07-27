import React, { useState } from "react";
import { ScrollView, View, RefreshControl, TouchableOpacity } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { useAuth } from "../store/auth";
import { useI18n } from "../i18n";
import { useAsync, fmtMoney } from "../hooks";
import { erpOverview } from "../api/endpoints";
import { C, R, Card, StatCard, PageHead, Loading, ErrorBox, Row, Txt, Badge } from "../ui";

const TABS = [["budgets", "預算"], ["work_tasks", "工單"], ["purchase_requests", "採購"], ["suppliers", "供應商"]] as const;

const num = (v: any) => { const n = parseFloat(String(v)); return isNaN(n) ? 0 : n; };
const statusTone = (s: string) => {
  if (["active", "approved", "completed", "received", "ordered"].includes(s)) return "ok";
  if (["draft", "planned", "submitted"].includes(s)) return "blue";
  if (["paused", "frozen", "pending"].includes(s)) return "warn";
  return "gray";
};

export default function ErpScreen() {
  const insets = useSafeAreaInsets();
  const { t } = useI18n();
  const { tenant } = useAuth();
  const { data, loading, error, reload } = useAsync<any>(() => erpOverview(), [tenant]);
  const [tab, setTab] = useState<(typeof TABS)[number][0]>("budgets");

  if (loading && !data) return <View style={{ flex: 1, backgroundColor: C.bg, paddingTop: insets.top }}><PageHead title="ERP 中樞" /><Loading /></View>;

  const s = data?.summary || {};
  const rows: any[] = (data?.[tab] as any[]) || [];

  const title = (r: any) => r.budget_no || r.task_name || r.task_no || r.title || r.request_no || r.supplier_name || r.name || `#${r.id}`;
  const sub = (r: any) => {
    if (tab === "budgets") return `${t("可用")} ${fmtMoney(r.available)} / ${fmtMoney(r.amount)}`;
    if (tab === "work_tasks") return `${t("預算")} ${fmtMoney(r.budget_estimate)} · ${r.priority || ""}`;
    if (tab === "purchase_requests") return `${fmtMoney(r.total_amount)} · ${r.supplier_name || ""}`;
    return r.contact || r.category || "";
  };

  return (
    <ScrollView style={{ flex: 1, backgroundColor: C.bg }} contentContainerStyle={{ paddingTop: insets.top, paddingBottom: 90 }}
      refreshControl={<RefreshControl refreshing={loading} onRefresh={reload} tintColor={C.blue} />}>
      <PageHead title="ERP 中樞" sub={t("預算 · 工單 · 採購 · 供應商")} />
      {!!error && <ErrorBox msg={error} onRetry={reload} />}

      <View style={{ flexDirection: "row", gap: 10, paddingHorizontal: 16 }}>
        <StatCard label={t("預算使用")} value={`${Math.round(num(s.budget_usage))}%`} accent={C.blue} />
        <StatCard label={t("開放工單")} value={s.open_tasks ?? (data?.work_tasks?.length || 0)} accent={C.teal} />
      </View>
      <View style={{ flexDirection: "row", gap: 10, paddingHorizontal: 16, marginTop: 10 }}>
        <StatCard label={t("待處理採購")} value={s.open_purchases ?? (data?.purchase_requests?.length || 0)} accent={C.warn} />
        <StatCard label={t("供應商")} value={data?.suppliers?.length || 0} accent={C.purple} />
      </View>

      <View style={{ flexDirection: "row", gap: 8, paddingHorizontal: 16, marginTop: 18 }}>
        {TABS.map(([k, label]) => (
          <TouchableOpacity key={k} onPress={() => setTab(k)}
            style={{ paddingHorizontal: 12, paddingVertical: 8, borderRadius: R.pill, backgroundColor: tab === k ? C.blue : C.surface, borderWidth: 1, borderColor: tab === k ? C.blue : C.line }}>
            <Txt c={tab === k ? C.white : C.ink2} s={13} w="700">{t(label)}</Txt>
          </TouchableOpacity>
        ))}
      </View>

      <View style={{ paddingHorizontal: 16, marginTop: 12, gap: 8 }}>
        {rows.length === 0 && <Card><Txt c={C.ink4} s={13}>{t("暫無數據")}</Txt></Card>}
        {rows.map((r, i) => (
          <Card key={i}>
            <Row style={{ justifyContent: "space-between" }}>
              <View style={{ flex: 1, paddingRight: 8 }}>
                <Txt s={14.5} w="700" numberOfLines={1}>{title(r)}</Txt>
                <Txt c={C.ink3} s={12} style={{ marginTop: 3 }} numberOfLines={1}>{sub(r)}</Txt>
              </View>
              {!!r.status && <Badge text={r.status} tone={statusTone(r.status) as any} />}
            </Row>
          </Card>
        ))}
      </View>
      <View style={{ height: 20 }} />
    </ScrollView>
  );
}
