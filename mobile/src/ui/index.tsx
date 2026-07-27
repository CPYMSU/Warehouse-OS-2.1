// 共用 UI 原語 — 視覺對齊 web components.jsx。
import React from "react";
import { View, Text, TouchableOpacity, ActivityIndicator, StyleProp, ViewStyle, TextStyle } from "react-native";
import Svg, { Circle, Polyline } from "react-native-svg";
import { C, R, SP, shadow } from "../theme";

export const Card: React.FC<{ children: React.ReactNode; style?: StyleProp<ViewStyle>; pad?: number }> = ({ children, style, pad = 16 }) => (
  <View style={[{ backgroundColor: C.surface, borderRadius: R.md, padding: pad, borderWidth: 1, borderColor: C.line, ...shadow.sm }, style]}>
    {children}
  </View>
);

export const Row: React.FC<{ children: React.ReactNode; style?: StyleProp<ViewStyle>; gap?: number }> = ({ children, style, gap = 8 }) => (
  <View style={[{ flexDirection: "row", alignItems: "center", gap }, style]}>{children}</View>
);

export const Txt: React.FC<{ children: React.ReactNode; c?: string; s?: number; w?: TextStyle["fontWeight"]; style?: StyleProp<TextStyle>; numberOfLines?: number }> =
  ({ children, c = C.ink, s = 14, w = "400", style, numberOfLines }) => (
    <Text numberOfLines={numberOfLines} style={[{ color: c, fontSize: s, fontWeight: w }, style]}>{children}</Text>
  );

export const PageHead: React.FC<{ title: string; sub?: string; right?: React.ReactNode }> = ({ title, sub, right }) => (
  <View style={{ flexDirection: "row", alignItems: "flex-start", justifyContent: "space-between", paddingHorizontal: 16, paddingTop: 8, paddingBottom: 12 }}>
    <View style={{ flex: 1 }}>
      <Text style={{ fontSize: 22, fontWeight: "800", color: C.ink }}>{title}</Text>
      {!!sub && <Text style={{ fontSize: 12.5, color: C.ink3, marginTop: 3 }}>{sub}</Text>}
    </View>
    {right}
  </View>
);

export const Badge: React.FC<{ text: string; tone?: "blue" | "ok" | "warn" | "danger" | "gray" }> = ({ text, tone = "gray" }) => {
  const map = {
    blue: [C.blueSoft, C.blueDeep], ok: [C.okSoft, "#047857"], warn: [C.warnSoft, "#B45309"],
    danger: [C.dangerSoft, "#B91C1C"], gray: [C.surface2, C.ink3],
  } as const;
  const [bg, fg] = map[tone];
  return (
    <View style={{ backgroundColor: bg, borderRadius: R.pill, paddingHorizontal: 9, paddingVertical: 3 }}>
      <Text style={{ color: fg, fontSize: 11, fontWeight: "700" }}>{text}</Text>
    </View>
  );
};

export const Button: React.FC<{ title: string; onPress: () => void; tone?: "primary" | "ghost" | "danger"; loading?: boolean; disabled?: boolean; style?: StyleProp<ViewStyle> }> =
  ({ title, onPress, tone = "primary", loading, disabled, style }) => {
    const bg = tone === "primary" ? C.blue : tone === "danger" ? C.danger : C.surface2;
    const fg = tone === "ghost" ? C.ink2 : C.white;
    return (
      <TouchableOpacity activeOpacity={0.85} disabled={disabled || loading} onPress={onPress}
        style={[{ backgroundColor: disabled ? C.ink4 : bg, borderRadius: R.sm, paddingVertical: 13, alignItems: "center", justifyContent: "center" }, style]}>
        {loading ? <ActivityIndicator color={fg} /> : <Text style={{ color: fg, fontWeight: "700", fontSize: 15 }}>{title}</Text>}
      </TouchableOpacity>
    );
  };

export const StatCard: React.FC<{ label: string; value: string | number; accent?: string; sub?: string }> = ({ label, value, accent = C.blue, sub }) => (
  <Card style={{ flex: 1 }} pad={14}>
    <Text style={{ fontSize: 11.5, color: C.ink3 }}>{label}</Text>
    <Text style={{ fontSize: 26, fontWeight: "800", color: accent, marginTop: 4 }}>{value}</Text>
    {!!sub && <Text style={{ fontSize: 11, color: C.ink4, marginTop: 2 }}>{sub}</Text>}
  </Card>
);

// 環形進度(容量/健康)
export const Ring: React.FC<{ value: number; size?: number; stroke?: number; color?: string; label?: string; sub?: string }> =
  ({ value, size = 110, stroke = 12, color = C.blue, label, sub }) => {
    const r = (size - stroke) / 2;
    const circ = 2 * Math.PI * r;
    const pct = Math.max(0, Math.min(100, value));
    return (
      <View style={{ width: size, height: size, alignItems: "center", justifyContent: "center" }}>
        <Svg width={size} height={size}>
          <Circle cx={size / 2} cy={size / 2} r={r} stroke={C.line} strokeWidth={stroke} fill="none" />
          <Circle cx={size / 2} cy={size / 2} r={r} stroke={color} strokeWidth={stroke} fill="none"
            strokeDasharray={`${circ}`} strokeDashoffset={circ * (1 - pct / 100)} strokeLinecap="round"
            transform={`rotate(-90 ${size / 2} ${size / 2})`} />
        </Svg>
        <View style={{ position: "absolute", alignItems: "center" }}>
          <Text style={{ fontSize: 22, fontWeight: "800", color: C.ink }}>{label ?? `${Math.round(pct)}%`}</Text>
          {!!sub && <Text style={{ fontSize: 10.5, color: C.ink3 }}>{sub}</Text>}
        </View>
      </View>
    );
  };

// 多段甜甜圈(健康分布)
export const Donut: React.FC<{ data: { value: number; color: string }[]; size?: number; stroke?: number }> = ({ data, size = 110, stroke = 14 }) => {
  const r = (size - stroke) / 2;
  const circ = 2 * Math.PI * r;
  const total = data.reduce((a, d) => a + d.value, 0) || 1;
  let acc = 0;
  return (
    <Svg width={size} height={size}>
      <Circle cx={size / 2} cy={size / 2} r={r} stroke={C.line} strokeWidth={stroke} fill="none" />
      {data.map((d, i) => {
        const frac = d.value / total;
        const seg = (
          <Circle key={i} cx={size / 2} cy={size / 2} r={r} stroke={d.color} strokeWidth={stroke} fill="none"
            strokeDasharray={`${circ * frac} ${circ * (1 - frac)}`} strokeDashoffset={-circ * acc}
            transform={`rotate(-90 ${size / 2} ${size / 2})`} strokeLinecap="butt" />
        );
        acc += frac;
        return seg;
      })}
    </Svg>
  );
};

export const Spark: React.FC<{ points: number[]; w?: number; h?: number; color?: string }> = ({ points, w = 80, h = 28, color = C.blue }) => {
  if (!points.length) return null;
  const max = Math.max(...points, 1), min = Math.min(...points, 0);
  const span = max - min || 1;
  const pts = points.map((p, i) => `${(i / (points.length - 1)) * w},${h - ((p - min) / span) * h}`).join(" ");
  return (
    <Svg width={w} height={h}>
      <Polyline points={pts} fill="none" stroke={color} strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" />
    </Svg>
  );
};

export const Section: React.FC<{ title: string; right?: React.ReactNode; children: React.ReactNode }> = ({ title, right, children }) => (
  <View style={{ paddingHorizontal: 16, marginTop: 18 }}>
    <View style={{ flexDirection: "row", alignItems: "center", justifyContent: "space-between", marginBottom: 10 }}>
      <Text style={{ fontSize: 15, fontWeight: "800", color: C.ink }}>{title}</Text>
      {right}
    </View>
    {children}
  </View>
);

export const Loading: React.FC<{ text?: string }> = ({ text }) => (
  <View style={{ paddingVertical: 40, alignItems: "center" }}>
    <ActivityIndicator color={C.blue} />
    {!!text && <Text style={{ color: C.ink3, marginTop: 8, fontSize: 12.5 }}>{text}</Text>}
  </View>
);

export const ErrorBox: React.FC<{ msg: string; onRetry?: () => void }> = ({ msg, onRetry }) => (
  <Card style={{ marginHorizontal: 16, borderLeftWidth: 3, borderLeftColor: C.danger }}>
    <Text style={{ color: C.danger, fontWeight: "700", fontSize: 13 }}>⚠ {msg}</Text>
    {!!onRetry && <TouchableOpacity onPress={onRetry} style={{ marginTop: 8 }}><Text style={{ color: C.blue, fontWeight: "700" }}>重試</Text></TouchableOpacity>}
  </Card>
);

export { C, R, SP };
