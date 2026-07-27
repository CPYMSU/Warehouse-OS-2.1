import React, { useState } from "react";
import { View, Text, TextInput, KeyboardAvoidingView, Platform, ScrollView, TouchableOpacity } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { useAuth } from "../store/auth";
import { useI18n } from "../i18n";
import { C, R, Button } from "../ui";

const Input = (props: any) => (
  <TextInput
    placeholderTextColor={C.ink4}
    {...props}
    style={[{ backgroundColor: C.surface2, borderWidth: 1, borderColor: C.line, borderRadius: R.sm, paddingHorizontal: 14, paddingVertical: 13, fontSize: 15, color: C.ink }, props.style]}
  />
);

export default function LoginScreen({ navigation }: any) {
  const insets = useSafeAreaInsets();
  const { signIn } = useAuth();
  const { t } = useI18n();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  const submit = async () => {
    if (!username.trim() || !password) { setErr(t("請輸入帳號和密碼")); return; }
    setBusy(true); setErr("");
    try { await signIn(username.trim(), password); }
    catch (e: any) { setErr(e?.message || t("登入失敗")); }
    finally { setBusy(false); }
  };

  return (
    <KeyboardAvoidingView behavior={Platform.OS === "ios" ? "padding" : undefined} style={{ flex: 1, backgroundColor: C.bg }}>
      <ScrollView contentContainerStyle={{ flexGrow: 1, justifyContent: "center", padding: 24, paddingTop: insets.top + 40 }}>
        <View style={{ alignItems: "center", marginBottom: 28 }}>
          <View style={{ width: 64, height: 64, borderRadius: 18, backgroundColor: C.blue, alignItems: "center", justifyContent: "center" }}>
            <Text style={{ color: C.white, fontSize: 30, fontWeight: "900" }}>倉</Text>
          </View>
          <Text style={{ fontSize: 22, fontWeight: "800", color: C.ink, marginTop: 14 }}>{t("智能倉儲管理平台")}</Text>
          <Text style={{ fontSize: 13, color: C.ink3, marginTop: 4 }}>{t("登入你的企業空間")}</Text>
        </View>

        {!!err && (
          <View style={{ backgroundColor: C.dangerSoft, borderRadius: R.sm, padding: 12, marginBottom: 14 }}>
            <Text style={{ color: "#B91C1C", fontWeight: "700", fontSize: 13 }}>{err}</Text>
          </View>
        )}

        <View style={{ gap: 12 }}>
          <Input placeholder={t("帳號 / 郵箱")} autoCapitalize="none" value={username} onChangeText={setUsername} />
          <Input placeholder={t("密碼")} secureTextEntry value={password} onChangeText={setPassword} onSubmitEditing={submit} returnKeyType="go" />
          <Button title={t("登入")} onPress={submit} loading={busy} style={{ marginTop: 6 }} />
        </View>

        <TouchableOpacity onPress={() => navigation.navigate("Register")} style={{ marginTop: 20, alignItems: "center" }}>
          <Text style={{ color: C.blue, fontWeight: "700", fontSize: 14 }}>{t("沒有帳號?註冊並加入公司")}</Text>
        </TouchableOpacity>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}
