import React from "react";
import { ScrollView, View, Text, RefreshControl } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { ArrowDownToLine, ArrowUpFromLine } from "lucide-react-native";
import { useAuth } from "../store/auth";
import { useI18n } from "../i18n";
import { useAsync } from "../hooks";
import { getBootstrap } from "../api/endpoints";
import { C, R, Card, Ring, Donut, StatCard, Section, PageHead, Loading, ErrorBox, Row, Txt } from "../ui";

const num = (v: any) => { const n = parseFloat(String(v).replace("%", "")); return isNaN(n) ? 0 : n; };

export default function OverviewScreen() {
  const insets = useSafeAreaInsets();
  const { t } = useI18n();
  const { tenant, companies } = useAuth();
  const { data, loading, error, reload } = useAsync<any>(() => getBootstrap(), [tenant]);

  if (loading && !data) return <View style={{ flex: 1, backgroundColor: C.bg, paddingTop: insets.top }}><PageHead title={t("倉儲總覽")} /><Loading /></View>;

  const inv = (data?.INVENTORY as any[]) || [];
  const alerts = (data?.ALERTS as any[]) || [];
  const inbound = (data?.INBOUND as any[]) || [];
  const outbound = (data?.OUTBOUND as any[]) || [];
  const zones = (data?.ZONES as any[]) || [];
  const company = companies.find((c) => c.slug === tenant);

  const sku = inv.length;
  const healthy = inv.filter((i) => (i.status || "").includes("健") || i.status === "ok" || i.status === "healthy").length;
  const low = inv.filter((i) => (i.status || "").includes("低") || i.status === "low").length;
  const overdue = inv.filter((i) => (i.status || "").includes("逾") || i.status === "overdue").length;
  const healthPct = sku ? Math.round((healthy / sku) * 100) : 0;
  const capAvg = zones.length ? Math.round(zones.reduce((a, z) => a + num(z.cap), 0) / zones.length) : 0;
  const redAlerts = alerts.filter((a) => a.level === "red");

  return (
    <ScrollView style={{ flex: 1, backgroundColor: C.bg }} contentContainerStyle={{ paddingTop: insets.top, paddingBottom: 90 }}
      refreshControl={<RefreshControl refreshing={loading} onRefresh={reload} tintColor={C.blue} />}>
      <PageHead title={t("倉儲總覽")} sub={company?.name || tenant} />
      {!!error && <ErrorBox msg={error} onRetry={reload} />}

      <View style={{ flexDirection: "row", gap: 10, paddingHorizontal: 16 }}>
        <StatCard label={t("物資種類")} value={sku} accent={C.blue} />
        <StatCard label={t("今日入庫")} value={inbound.length} accent={C.teal} />
      </View>
      <View style={{ flexDirection: "row", gap: 10, paddingHorizontal: 16, marginTop: 10 }}>
        <StatCard label={t("今日出庫")} value={outbound.length} accent={C.warn} />
        <StatCard label={t("活動預警")} value={alerts.length} accent={alerts.length ? C.danger : C.ink4} />
      </View>

      <Section title={t("容量與健康")}>
        <Card>
          <Row style={{ justifyContent: "space-around" }}>
            <View style={{ alignItems: "center" }}>
              <Ring value={capAvg} color={capAvg >= 90 ? C.danger : capAvg >= 70 ? C.warn : C.blue} sub={t("平均容量")} />
              <Txt c={C.ink3} s={12} style={{ marginTop: 6 }}>{zones.length} {t("個庫區")}</Txt>
            </View>
            <View style={{ alignItems: "center" }}>
              <View style={{ width: 110, height: 110, alignItems: "center", justifyContent: "center" }}>
                <Donut size={110} data={[
                  { value: healthy, color: C.ok }, { value: low, color: C.warn }, { value: overdue, color: C.danger },
                ]} />
                <View style={{ position: "absolute", alignItems: "center" }}>
                  <Text style={{ fontSize: 22, fontWeight: "800", color: C.ink }}>{healthPct}%</Text>
                  <Text style={{ fontSize: 10.5, color: C.ink3 }}>{t("健康")}</Text>
                </View>
              </View>
              <Row gap={10} style={{ marginTop: 6 }}>
                <Row gap={4}><View style={{ width: 8, height: 8, borderRadius: 4, backgroundColor: C.ok }} /><Txt c={C.ink3} s={11}>{t("健康")} {healthy}</Txt></Row>
                <Row gap={4}><View style={{ width: 8, height: 8, borderRadius: 4, backgroundColor: C.warn }} /><Txt c={C.ink3} s={11}>{t("偏低")} {low}</Txt></Row>
              </Row>
            </View>
          </Row>
        </Card>
      </Section>

      <Section title={t("近期出入庫")}>
        <Card pad={6}>
          {[...inbound.slice(0, 3).map((x) => ({ ...x, _in: true })), ...outbound.slice(0, 3).map((x) => ({ ...x, _in: false }))].slice(0, 5).map((x, i) => (
            <Row key={i} style={{ paddingVertical: 10, paddingHorizontal: 10, borderBottomWidth: i < 4 ? 1 : 0, borderBottomColor: C.lineSoft, justifyContent: "space-between" }}>
              <Row gap={10}>
                <View style={{ width: 30, height: 30, borderRadius: 9, backgroundColor: x._in ? C.tealSoft : C.warnSoft, alignItems: "center", justifyContent: "center" }}>
                  {x._in ? <ArrowDownToLine size={16} color={C.teal} /> : <ArrowUpFromLine size={16} color={C.warn} />}
                </View>
                <View>
                  <Txt s={13.5} w="700">{x.item || x.source || x.dept || t("單據")}</Txt>
                  <Txt c={C.ink3} s={11}>{x._in ? t("入庫") : t("出庫")} · {x.qty != null ? x.qty : ""} {x.time || ""}</Txt>
                </View>
              </Row>
            </Row>
          ))}
          {inbound.length === 0 && outbound.length === 0 && <Txt c={C.ink4} s={13} style={{ padding: 14 }}>{t("暫無記錄")}</Txt>}
        </Card>
      </Section>

      {redAlerts.length > 0 && (
        <Section title={t("高風險預警")}>
          {redAlerts.slice(0, 4).map((a, i) => (
            <Card key={i} style={{ marginBottom: 8, borderLeftWidth: 3, borderLeftColor: C.danger }}>
              <Txt s={14} w="700">{a.item || a.type}</Txt>
              <Txt c={C.ink3} s={12} style={{ marginTop: 3 }}>{a.suggest || a.scope || ""}</Txt>
            </Card>
          ))}
        </Section>
      )}
      <View style={{ height: 20 }} />
    </ScrollView>
  );
}
