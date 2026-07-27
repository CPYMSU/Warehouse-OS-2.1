import React, { useState } from "react";
import { View } from "react-native";
import { NavigationContainer } from "@react-navigation/native";
import { createNativeStackNavigator } from "@react-navigation/native-stack";
import { createBottomTabNavigator } from "@react-navigation/bottom-tabs";
import { LayoutGrid, Layers, LineChart, AlertTriangle, User } from "lucide-react-native";
import { useAuth } from "../store/auth";
import { useI18n } from "../i18n";
import { C, Loading } from "../ui";
import LoginScreen from "../screens/Login";
import RegisterScreen from "../screens/Register";
import OverviewScreen from "../screens/Overview";
import ErpScreen from "../screens/Erp";
import FinanceScreen from "../screens/Finance";
import AlertsScreen from "../screens/Alerts";
import MeScreen from "../screens/Me";
import AgentFab from "../features/agent/AgentFab";

const Stack = createNativeStackNavigator();
const Tab = createBottomTabNavigator();

function Tabs() {
  const { t } = useI18n();
  const icon = (Cmp: any) => ({ color, size }: { color: string; size: number }) => <Cmp color={color} size={size} />;
  return (
    <Tab.Navigator
      screenOptions={{
        headerShown: false,
        tabBarActiveTintColor: C.blue,
        tabBarInactiveTintColor: C.ink4,
        tabBarStyle: { backgroundColor: C.surface, borderTopColor: C.line, height: 60, paddingBottom: 8, paddingTop: 6 },
        tabBarLabelStyle: { fontSize: 11, fontWeight: "600" },
      }}
    >
      <Tab.Screen name="Overview" component={OverviewScreen} options={{ title: t("總覽"), tabBarIcon: icon(LayoutGrid) }} />
      <Tab.Screen name="Erp" component={ErpScreen} options={{ title: "ERP", tabBarIcon: icon(Layers) }} />
      <Tab.Screen name="Finance" component={FinanceScreen} options={{ title: t("財務"), tabBarIcon: icon(LineChart) }} />
      <Tab.Screen name="Alerts" component={AlertsScreen} options={{ title: t("預警"), tabBarIcon: icon(AlertTriangle) }} />
      <Tab.Screen name="Me" component={MeScreen} options={{ title: t("我的"), tabBarIcon: icon(User) }} />
    </Tab.Navigator>
  );
}

export default function RootNavigator() {
  const { ready, token } = useAuth();
  const [agentOpen, setAgentOpen] = useState(false);
  if (!ready) return <View style={{ flex: 1, backgroundColor: C.bg, justifyContent: "center" }}><Loading text="載入中…" /></View>;
  return (
    <NavigationContainer>
      {token ? (
        <View style={{ flex: 1 }}>
          <Tabs />
          <AgentFab open={agentOpen} setOpen={setAgentOpen} />
        </View>
      ) : (
        <Stack.Navigator screenOptions={{ headerShown: false }}>
          <Stack.Screen name="Login" component={LoginScreen} />
          <Stack.Screen name="Register" component={RegisterScreen} />
        </Stack.Navigator>
      )}
    </NavigationContainer>
  );
}
