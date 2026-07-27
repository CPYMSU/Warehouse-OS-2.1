// AI 協作 — 緊湊版:消息 / 共創 列表。以 Modal 形式從「我的」進入(非底部 Tab)。
import React, { useState } from "react";
import { View, Text, TouchableOpacity, Modal, ScrollView } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { X } from "lucide-react-native";
import { useI18n } from "../i18n";
import { useAsync } from "../hooks";
import { collabMessages, collabIdeas } from "../api/endpoints";
import { C, R, Card, Loading, ErrorBox, Row, Txt, Badge } from "../ui";

export default function CollabModal({ visible, onClose }: { visible: boolean; onClose: () => void }) {
  const insets = useSafeAreaInsets();
  const { t } = useI18n();
  const [tab, setTab] = useState<"messages" | "ideas">("messages");
  const { data, loading, error, reload } = useAsync<any>(async () => {
    if (tab === "messages") return { list: (await collabMessages()).messages || [] };
    return { list: (await collabIdeas()).ideas || [] };
  }, [tab, visible]);

  return (
    <Modal visible={visible} animationType="slide" onRequestClose={onClose}>
      <View style={{ flex: 1, backgroundColor: C.bg, paddingTop: insets.top }}>
        <View style={{ flexDirection: "row", alignItems: "center", justifyContent: "space-between", padding: 16 }}>
          <Text style={{ fontSize: 20, fontWeight: "800", color: C.ink }}>{t("AI 協作")}</Text>
          <TouchableOpacity onPress={onClose}><X size={24} color={C.ink3} /></TouchableOpacity>
        </View>
        <View style={{ flexDirection: "row", gap: 8, paddingHorizontal: 16, marginBottom: 6 }}>
          {([["messages", "消息"], ["ideas", "共創"]] as const).map(([k, l]) => (
            <TouchableOpacity key={k} onPress={() => setTab(k)}
              style={{ paddingHorizontal: 14, paddingVertical: 7, borderRadius: R.pill, backgroundColor: tab === k ? C.blue : C.surface, borderWidth: 1, borderColor: tab === k ? C.blue : C.line }}>
              <Txt c={tab === k ? C.white : C.ink2} s={13} w="700">{t(l)}</Txt>
            </TouchableOpacity>
          ))}
        </View>

        {loading && !data ? <Loading /> : (
          <ScrollView contentContainerStyle={{ padding: 16, gap: 8, paddingBottom: 40 }}>
            {!!error && <ErrorBox msg={error} onRetry={reload} />}
            {(data?.list || []).length === 0 && <Card><Txt c={C.ink4} s={13}>{t("暫無內容")}</Txt></Card>}
            {tab === "messages" && (data?.list || []).map((m: any, i: number) => (
              <Card key={i}>
                <Row style={{ justifyContent: "space-between" }}>
                  <Txt s={14} w="700">{m.sender_name || m.recipient_name || t("消息")}</Txt>
                  {!!m.priority && <Badge text={m.priority} tone={m.priority === "urgent" ? "danger" : "blue"} />}
                </Row>
                <Txt c={C.ink2} s={13} style={{ marginTop: 5 }} numberOfLines={3}>{m.assistant_text || m.original_text || ""}</Txt>
              </Card>
            ))}
            {tab === "ideas" && (data?.list || []).map((idea: any, i: number) => (
              <Card key={i}>
                <Row style={{ justifyContent: "space-between" }}>
                  <Txt s={14.5} w="700" style={{ flex: 1 }} numberOfLines={1}>{idea.title}</Txt>
                  {!!idea.status && <Badge text={idea.status} tone="blue" />}
                </Row>
                {!!idea.ai_summary && <Txt c={C.ink2} s={12.5} style={{ marginTop: 5 }} numberOfLines={3}>{idea.ai_summary}</Txt>}
                <Txt c={C.ink4} s={11.5} style={{ marginTop: 6 }}>{t("任務")} {idea.task_done || 0}/{idea.task_total || 0}</Txt>
              </Card>
            ))}
          </ScrollView>
        )}
      </View>
    </Modal>
  );
}
