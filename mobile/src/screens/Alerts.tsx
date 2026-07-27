import React, { useState } from "react";
import { ScrollView, View, RefreshControl, TouchableOpacity } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { useAuth } from "../store/auth";
import { useI18n } from "../i18n";
import { useAsync } from "../hooks";
import { getBootstrap, alertsScan, alertAction } from "../api/endpoints";
import { C, R, Card, StatCard, PageHead, Loading, ErrorBox, Row, Txt, Button } from "../ui";
import { levelColor } from "../theme";

const LEVELS: [string, string][] = [["red", "緊急"], ["orange", "高"], ["yellow", "中"], ["blue", "提示"]];

export default function AlertsScreen() {
  const insets = useSafeAreaInsets();
  const { t } = useI18n();
  const { tenant } = useAuth();
  const { data, loading, error, reload } = useAsync<any>(() => getBootstrap(), [tenant]);
  const [busy, setBusy] = useState(false);

  if (loading && !data) return <View style={{ flex: 1, backgroundColor: C.bg, paddingTop: insets.top }}><PageHead title={t("智能預警")} /><Loading /></View>;

  const alerts: any[] = (data?.ALERTS as any[]) || [];
  const byLevel = (lv: string) => alerts.filter((a) => (a.level || "blue") === lv);

  const scan = async () => { setBusy(true); try { await alertsScan(); await reload(); } catch (_) {} finally { setBusy(false); } };
  const act = async (id: any, action: "resolve" | "dismiss") => { try { await alertAction(id, action); await reload(); } catch (_) {} };

  return (
    <ScrollView style={{ flex: 1, backgroundColor: C.bg }} contentContainerStyle={{ paddingTop: insets.top, paddingBottom: 90 }}
      refreshControl={<RefreshControl refreshing={loading} onRefresh={reload} tintColor={C.blue} />}>
      <PageHead title={t("智能預警")} sub={`${alerts.length} ${t("條活動預警")}`}
        right={<TouchableOpacity onPress={scan} disabled={busy} style={{ backgroundColor: C.blue, borderRadius: R.pill, paddingHorizontal: 14, paddingVertical: 7 }}><Txt c={C.white} s={13} w="700">{busy ? t("掃描中…") : t("AI 掃描")}</Txt></TouchableOpacity>} />
      {!!error && <ErrorBox msg={error} onRetry={reload} />}

      <View style={{ flexDirection: "row", gap: 10, paddingHorizontal: 16 }}>
        <StatCard label={t("緊急")} value={byLevel("red").length} accent={C.danger} />
        <StatCard label={t("高風險")} value={byLevel("orange").length} accent={C.warn} />
        <StatCard label={t("提示")} value={byLevel("yellow").length + byLevel("blue").length} accent={C.blue} />
      </View>

      {alerts.length === 0 && <Card style={{ marginHorizontal: 16, marginTop: 18 }}><Txt c={C.ink4} s={13}>{t("目前沒有預警 ✓")}</Txt></Card>}

      {LEVELS.map(([lv, label]) => {
        const list = byLevel(lv);
        if (!list.length) return null;
        return (
          <View key={lv} style={{ paddingHorizontal: 16, marginTop: 18 }}>
            <Row gap={6} style={{ marginBottom: 8 }}>
              <View style={{ width: 10, height: 10, borderRadius: 5, backgroundColor: levelColor[lv] }} />
              <Txt s={14} w="800">{t(label)} · {list.length}</Txt>
            </Row>
            {list.map((a, i) => (
              <Card key={i} style={{ marginBottom: 8, borderLeftWidth: 3, borderLeftColor: levelColor[lv] }}>
                <Txt s={14.5} w="700">{a.item || a.type}</Txt>
                <Txt c={C.ink3} s={12} style={{ marginTop: 3 }}>{a.code ? `${a.code} · ` : ""}{a.scope || ""}</Txt>
                {!!a.suggest && <Txt c={C.ink2} s={12.5} style={{ marginTop: 6 }}>{a.suggest}</Txt>}
                <Row gap={8} style={{ marginTop: 10 }}>
                  <Button title={t("處置")} tone="primary" onPress={() => act(a.id, "resolve")} style={{ flex: 1, paddingVertical: 9 }} />
                  <Button title={t("忽略")} tone="ghost" onPress={() => act(a.id, "dismiss")} style={{ flex: 1, paddingVertical: 9 }} />
                </Row>
              </Card>
            ))}
          </View>
        );
      })}
      <View style={{ height: 20 }} />
    </ScrollView>
  );
}
