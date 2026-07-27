import React, { useState } from "react";
import { ScrollView, View, TextInput, TouchableOpacity, Modal, Alert } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { Building2, Languages, KeyRound, Bell, Check, Users } from "lucide-react-native";
import { useAuth } from "../store/auth";
import { useI18n, Lang } from "../i18n";
import { useAsync } from "../hooks";
import { notificationsSummary, changePassword, joinCompany } from "../api/endpoints";
import { C, R, Card, PageHead, Row, Txt, Button } from "../ui";
import CollabModal from "./Collab";

const Item: React.FC<{ icon: React.ReactNode; label: string; value?: string; onPress?: () => void; right?: React.ReactNode }> =
  ({ icon, label, value, onPress, right }) => (
    <TouchableOpacity disabled={!onPress} onPress={onPress} activeOpacity={0.7}
      style={{ flexDirection: "row", alignItems: "center", paddingVertical: 14, paddingHorizontal: 14, borderBottomWidth: 1, borderBottomColor: C.lineSoft, gap: 12 }}>
      <View style={{ width: 34, height: 34, borderRadius: 10, backgroundColor: C.blueSoft, alignItems: "center", justifyContent: "center" }}>{icon}</View>
      <Txt s={14.5} w="600" style={{ flex: 1 }}>{label}</Txt>
      {!!value && <Txt c={C.ink3} s={13}>{value}</Txt>}
      {right}
    </TouchableOpacity>
  );

export default function MeScreen() {
  const insets = useSafeAreaInsets();
  const { t, lang, setLang } = useI18n();
  const { user, companies, tenant, switchCompany, signOut } = useAuth();
  const { data: notif } = useAsync<any>(() => notificationsSummary().catch(() => ({ count: 0 })), [tenant]);
  const [showCompany, setShowCompany] = useState(false);
  const [showPwd, setShowPwd] = useState(false);
  const [showJoin, setShowJoin] = useState(false);
  const [showCollab, setShowCollab] = useState(false);

  const company = companies.find((c) => c.slug === tenant);

  return (
    <ScrollView style={{ flex: 1, backgroundColor: C.bg }} contentContainerStyle={{ paddingTop: insets.top, paddingBottom: 90 }}>
      <PageHead title={t("我的")} />

      <Card style={{ marginHorizontal: 16 }}>
        <Row gap={14}>
          <View style={{ width: 54, height: 54, borderRadius: 16, backgroundColor: C.blue, alignItems: "center", justifyContent: "center" }}>
            <Txt c={C.white} s={22} w="800">{(user?.display_name || user?.username || "?").slice(0, 1)}</Txt>
          </View>
          <View style={{ flex: 1 }}>
            <Txt s={17} w="800">{user?.display_name || user?.username}</Txt>
            <Txt c={C.ink3} s={12.5} style={{ marginTop: 2 }}>{(user?.role_names || []).join("、") || t("成員")}</Txt>
          </View>
        </Row>
      </Card>

      <Card style={{ marginHorizontal: 16, marginTop: 14 }} pad={0}>
        <Item icon={<Building2 size={18} color={C.blue} />} label={t("當前公司")} value={company?.name || tenant} onPress={() => setShowCompany(true)} />
        <Item icon={<Users size={18} color={C.blue} />} label={t("AI 協作")} onPress={() => setShowCollab(true)} />
        <Item icon={<Bell size={18} color={C.blue} />} label={t("通知")} value={notif?.count ? String(notif.count) : t("無")} />
        <Item icon={<Languages size={18} color={C.blue} />} label={t("語言")}
          right={
            <Row gap={4} style={{ backgroundColor: C.surface2, borderRadius: R.pill, padding: 3 }}>
              {(["zh-Hant", "zh-Hans"] as Lang[]).map((l) => (
                <TouchableOpacity key={l} onPress={() => setLang(l)} style={{ paddingHorizontal: 12, paddingVertical: 5, borderRadius: R.pill, backgroundColor: lang === l ? C.blue : "transparent" }}>
                  <Txt c={lang === l ? C.white : C.ink3} s={13} w="700">{l === "zh-Hant" ? "繁" : "简"}</Txt>
                </TouchableOpacity>
              ))}
            </Row>
          } />
        <Item icon={<KeyRound size={18} color={C.blue} />} label={t("修改密碼")} onPress={() => setShowPwd(true)} />
      </Card>

      <View style={{ paddingHorizontal: 16, marginTop: 20 }}>
        <Button title={t("退出登入")} tone="danger" onPress={() => Alert.alert(t("退出登入"), t("確定退出?"), [{ text: t("取消") }, { text: t("退出"), style: "destructive", onPress: signOut }])} />
      </View>

      <CompanyModal visible={showCompany} onClose={() => setShowCompany(false)}
        companies={companies} tenant={tenant} onPick={(s: string) => { switchCompany(s); setShowCompany(false); }}
        onJoin={() => { setShowCompany(false); setShowJoin(true); }} />
      <PasswordModal visible={showPwd} onClose={() => setShowPwd(false)} />
      <JoinModal visible={showJoin} onClose={() => setShowJoin(false)} />
      <CollabModal visible={showCollab} onClose={() => setShowCollab(false)} />
    </ScrollView>
  );
}

const Sheet: React.FC<{ visible: boolean; onClose: () => void; title: string; children: React.ReactNode }> = ({ visible, onClose, title, children }) => (
  <Modal visible={visible} transparent animationType="slide" onRequestClose={onClose}>
    <View style={{ flex: 1, backgroundColor: "rgba(0,0,0,0.35)", justifyContent: "flex-end" }}>
      <TouchableOpacity style={{ flex: 1 }} onPress={onClose} />
      <View style={{ backgroundColor: C.bg, borderTopLeftRadius: 22, borderTopRightRadius: 22, padding: 18, paddingBottom: 34 }}>
        <View style={{ width: 40, height: 4, borderRadius: 2, backgroundColor: C.line, alignSelf: "center", marginBottom: 14 }} />
        <Txt s={17} w="800" style={{ marginBottom: 14 }}>{title}</Txt>
        {children}
      </View>
    </View>
  </Modal>
);

function CompanyModal({ visible, onClose, companies, tenant, onPick, onJoin }: any) {
  const { t } = useI18n();
  return (
    <Sheet visible={visible} onClose={onClose} title={t("切換公司")}>
      {companies.map((c: any) => (
        <TouchableOpacity key={c.slug} onPress={() => onPick(c.slug)}
          style={{ flexDirection: "row", alignItems: "center", justifyContent: "space-between", paddingVertical: 13, paddingHorizontal: 14, backgroundColor: C.surface, borderRadius: R.sm, marginBottom: 8, borderWidth: 1, borderColor: c.slug === tenant ? C.blue : C.line }}>
          <View><Txt s={14.5} w="700">{c.name}</Txt><Txt c={C.ink3} s={12}>{c.role || c.slug}</Txt></View>
          {c.slug === tenant && <Check size={18} color={C.blue} />}
        </TouchableOpacity>
      ))}
      <Button title={t("加入其他公司")} tone="ghost" onPress={onJoin} style={{ marginTop: 6 }} />
    </Sheet>
  );
}

function PasswordModal({ visible, onClose }: any) {
  const { t } = useI18n();
  const [cur, setCur] = useState(""); const [next, setNext] = useState("");
  const [busy, setBusy] = useState(false); const [msg, setMsg] = useState("");
  const submit = async () => {
    if (!cur || !next) { setMsg(t("請填寫完整")); return; }
    setBusy(true); setMsg("");
    try { await changePassword(cur, next); setMsg(t("✓ 已修改")); setCur(""); setNext(""); }
    catch (e: any) { setMsg(e?.message || t("失敗")); } finally { setBusy(false); }
  };
  const inp = { placeholderTextColor: C.ink4, style: { backgroundColor: C.surface, borderWidth: 1, borderColor: C.line, borderRadius: R.sm, paddingHorizontal: 14, paddingVertical: 12, fontSize: 15, color: C.ink, marginBottom: 10 } };
  return (
    <Sheet visible={visible} onClose={onClose} title={t("修改密碼")}>
      <TextInput placeholder={t("當前密碼")} secureTextEntry value={cur} onChangeText={setCur} {...inp} />
      <TextInput placeholder={t("新密碼")} secureTextEntry value={next} onChangeText={setNext} {...inp} />
      {!!msg && <Txt c={msg.startsWith("✓") ? C.ok : C.danger} s={13} w="700" style={{ marginBottom: 8 }}>{msg}</Txt>}
      <Button title={t("確認修改")} onPress={submit} loading={busy} />
    </Sheet>
  );
}

function JoinModal({ visible, onClose }: any) {
  const { t } = useI18n();
  const [slug, setSlug] = useState(""); const [busy, setBusy] = useState(false); const [msg, setMsg] = useState("");
  const submit = async () => {
    if (!slug.trim()) return;
    setBusy(true); setMsg("");
    try { await joinCompany(slug.trim().toLowerCase()); setMsg(t("✓ 申請已提交,待審批")); setSlug(""); }
    catch (e: any) { setMsg(e?.message || t("失敗")); } finally { setBusy(false); }
  };
  return (
    <Sheet visible={visible} onClose={onClose} title={t("加入公司")}>
      <Txt c={C.ink3} s={12.5} style={{ marginBottom: 10 }}>{t("輸入公司代碼,提交後由該公司管理員審批")}</Txt>
      <TextInput placeholder="company-code" autoCapitalize="none" placeholderTextColor={C.ink4} value={slug} onChangeText={setSlug}
        style={{ backgroundColor: C.surface, borderWidth: 1, borderColor: C.line, borderRadius: R.sm, paddingHorizontal: 14, paddingVertical: 12, fontSize: 15, color: C.ink, marginBottom: 10 }} />
      {!!msg && <Txt c={msg.startsWith("✓") ? C.ok : C.danger} s={13} w="700" style={{ marginBottom: 8 }}>{msg}</Txt>}
      <Button title={t("提交申請")} onPress={submit} loading={busy} />
    </Sheet>
  );
}
