# 智能倉儲 — 手機原生 App(React Native / Expo)

手機版 v1。後端**完全不改**,App 直連同一套 REST API(默認生產 `https://ncsyaikg.com`)。

## 模塊(底部 5 Tab + 全局 AI 秘書)
- 總覽 / ERP 中樞 / AI 財務 / 智能預警 / 我的
- 右下角浮動 **AI 秘書**:以自然語言提交業務目標，與網頁終端共用 Auto Runtime 的 NDJSON 流
- 「我的 → AI 協作」:消息 / 共創

## 運行(開發)
```bash
cd mobile
npm install
npx expo start          # 手機裝 Expo Go App 掃碼即真機運行
# 或:
npx expo start --web    # 瀏覽器預覽(react-native-web)
```
聯調本地後端:`EXPO_PUBLIC_API_BASE=http://<你的IP>:8090 npx expo start`

## 出安裝包(上架)
```bash
npm i -g eas-cli && eas login
eas build -p android      # 或 -p ios(需 Apple 開發者帳號)
```

## 技術
Expo SDK 52 · React Navigation(bottom-tabs)· react-native-svg(圖表)·
lucide-react-native(圖標)· expo-secure-store(token,web 退回 AsyncStorage)。
登錄態為全局身份(Model B):token + `X-Tenant-Slug`,可多公司切換。

## 與網頁的關係
這是獨立原生工程,不復用網頁 `frontend/*.jsx`;復用的是後端 API 契約、
登錄態模型、設計 token(`src/theme.ts`)與繁簡轉換表(`src/i18n`)。
不走網站部署管線(獨立 Expo 構建)。
