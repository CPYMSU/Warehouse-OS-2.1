// 全局 AI 秘書 — 浮動按鈕 + 底部抽屜；只作 Auto Runtime 的行動端表面。
import React, { useCallback, useEffect, useRef, useState } from "react";
import { View, Text, TextInput, TouchableOpacity, Modal, ScrollView, KeyboardAvoidingView, Platform, ActivityIndicator } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { Sparkles, X, Send } from "lucide-react-native";
import { currentToken, currentSlug, useAuth } from "../../store/auth";
import { useI18n } from "../../i18n";
import { streamNDJSON } from "../../api/stream";
import { assistantBootstrap } from "../../api/endpoints";
import { C, R, Button } from "../../ui";

type Msg = { role: "user" | "assistant"; text: string };

export default function AgentFab({ open, setOpen }: { open: boolean; setOpen: (v: boolean) => void }) {
  const insets = useSafeAreaInsets();
  const { t } = useI18n();
  const auth = useAuth();
  const authActor = auth.user?.id || auth.user?.username || "";
  // Include the session token so a re-login as the same user cannot reuse an old
  // restore/stream callback. The identity is never rendered or persisted here.
  const authIdentity = auth.ready && auth.token && auth.tenant
    ? `${authActor}\u001f${auth.tenant}\u001f${auth.token}` : "";
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [restoring, setRestoring] = useState(false);
  const [restoreReady, setRestoreReady] = useState(false);
  const [restoreError, setRestoreError] = useState("");
  const [restoreNonce, setRestoreNonce] = useState(0);
  const convId = useRef<string | null>(null);
  const restorePromise = useRef<Promise<void>>(Promise.resolve());
  const restoreReadyRef = useRef(false);
  const restoreGeneration = useRef(0);
  const streamGeneration = useRef(0);
  const streamingRef = useRef(false);
  const streamCancelRef = useRef<null | (() => void)>(null);
  const identityRef = useRef(authIdentity);
  const previousIdentity = useRef(authIdentity);
  const openRef = useRef(open);
  const tRef = useRef(t);
  const scrollRef = useRef<ScrollView>(null);

  identityRef.current = authIdentity;
  openRef.current = open;
  tRef.current = t;

  const setRestoreAvailability = useCallback((ready: boolean) => {
    restoreReadyRef.current = ready;
    setRestoreReady(ready);
  }, []);

  const startRestore = useCallback(() => {
    if (!openRef.current || !auth.ready || !authIdentity || streamingRef.current) {
      return Promise.resolve();
    }

    const generation = ++restoreGeneration.current;
    const expectedIdentity = authIdentity;
    const isCurrent = () => (
      generation === restoreGeneration.current
      && expectedIdentity === identityRef.current
      && openRef.current
    );

    convId.current = null;
    setMsgs([]);
    setRestoreAvailability(false);
    setRestoreError("");
    setRestoring(true);

    const task: Promise<void> = assistantBootstrap(80)
      .then((payload: any) => {
        if (!isCurrent()) return;
        convId.current = payload?.conversation?.id
          ? String(payload.conversation.id) : null;
        const history: Msg[] = (payload?.messages || [])
          .filter((message: any) => message?.role === "user" || message?.role === "assistant")
          .map((message: any) => ({
            role: message.role,
            text: String(message.content || ""),
            cards: [],
          }));
        setMsgs(history);
        setRestoreAvailability(true);
      })
      .catch((error: any) => {
        if (!isCurrent()) return;
        convId.current = null;
        setMsgs([]);
        setRestoreAvailability(false);
        setRestoreError(error?.message || tRef.current("會話恢復失敗"));
      })
      .finally(() => {
        if (isCurrent()) setRestoring(false);
      });
    restorePromise.current = task;
    return task;
  }, [auth.ready, authIdentity, setRestoreAvailability]);

  // A tenant/account/session change is a hard boundary. Invalidate both classes
  // of asynchronous callbacks before clearing any state from the old identity.
  useEffect(() => {
    if (previousIdentity.current === authIdentity) return;
    previousIdentity.current = authIdentity;
    ++restoreGeneration.current;
    ++streamGeneration.current;
    streamCancelRef.current?.();
    streamCancelRef.current = null;
    streamingRef.current = false;
    restorePromise.current = Promise.resolve();
    convId.current = null;
    setStreaming(false);
    setRestoring(false);
    setRestoreAvailability(false);
    setRestoreError("");
    setInput("");
    setMsgs([]);
  }, [authIdentity, setRestoreAvailability]);

  useEffect(() => () => {
    ++restoreGeneration.current;
    ++streamGeneration.current;
    streamCancelRef.current?.();
    streamCancelRef.current = null;
  }, []);

  useEffect(() => {
    if (!open) {
      ++restoreGeneration.current;
      setRestoring(false);
      return;
    }
    if (!auth.ready) {
      setRestoreAvailability(false);
      setRestoreError("");
      setRestoring(true);
      return;
    }
    if (!authIdentity) {
      setRestoreAvailability(false);
      setRestoreError(tRef.current("登入狀態或目前公司無效，無法恢復會話"));
      setRestoring(false);
      return;
    }
    // Closing and reopening during a live stream keeps the live turn; starting
    // a bootstrap here could replace it with an older persisted snapshot.
    if (streamingRef.current) return;
    const taskGeneration = restoreGeneration.current + 1;
    startRestore();
    return () => {
      if (restoreGeneration.current === taskGeneration) ++restoreGeneration.current;
    };
  }, [open, auth.ready, authIdentity, restoreNonce, setRestoreAvailability, startRestore]);

  const retryRestore = () => {
    if (!restoring && !streamingRef.current) setRestoreNonce((value) => value + 1);
  };

  const send = async () => {
    const text = input.trim();
    const expectedIdentity = identityRef.current;
    if (!text || streamingRef.current || restoring || !expectedIdentity) return;
    await restorePromise.current;
    if (!restoreReadyRef.current || expectedIdentity !== identityRef.current) return;
    const generation = ++streamGeneration.current;
    const isCurrentStream = () => (
      generation === streamGeneration.current
      && expectedIdentity === identityRef.current
    );
    setInput("");
    setMsgs((m) => [...m, { role: "user", text }, { role: "assistant", text: "" }]);
    ++restoreGeneration.current;
    streamingRef.current = true;
    setStreaming(true);
    const update = (patch: (a: Msg) => Msg) => {
      if (!isCurrentStream()) return;
      setMsgs((m) => {
        if (!isCurrentStream()) return m;
        const c = [...m];
        const i = c.length - 1;
        if (i >= 0 && c[i].role === "assistant") c[i] = patch(c[i]);
        return c;
      });
    };

    try {
      streamCancelRef.current = streamNDJSON("/api/agent/run/stream",
        { text, conversation_id: convId.current || undefined, surface: "mobile" },
        {
        token: currentToken(), slug: currentSlug(),
        onEvent: (e) => {
          if (!isCurrentStream()) return;
          if (e.event === "run_start" && e.conversation_id) convId.current = e.conversation_id;
          else if (e.event === "final") update((a) => ({
            ...a,
            text: e.message || a.text,
          }));
          }));
          setTimeout(() => scrollRef.current?.scrollToEnd({ animated: true }), 30);
        },
        onError: (msg) => {
          if (!isCurrentStream()) return;
          update((a) => ({ ...a, text: a.text || ("⚠ " + msg) }));
          streamCancelRef.current = null;
          streamingRef.current = false;
          setStreaming(false);
        },
        onDone: () => {
          if (!isCurrentStream()) return;
          streamCancelRef.current = null;
          streamingRef.current = false;
          setStreaming(false);
        },
        });
    } catch (error: any) {
      if (!isCurrentStream()) return;
      update((a) => ({ ...a, text: a.text || ("⚠ " + (error?.message || t("請求失敗"))) }));
      streamCancelRef.current = null;
      streamingRef.current = false;
      setStreaming(false);
    }
  };

  return (
    <>
      {!open && (
        <TouchableOpacity activeOpacity={0.9} onPress={() => setOpen(true)}
          style={{ position: "absolute", right: 16, bottom: 76, width: 56, height: 56, borderRadius: 28, backgroundColor: C.blue, alignItems: "center", justifyContent: "center", shadowColor: C.blue, shadowOpacity: 0.4, shadowRadius: 12, shadowOffset: { width: 0, height: 6 }, elevation: 6 }}>
          <Sparkles size={26} color={C.white} />
        </TouchableOpacity>
      )}

      <Modal visible={open} animationType="slide" transparent onRequestClose={() => setOpen(false)}>
        <View style={{ flex: 1, backgroundColor: "rgba(0,0,0,0.3)" }}>
          <TouchableOpacity style={{ height: insets.top + 40 }} onPress={() => setOpen(false)} />
          <KeyboardAvoidingView behavior={Platform.OS === "ios" ? "padding" : undefined} style={{ flex: 1, backgroundColor: C.bg, borderTopLeftRadius: 22, borderTopRightRadius: 22, overflow: "hidden" }}>
            <View style={{ flexDirection: "row", alignItems: "center", justifyContent: "space-between", padding: 16, borderBottomWidth: 1, borderBottomColor: C.line }}>
              <View style={{ flexDirection: "row", alignItems: "center", gap: 8 }}>
                <Sparkles size={20} color={C.blue} /><Text style={{ fontSize: 16, fontWeight: "800", color: C.ink }}>{t("公司 AI 秘書")}</Text>
              </View>
              <TouchableOpacity onPress={() => setOpen(false)}><X size={22} color={C.ink3} /></TouchableOpacity>
            </View>

            <ScrollView ref={scrollRef} style={{ flex: 1 }} contentContainerStyle={{ padding: 14, gap: 10 }}>
              {restoring && msgs.length === 0 && (
                <View style={{ paddingTop: 36, alignItems: "center", gap: 10 }}>
                  <ActivityIndicator color={C.blue} />
                  <Text style={{ color: C.ink3, fontSize: 13 }}>{t("正在恢復會話…")}</Text>
                </View>
              )}
              {!restoring && !!restoreError && (
                <View style={{ marginTop: 24, padding: 14, backgroundColor: C.warnSoft, borderRadius: R.md, alignItems: "center", gap: 10 }}>
                  <Text style={{ color: C.danger, fontSize: 13, textAlign: "center" }}>⚠ {restoreError}</Text>
                  <Button title={t("重試恢復")} onPress={retryRestore} style={{ paddingHorizontal: 18, paddingVertical: 9 }} />
                </View>
              )}
              {restoreReady && msgs.length === 0 && (
                <View style={{ paddingTop: 30, alignItems: "center" }}>
                  <Text style={{ color: C.ink3, fontSize: 13, textAlign: "center" }}>{t("用自然語言描述想達到的業務結果,例如:")}</Text>
                  {[t("幫我判斷本週哪些物資短缺風險最高"), t("整理目前採購目標與需要的證據"), t("分析工單堵塞的下一步")].map((ex, i) => (
                    <TouchableOpacity key={i} onPress={() => setInput(ex)} style={{ backgroundColor: C.surface, borderRadius: R.pill, paddingHorizontal: 14, paddingVertical: 8, marginTop: 8, borderWidth: 1, borderColor: C.line }}>
                      <Text style={{ color: C.blueDeep, fontSize: 13 }}>{ex}</Text>
                    </TouchableOpacity>
                  ))}
                </View>
              )}
              {msgs.map((m, i) => (
                <View key={i} style={{ alignItems: m.role === "user" ? "flex-end" : "flex-start" }}>
                  <View style={{ maxWidth: "86%", backgroundColor: m.role === "user" ? C.blue : C.surface, borderRadius: 14, padding: 12, borderWidth: m.role === "user" ? 0 : 1, borderColor: C.line }}>
                    {!!m.text && <Text style={{ color: m.role === "user" ? C.white : C.ink, fontSize: 14, lineHeight: 20 }}>{m.text}</Text>}
                  </View>
                </View>
              ))}
            </ScrollView>

            <View style={{ flexDirection: "row", alignItems: "flex-end", gap: 8, padding: 12, paddingBottom: insets.bottom + 12, borderTopWidth: 1, borderTopColor: C.line, backgroundColor: C.surface }}>
              <TextInput value={input} onChangeText={setInput} placeholder={t("描述想達到的業務結果…")} placeholderTextColor={C.ink4} multiline
                editable={restoreReady && !restoring && !streaming}
                style={{ flex: 1, maxHeight: 100, backgroundColor: C.surface2, borderRadius: R.md, paddingHorizontal: 14, paddingVertical: 10, fontSize: 14.5, color: C.ink }} />
              <TouchableOpacity onPress={send} disabled={streaming || restoring || !restoreReady || !input.trim()}
                style={{ width: 44, height: 44, borderRadius: 22, backgroundColor: streaming || restoring || !restoreReady || !input.trim() ? C.ink4 : C.blue, alignItems: "center", justifyContent: "center" }}>
                {streaming || restoring ? <ActivityIndicator color={C.white} /> : <Send size={20} color={C.white} />}
              </TouchableOpacity>
            </View>
          </KeyboardAvoidingView>
        </View>
      </Modal>
    </>
  );
}
