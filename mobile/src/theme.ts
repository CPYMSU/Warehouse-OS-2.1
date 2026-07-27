// 設計 token — 數值照搬 web frontend/styles.css,保證與網頁視覺一致
export const C = {
  bg: "#EAEFF6",
  bg2: "#F2F5FA",
  surface: "#FFFFFF",
  surface2: "#F7F9FC",
  line: "#E1E8F1",
  lineSoft: "#EDF1F7",
  ink: "#0E1A2B",
  ink2: "#3C4A5E",
  ink3: "#6B7A90",
  ink4: "#98A4B5",
  blue: "#1B6BFF",
  blueDeep: "#0B4ED6",
  blueSoft: "#E7F0FF",
  teal: "#07B6A2",
  tealSoft: "#DDF6F2",
  ok: "#10B981",
  okSoft: "#DCFCE7",
  warn: "#F59E0B",
  warnSoft: "#FEF3C7",
  danger: "#EF4444",
  dangerSoft: "#FEE2E2",
  yellow: "#EAB308",
  purple: "#8B5CF6",
  white: "#FFFFFF",
};

export const R = { xs: 8, sm: 12, md: 16, lg: 22, xl: 28, pill: 999 };
export const SP = { xs: 4, sm: 8, md: 12, lg: 16, xl: 24 };

export const shadow = {
  sm: {
    shadowColor: "#0E1A2B",
    shadowOpacity: 0.06,
    shadowRadius: 10,
    shadowOffset: { width: 0, height: 4 },
    elevation: 2,
  },
  md: {
    shadowColor: "#0E1A2B",
    shadowOpacity: 0.1,
    shadowRadius: 20,
    shadowOffset: { width: 0, height: 8 },
    elevation: 4,
  },
};

// 容量/狀態著色(與 GIS/總覽一致)
export const capColor = (pct: number) =>
  pct >= 90 ? C.danger : pct >= 70 ? C.warn : C.blue;

export const levelColor: Record<string, string> = {
  red: C.danger,
  orange: C.warn,
  yellow: C.yellow,
  blue: C.blue,
};
