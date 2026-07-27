import React, { useEffect, useState } from "react";
import { View, Text, TextInput, KeyboardAvoidingView, Platform, ScrollView, TouchableOpacity } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { useI18n } from "../i18n";
import { registerUser, rolesForTenant } from "../api/endpoints";
import { C, R, Button } from "../ui";

const Input = (props: any) => (
  <TextInput placeholderTextColor={C.ink4} {...props}
    style={[{ backgroundColor: C.surface2, borderWidth: 1, borderColor: C.line, borderRadius: R.sm, paddingHorizontal: 14, paddingVertical: 13, fontSize: 15, color: C.ink }, props.style]} />
);
const Label = ({ children }: any) => <Text style={{ fontSize: 12.5, fontWeight: "700", color: C.ink2, marginBottom: 6, marginTop: 6 }}>{children}</Text>;

export default function RegisterScreen({ navigation }: any) {
  const insets = useSafeAreaInsets();
  const { t } = useI18n();
  const [companyCode, setCompanyCode] = useState("");
  const [username, setUsername] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [password, setPassword] = useState("");
  const [contact, setContact] = useState("");
  const [roles, setRoles] = useState<any[]>([]);
  const [roleId, setRoleId] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [ok, setOk] = useState("");

  useEffect(() => {
    const code = companyCode.trim().toLowerCase();
    if (!code) { setRoles([]); return; }
    const h = setTimeout(() => {
      rolesForTenant(code).then((d: any) => setRoles(d.roles || [])).catch(() => setRoles([]));
    }, 300);
    return () => clearTimeout(h);
  }, [companyCode]);

  const submit = async () => {
    if (!companyCode.trim() || !username.trim() || !password) { setErr(t("公司代碼、帳號、密碼必填")); return; }
    setBusy(true); setErr(""); setOk("");
    try {
      await registerUser({
        username: username.trim(),
        tenant_slug: companyCode.trim().toLowerCase(),
        display_name: displayName.trim() || username.trim(),
        password, contact: contact.trim() || undefined,
        requested_role_id: roleId || null,
      });
      setOk(t("註冊已提交,等待公司管理員審批後即可登入"));
    } catch (e: any) { setErr(e?.message || t("註冊失敗")); }
    finally { setBusy(false); }
  };

  return (
    <KeyboardAvoidingView behavior={Platform.OS === "ios" ? "padding" : undefined} style={{ flex: 1, backgroundColor: C.bg }}>
      <ScrollView contentContainerStyle={{ padding: 24, paddingTop: insets.top + 24, paddingBottom: 40 }}>
        <Text style={{ fontSize: 22, fontWeight: "800", color: C.ink, marginBottom: 4 }}>{t("註冊並加入公司")}</Text>
        <Text style={{ fontSize: 12.5, color: C.ink3, marginBottom: 16 }}>{t("輸入公司代碼,提交後由管理員審批")}</Text>

        {!!err && <View style={{ backgroundColor: C.dangerSoft, borderRadius: R.sm, padding: 12, marginBottom: 12 }}><Text style={{ color: "#B91C1C", fontWeight: "700", fontSize: 13 }}>{err}</Text></View>}
        {!!ok && <View style={{ backgroundColor: C.okSoft, borderRadius: R.sm, padding: 12, marginBottom: 12 }}><Text style={{ color: "#047857", fontWeight: "700", fontSize: 13 }}>{ok}</Text></View>}

        <Label>{t("公司代碼")}</Label>
        <Input placeholder="company-code" autoCapitalize="none" value={companyCode} onChangeText={setCompanyCode} />
        <Label>{t("帳號")}</Label>
        <Input placeholder={t("登入帳號")} autoCapitalize="none" value={username} onChangeText={setUsername} />
        <Label>{t("姓名")}</Label>
        <Input placeholder={t("顯示姓名")} value={displayName} onChangeText={setDisplayName} />
        <Label>{t("密碼")}</Label>
        <Input placeholder={t("設置密碼")} secureTextEntry value={password} onChangeText={setPassword} />
        <Label>{t("聯繫方式(選填)")}</Label>
        <Input placeholder={t("電話 / 郵箱")} value={contact} onChangeText={setContact} />

        {roles.length > 0 && (
          <>
            <Label>{t("申請角色(選填)")}</Label>
            <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 8 }}>
              {roles.map((r: any) => (
                <TouchableOpacity key={r.id} onPress={() => setRoleId(roleId === String(r.id) ? null : String(r.id))}
                  style={{ paddingHorizontal: 12, paddingVertical: 8, borderRadius: R.pill, borderWidth: 1, borderColor: roleId === String(r.id) ? C.blue : C.line, backgroundColor: roleId === String(r.id) ? C.blueSoft : C.surface }}>
                  <Text style={{ color: roleId === String(r.id) ? C.blueDeep : C.ink2, fontSize: 13, fontWeight: "600" }}>{r.name}</Text>
                </TouchableOpacity>
              ))}
            </View>
          </>
        )}

        <Button title={t("提交註冊")} onPress={submit} loading={busy} style={{ marginTop: 20 }} />
        <TouchableOpacity onPress={() => navigation.goBack()} style={{ marginTop: 16, alignItems: "center" }}>
          <Text style={{ color: C.blue, fontWeight: "700", fontSize: 14 }}>{t("已有帳號?返回登入")}</Text>
        </TouchableOpacity>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}
