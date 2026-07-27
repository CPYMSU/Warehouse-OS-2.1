// 持久化抽象:原生用 expo-secure-store(安全存 token);web 退回 AsyncStorage(localStorage)。
import { Platform } from "react-native";
import AsyncStorage from "@react-native-async-storage/async-storage";

let Secure: typeof import("expo-secure-store") | null = null;
if (Platform.OS !== "web") {
  // 僅原生加載,避免 web 上拋 UnavailabilityError
  Secure = require("expo-secure-store");
}

export const storageGet = async (k: string): Promise<string | null> => {
  try { return Platform.OS === "web" || !Secure ? await AsyncStorage.getItem(k) : await Secure.getItemAsync(k); }
  catch { return null; }
};
export const storageSet = async (k: string, v: string): Promise<void> => {
  try { Platform.OS === "web" || !Secure ? await AsyncStorage.setItem(k, v) : await Secure.setItemAsync(k, v); } catch {}
};
export const storageDel = async (k: string): Promise<void> => {
  try { Platform.OS === "web" || !Secure ? await AsyncStorage.removeItem(k) : await Secure.deleteItemAsync(k); } catch {}
};
