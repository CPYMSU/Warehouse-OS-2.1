import React, { useMemo, useState } from "react";
import { ScrollView, View, RefreshControl, TouchableOpacity } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { useAuth } from "../store/auth";
import { useI18n } from "../i18n";
import { useAsync, fmtMoney } from "../hooks";
import { glIncome, glBalanceSheet, glCashflow, glAp, glAr, glTrialBalance } from "../api/endpoints";
import { C, R, Card, StatCard, Section, PageHead, Loading, ErrorBox, Row, Txt, Badge } from "../ui";

const periodOf = (kind: "m" | "q" | "y") => {
  const now = new Date();
  const y = now.getFullYear();
  const m = now.getMonth() + 1;
  if (kind === "m") return `${y}-${String(m).padStart(2, "0")}`;
  if (kind === "q") return `${y}-Q${Math.floor((m - 1) / 3) + 1}`;
  return `${y}`;
};

export default function FinanceScreen() {
  const insets = useSafeAreaInsets();
  const { t } = useI18n();
  const { tenant } = useAuth();
  const [pk, setPk] = useState<"m" | "q" | "y">("m");
  const period = useMemo(() => periodOf(pk), [pk]);

  const { data, loading, error, reload } = useAsync<any>(async () => {
    const [income, bs, cf, ap, ar, tb] = await Promise.all([
      glIncome(period).catch(() => null),
      glBalanceSheet().catch(() => null),
      glCashflow(period).catch(() => null),
      glAp().catch(() => null),
      glAr().catch(() => null),
      glTrialBalance().catch(() => null),
    ]);
    return { income, bs, cf, ap, ar, tb };
  }, [tenant, period]);

  if (loading && !data) return <View style={{ flex: 1, backgroundColor: C.bg, paddingTop: insets.top }}><PageHead title="AI 財務" /><Loading /></View>;

  const inc = data?.income || {}, bs = data?.bs || {}, cf = data?.cf || {}, ap = data?.ap || {}, ar = data?.ar || {}, tb = data?.tb || {};

  return (
    <ScrollView style={{ flex: 1, backgroundColor: C.bg }} contentContainerStyle={{ paddingTop: insets.top, paddingBottom: 90 }}
      refreshControl={<RefreshControl refreshing={loading} onRefresh={reload} tintColor={C.blue} />}>
      <PageHead title="AI 財務" sub={t("駕駛艙 · 三大報表")}
        right={tb && tb.balanced != null ? <Badge text={tb.balanced ? t("試算平衡") : t("未平衡")} tone={tb.balanced ? "ok" : "danger"} /> : undefined} />
      {!!error && <ErrorBox msg={error} onRetry={reload} />}

      <View style={{ flexDirection: "row", gap: 8, paddingHorizontal: 16, marginBottom: 4 }}>
        {([["m", "本月"], ["q", "本季"], ["y", "本年"]] as const).map(([k, l]) => (
          <TouchableOpacity key={k} onPress={() => setPk(k)}
            style={{ paddingHorizontal: 14, paddingVertical: 7, borderRadius: R.pill, backgroundColor: pk === k ? C.blue : C.surface, borderWidth: 1, borderColor: pk === k ? C.blue : C.line }}>
            <Txt c={pk === k ? C.white : C.ink2} s={13} w="700">{t(l)}</Txt>
          </TouchableOpacity>
        ))}
      </View>

      <View style={{ flexDirection: "row", gap: 10, paddingHorizontal: 16, marginTop: 8 }}>
        <StatCard label={t("利潤")} value={fmtMoney(inc.profit)} accent={(inc.profit || 0) >= 0 ? C.ok : C.danger} />
        <StatCard label={t("現金淨變動")} value={fmtMoney(cf.net_change)} accent={C.blue} />
      </View>
      <View style={{ flexDirection: "row", gap: 10, paddingHorizontal: 16, marginTop: 10 }}>
        <StatCard label={t("應收")} value={fmtMoney(ar.total_outstanding)} accent={C.teal} />
        <StatCard label={t("應付")} value={fmtMoney(ap.total_outstanding)} accent={C.warn} />
      </View>

      <Section title={t("利潤表")}>
        <Card>
          {[[t("收入"), inc.revenue], [t("成本"), inc.cost], [t("費用"), inc.expense], [t("利潤"), inc.profit]].map(([k, v], i) => (
            <Row key={i} style={{ justifyContent: "space-between", paddingVertical: 8, borderBottomWidth: i < 3 ? 1 : 0, borderBottomColor: C.lineSoft }}>
              <Txt c={C.ink2} s={13}>{k as string}</Txt>
              <Txt s={14} w="700">{fmtMoney(v as number)}</Txt>
            </Row>
          ))}
        </Card>
      </Section>

      <Section title={t("資產負債")}>
        <Card>
          {[[t("資產"), bs.assets], [t("負債"), bs.liabilities], [t("權益"), bs.total_equity], [t("本期利潤"), bs.current_profit]].map(([k, v], i) => (
            <Row key={i} style={{ justifyContent: "space-between", paddingVertical: 8, borderBottomWidth: i < 3 ? 1 : 0, borderBottomColor: C.lineSoft }}>
              <Txt c={C.ink2} s={13}>{k as string}</Txt>
              <Txt s={14} w="700">{fmtMoney(v as number)}</Txt>
            </Row>
          ))}
        </Card>
      </Section>

      <Card style={{ marginHorizontal: 16, marginTop: 16, backgroundColor: C.blueSoft, borderColor: C.blueSoft }}>
        <Txt c={C.blueDeep} s={13} w="700">{t("需要動賬?")}</Txt>
        <Txt c={C.ink2} s={12.5} style={{ marginTop: 4 }}>{t("付款、收款、計提折舊、期末結轉等請用右下角「AI 秘書」對話完成。")}</Txt>
      </Card>
      <View style={{ height: 20 }} />
    </ScrollView>
  );
}
