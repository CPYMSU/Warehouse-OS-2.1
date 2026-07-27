/* ============================================================
   ERP 中樞：AI 優先 · Apple-inspired operation surface
   ============================================================ */
const { useEffect: useEffectErp, useMemo: useMemoErp, useRef: useRefErp, useState: useStateErp } = React;

const ERP_API_BASE = typeof window.WAREHOUSE_API_BASE === "string" ? window.WAREHOUSE_API_BASE : "http://127.0.0.1:8090";
const erpJson = async (path, options) => {
  const res = await (window.authFetch || fetch)(ERP_API_BASE + path, options);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || res.statusText || "ERP 請求失敗");
  return data;
};
const postErp = (path, body) => erpJson(path, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body),
});
const erpMoney = (value, currency = "CNY") => {
  const n = Number(value || 0);
  const prefix = currency === "CNY" ? "¥" : `${currency || ""} `;
  return `${prefix}${Number.isFinite(n) ? n.toLocaleString("zh-CN", { maximumFractionDigits: 2 }) : "0"}`;
};
const erpCount = (value) => {
  const n = Number(value || 0);
  return Number.isFinite(n) ? n : 0;
};
const erpStatus = {
  draft: { text: "草稿", cls: "badge-gray" },
  planned: { text: "計劃", cls: "badge-gray" },
  active: { text: "進行中", cls: "badge-info" },
  paused: { text: "暫停", cls: "badge-warn" },
  completed: { text: "完成", cls: "badge-ok" },
  frozen: { text: "凍結", cls: "badge-warn" },
  closed: { text: "關閉", cls: "badge-gray" },
  reserved: { text: "已佔用", cls: "badge-info" },
  approved: { text: "已批准", cls: "badge-ok" },
  submitted: { text: "已提交", cls: "badge-info" },
  ordered: { text: "已下單", cls: "badge-warn" },
  received: { text: "已到貨", cls: "badge-ok" },
  spent: { text: "已支出", cls: "badge-danger" },
  released: { text: "已釋放", cls: "badge-gray" },
  cancelled: { text: "已取消", cls: "badge-gray" },
  confirmed: { text: "已確認", cls: "badge-ok" },
  posted: { text: "已過賬", cls: "badge-ok" },
  pending: { text: "待處理", cls: "badge-warn" },
  pending_closure: { text: "待閉環", cls: "badge-warn" },
  auto_closed: { text: "AI 閉環", cls: "badge-ok" },
  exception: { text: "異常", cls: "badge-danger" },
};
const ErpBadge = ({ value }) => {
  const item = erpStatus[value] || { text: value || "—", cls: "badge-gray" };
  return <span className={`badge ${item.cls}`} style={{ height: 22 }}>{item.text}</span>;
};

const ERP_APPLE = {
  ink: "#1D1D1F",
  sub: "#6E6E73",
  hair: "rgba(29,29,31,0.12)",
  blue: "#0071E3",
  green: "#34C759",
  orange: "#FF9F0A",
  red: "#FF3B30",
  bg: "#F5F5F7",
};

const ErpCanvas = () => {
  const ref = useRefErp(null);
  useEffectErp(() => {
    const canvas = ref.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    let raf = 0;
    let width = 0;
    let height = 0;
    const resize = () => {
      const rect = canvas.getBoundingClientRect();
      const dpr = window.devicePixelRatio || 1;
      width = Math.max(1, Math.floor(rect.width));
      height = Math.max(1, Math.floor(rect.height));
      canvas.width = Math.floor(width * dpr);
      canvas.height = Math.floor(height * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    };
    const draw = (t) => {
      ctx.clearRect(0, 0, width, height);
      ctx.fillStyle = "#fbfbfd";
      ctx.fillRect(0, 0, width, height);
      ctx.lineWidth = 1;
      for (let i = 0; i < 9; i += 1) {
        const y = 26 + i * 36;
        const xShift = (t * 0.012 + i * 28) % Math.max(width, 1);
        ctx.strokeStyle = i % 3 === 0 ? "rgba(0,113,227,0.18)" : "rgba(29,29,31,0.08)";
        ctx.beginPath();
        ctx.moveTo(-40, y);
        ctx.bezierCurveTo(width * 0.28, y - 42, width * 0.58, y + 46, width + 40, y + 6);
        ctx.stroke();
        ctx.fillStyle = i % 3 === 0 ? "rgba(0,113,227,0.24)" : "rgba(52,199,89,0.18)";
        ctx.beginPath();
        ctx.arc(xShift, y + Math.sin((t / 900) + i) * 10, 2.2, 0, Math.PI * 2);
        ctx.fill();
      }
      ctx.strokeStyle = "rgba(29,29,31,0.05)";
      for (let x = 0; x < width; x += 54) {
        ctx.beginPath();
        ctx.moveTo(x, 0);
        ctx.lineTo(x + 34, height);
        ctx.stroke();
      }
      raf = requestAnimationFrame(draw);
    };
    resize();
    window.addEventListener("resize", resize);
    raf = requestAnimationFrame(draw);
    return () => {
      window.removeEventListener("resize", resize);
      cancelAnimationFrame(raf);
    };
  }, []);
  return <canvas ref={ref} style={{ position: "absolute", inset: 0, width: "100%", height: "100%", opacity: 1 }}/>;
};

const AppleButton = ({ children, onClick, primary, disabled, icon }) => (
  <button
    onClick={onClick}
    disabled={disabled}
    className="row gap-8"
    style={{
      minHeight: 38,
      padding: "0 14px",
      borderRadius: 999,
      border: primary ? "none" : `1px solid ${ERP_APPLE.hair}`,
      background: primary ? ERP_APPLE.blue : "#fff",
      color: primary ? "#fff" : ERP_APPLE.ink,
      fontSize: 13,
      fontWeight: 750,
      boxShadow: primary ? "0 10px 24px rgba(0,113,227,0.22)" : "0 1px 2px rgba(0,0,0,0.04)",
      opacity: disabled ? 0.55 : 1,
      whiteSpace: "nowrap",
    }}
  >
    {icon && <Icon name={icon} size={15}/>}
    {children}
  </button>
);

const MiniMetric = ({ label, value, tone = ERP_APPLE.ink, sub }) => (
  <div style={{ minWidth: 0 }}>
    <div className="muted" style={{ fontSize: 11.5, color: ERP_APPLE.sub, marginBottom: 4 }}>{label}</div>
    <div className="num" style={{ fontSize: 22, fontWeight: 850, color: tone, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{value}</div>
    {sub && <div className="muted" style={{ fontSize: 11.5, marginTop: 2 }}>{sub}</div>}
  </div>
);

const WorkflowChip = ({ icon, label, value, tone, onClick }) => (
  <button type="button" onClick={onClick} className="row gap-10" style={{
    width: "100%",
    minHeight: 58,
    padding: "10px 12px",
    border: `1px solid ${ERP_APPLE.hair}`,
    borderRadius: 8,
    background: "#fff",
    textAlign: "left",
    cursor: onClick ? "pointer" : "default",
    font: "inherit",
    color: "inherit",
  }}>
    <div style={{ width: 34, height: 34, borderRadius: 8, display: "grid", placeItems: "center", background: "#F5F5F7", color: tone }}>
      <Icon name={icon} size={17}/>
    </div>
    <div style={{ minWidth: 0 }}>
      <div style={{ fontSize: 12, color: ERP_APPLE.sub }}>{label}</div>
      <div className="num" style={{ fontSize: 17, fontWeight: 850, color: ERP_APPLE.ink }}>{value}</div>
    </div>
  </button>
);

const ERP_MONEY_FIELDS = new Set(["amount", "budget_estimate", "estimated_price", "total_amount", "quantity"]);

const DraftPanel = ({ draft, busy, onConfirm, onDelegate, onClear }) => {
  // 缺失字段就地補選/補填:key → 用戶選/填的值
  const [fixes, setFixes] = useStateErp({});
  useEffectErp(() => { setFixes({}); }, [draft]);
  if (!draft) {
    return (
      <div style={{ padding: 14, borderRadius: 8, background: "#F5F5F7", border: `1px solid ${ERP_APPLE.hair}` }}>
        <div style={{ fontSize: 13, fontWeight: 850, color: ERP_APPLE.ink }}>AI 草稿待生成</div>
        <div style={{ fontSize: 12, color: ERP_APPLE.sub, lineHeight: 1.55, marginTop: 6 }}>自然語言會被轉成 ERP 動作草稿，確認後才寫入系統。</div>
      </div>
    );
  }
  const missing = draft.missing_fields || [];
  const missingLabels = draft.missing_labels || {};
  const options = draft.options || {};
  const stillMissing = missing.filter((k) => fixes[k] === undefined || fixes[k] === "" || fixes[k] === null);
  // link_inventory_document 的路徑由補選的單據 id 在確認時拼出,這裡不要求 path 已存在
  const canExecute = (!!draft.action?.path || draft.intent === "link_inventory_document") && !stillMissing.length;
  const confirm = () => {
    const extra = {};
    missing.forEach((k) => {
      const v = fixes[k];
      if (v === undefined || v === "" || v === null) return;
      extra[k] = (options[k] || ERP_MONEY_FIELDS.has(k)) ? Number(v) : v;
    });
    onConfirm(extra);
  };
  return (
    <div style={{ padding: 14, borderRadius: 8, background: "#fff", border: `1px solid ${stillMissing.length ? "rgba(255,159,10,0.4)" : "rgba(0,113,227,0.28)"}` }} className="col gap-12">
      <div className="row spread" style={{ gap: 12, alignItems: "flex-start" }}>
        <div className="col gap-4" style={{ minWidth: 0 }}>
          <div className="row gap-8" style={{ flexWrap: "wrap" }}>
            <span style={{ fontSize: 14, fontWeight: 900, color: ERP_APPLE.ink }}>{draft.title || "ERP 草稿"}</span>
            <span className="badge badge-info" style={{ height: 22 }}>{Math.round(Number(draft.confidence || 0) * 100)}%</span>
          </div>
          <div style={{ fontSize: 12.5, color: ERP_APPLE.sub, lineHeight: 1.55 }}>{draft.summary}</div>
        </div>
        <button className="btn btn-ghost btn-sm" onClick={onClear} style={{ width: 30, padding: 0 }}><Icon name="x" size={14}/></button>
      </div>
      {!!draft.fields?.length && (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(118px, 1fr))", gap: 8 }}>
          {draft.fields.slice(0, 8).map((f, idx) => (
            <div key={idx} style={{ padding: 10, borderRadius: 8, background: "#F5F5F7" }}>
              <div style={{ fontSize: 11, color: ERP_APPLE.sub, marginBottom: 4 }}>{f.label}</div>
              <div style={{ fontSize: 12.5, fontWeight: 800, color: ERP_APPLE.ink, wordBreak: "break-word" }}>{String(f.value ?? "—")}</div>
            </div>
          ))}
        </div>
      )}
      {!!missing.length && (
        <div className="col gap-8" style={{ padding: 10, borderRadius: 8, background: "rgba(255,159,10,0.12)" }}>
          <div style={{ color: "#8A4B00", fontSize: 12.5, fontWeight: 750 }}>
            待補充：{missing.map((k) => missingLabels[k] || k).join("、")}（補齊後即可執行）
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))", gap: 8 }}>
            {missing.map((k) => (
              <label key={k} className="col gap-4" style={{ fontSize: 11.5, fontWeight: 700, color: "#8A4B00" }}>
                {missingLabels[k] || k}
                {options[k]?.length ? (
                  <select className="input" style={{ height: 34, fontSize: 12.5, background: "#fff" }}
                    value={fixes[k] ?? ""} onChange={(e) => setFixes({ ...fixes, [k]: e.target.value })}>
                    <option value="">請選擇…</option>
                    {options[k].map((o) => <option key={o.id} value={o.id}>{o.label}</option>)}
                  </select>
                ) : (
                  <input className="input" style={{ height: 34, fontSize: 12.5, background: "#fff" }}
                    type={ERP_MONEY_FIELDS.has(k) ? "number" : "text"}
                    placeholder={ERP_MONEY_FIELDS.has(k) ? "輸入數字" : "輸入內容"}
                    value={fixes[k] ?? ""} onChange={(e) => setFixes({ ...fixes, [k]: e.target.value })}/>
                )}
              </label>
            ))}
          </div>
        </div>
      )}
      {!!draft.warnings?.length && (
        <div className="col gap-4">
          {draft.warnings.slice(0, 3).map((w, i) => <div key={i} className="muted" style={{ fontSize: 12, lineHeight: 1.45 }}>· {w}</div>)}
        </div>
      )}
      <div className="row gap-8" style={{ justifyContent: "flex-end", flexWrap: "wrap" }}>
        <AppleButton onClick={onDelegate} icon="sparkle">問秘書解釋</AppleButton>
        <AppleButton primary onClick={confirm} disabled={busy || !canExecute} icon="check">
          {busy ? "執行中" : stillMissing.length ? `先補充 ${stillMissing.length} 項` : "確認執行"}
        </AppleButton>
      </div>
    </div>
  );
};

const StreamRow = ({ icon, title, sub, right, tone = ERP_APPLE.blue, actions, onClick }) => (
  <div
    role={onClick ? "button" : undefined}
    tabIndex={onClick ? 0 : undefined}
    onClick={onClick}
    onKeyDown={(e) => {
      if (!onClick) return;
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        onClick();
      }
    }}
    style={{
    display: "grid",
    gridTemplateColumns: "34px minmax(0, 1fr) auto",
    gap: 11,
    alignItems: "start",
    padding: "12px 0",
    borderTop: `1px solid ${ERP_APPLE.hair}`,
    cursor: onClick ? "pointer" : "default",
  }}>
    <div style={{ width: 34, height: 34, borderRadius: 8, display: "grid", placeItems: "center", background: "#F5F5F7", color: tone }}>
      <Icon name={icon} size={16}/>
    </div>
    <div style={{ minWidth: 0 }}>
      <div style={{ fontSize: 13.5, fontWeight: 850, color: ERP_APPLE.ink, overflowWrap: "anywhere" }}>{title}</div>
      {sub && <div style={{ fontSize: 12, lineHeight: 1.5, color: ERP_APPLE.sub, marginTop: 3, overflowWrap: "anywhere" }}>{sub}</div>}
      {actions && actions.length > 0 && <div className="row gap-6" style={{ flexWrap: "wrap", marginTop: 8 }}>{actions}</div>}
    </div>
    <div style={{ justifySelf: "end", textAlign: "right" }}>{right}</div>
  </div>
);

const erpBudgetUsage = (budget) => {
  const amount = Number(budget?.amount || 0);
  if (!amount) return 0;
  return Math.min(100, Math.round(((Number(budget?.reserved || 0) + Number(budget?.spent || 0)) / amount) * 100));
};
const erpBudgetArchiveState = (budget) => {
  const ai = budget?.ai_status || "";
  if (budget?.status === "closed" || ai === "auto_closed" || ai === "closed") return "archived";
  if (ai === "pending_closure" || ai === "exception") return "review";
  return "active";
};

const BudgetCenterGroup = ({ group, open, onToggle, onOpenBudget }) => {
  const used = erpBudgetUsage(group);
  const tone = group.exception_count ? ERP_APPLE.red : group.pending_count ? ERP_APPLE.orange : used > 90 ? ERP_APPLE.red : used > 70 ? ERP_APPLE.orange : ERP_APPLE.blue;
  const accountPreview = group.accounts.slice(0, 3).join("、");
  const extraAccounts = Math.max(0, group.accounts.length - 3);
  const aiHint = group.exception_count ? ` · 異常 ${group.exception_count}` : group.pending_count ? ` · 待閉環 ${group.pending_count}` : "";
  return (
    <div style={{ borderTop: `1px solid ${ERP_APPLE.hair}`, padding: "10px 0" }}>
      <button type="button" onClick={onToggle}
        style={{
          width: "100%",
          display: "grid",
          gridTemplateColumns: "34px minmax(0, 1fr) auto",
          gap: 11,
          alignItems: "start",
          border: "none",
          background: "transparent",
          padding: "2px 0",
          textAlign: "left",
          color: "inherit",
          cursor: "pointer",
          font: "inherit",
        }}>
        <div style={{ width: 34, height: 34, borderRadius: 8, display: "grid", placeItems: "center", background: "#F5F5F7", color: tone }}>
          <Icon name="layers" size={16}/>
        </div>
        <div style={{ minWidth: 0 }}>
          <div style={{ fontSize: 13.5, fontWeight: 900, color: ERP_APPLE.ink, overflowWrap: "anywhere" }}>{group.center_name}</div>
          <div style={{ fontSize: 12, lineHeight: 1.5, color: ERP_APPLE.sub, marginTop: 3, overflowWrap: "anywhere" }}>
            {group.children.length} 條預算 · 可用 {erpMoney(group.available, group.currency)} · 使用率 {used}%{aiHint}
            {accountPreview ? ` · ${accountPreview}${extraAccounts ? ` 等 ${group.accounts.length} 類` : ""}` : ""}
          </div>
        </div>
        <div className="row gap-8" style={{ justifySelf: "end", alignItems: "center" }}>
          <span className="num" style={{ color: tone, fontSize: 13, fontWeight: 900 }}>{erpMoney(group.amount, group.currency)}</span>
          <Icon name={open ? "chevronDown" : "chevron"} size={13} color={ERP_APPLE.sub}/>
        </div>
      </button>
      {open && (
        <div style={{ marginLeft: 45, marginTop: 8, borderLeft: `2px solid ${ERP_APPLE.hair}`, paddingLeft: 10 }}>
          {group.children.map((b) => {
            const childUsed = erpBudgetUsage(b);
            return (
              <StreamRow
                key={b.id}
                icon="chart"
                title={b.account_name || b.budget_no || "預算"}
                sub={`${b.budget_no} · ${b.period_name || "當前期間"} · 可用 ${erpMoney(b.available, b.currency)} · 使用率 ${childUsed}%${b.ai_status_reason ? ` · ${b.ai_status_reason}` : ""}`}
                tone={b.ai_status === "exception" ? ERP_APPLE.red : b.ai_status === "pending_closure" ? ERP_APPLE.orange : childUsed > 90 ? ERP_APPLE.red : childUsed > 70 ? ERP_APPLE.orange : ERP_APPLE.blue}
                right={<ErpBadge value={b.ai_status || b.status}/>}
                onClick={() => onOpenBudget(b.id)}
              />
            );
          })}
        </div>
      )}
    </div>
  );
};

const ArchiveBlock = ({ title, count, children }) => {
  if (!count) return null;
  return (
    <details style={{ marginTop: 10, paddingTop: 10, borderTop: `1px solid ${ERP_APPLE.hair}` }}>
      <summary style={{ cursor: "pointer", color: ERP_APPLE.sub, fontSize: 12.5, fontWeight: 850, listStyle: "none" }}>
        {title} · {count}
      </summary>
      <div style={{ marginTop: 6 }}>{children}</div>
    </details>
  );
};

const erpQtyText = (value) => {
  const n = Number(value || 0);
  if (!Number.isFinite(n)) return value || "0";
  return Number.isInteger(n) ? String(n) : n.toLocaleString("zh-CN", { maximumFractionDigits: 2 });
};

const purchaseLinePreview = (purchase) => {
  const lines = purchase?.lines || [];
  if (!lines.length) return "未填明細";
  const preview = lines.slice(0, 2).map((line) => {
    const qty = erpQtyText(line.quantity || 0);
    return `${line.item_name || "未命名物資"} x${qty}${line.unit || ""}`;
  }).join("、");
  return lines.length > 2 ? `${preview} 等 ${lines.length} 項` : preview;
};

const erpStatusKey = (value) => String(value || "").trim().toLowerCase();
const erpStatusIn = (statuses, value) => statuses.has(erpStatusKey(value)) || statuses.has(String(value || "").trim());
const ERP_ARCHIVED_PURCHASE_STATUSES = new Set(["received", "cancelled", "completed", "closed"]);
const ERP_ARCHIVED_RESERVATION_STATUSES = new Set(["spent", "released", "cancelled", "closed"]);
const ERP_ARCHIVED_INVENTORY_STATUSES = new Set(["confirmed", "posted", "closed", "cancelled", "completed", "done", "已完成"]);
const ERP_ARCHIVED_STOCKTAKE_STATUSES = new Set(["completed", "closed", "cancelled", "done", "已完成"]);
const ERP_PURCHASE_NEXT = {
  draft: ["submitted", "cancelled"],
  submitted: ["cancelled"],
};
const ERP_PURCHASE_ACTION_LABEL = {
  submitted: "提交",
  cancelled: "取消",
};
const ERP_PURCHASE_DIRECT_STATUSES = new Set(["submitted", "cancelled"]);
const ERP_RESERVATION_NEXT = {
  reserved: ["approved", "released", "cancelled"],
  approved: ["spent", "released", "cancelled"],
};
const ERP_RESERVATION_ACTION_LABEL = {
  approved: "批准",
  spent: "記為支出",
  released: "釋放",
  cancelled: "取消",
};
const isErpPurchaseArchived = (purchase) => erpStatusIn(ERP_ARCHIVED_PURCHASE_STATUSES, purchase?.status || "draft");
const isErpPurchaseOpen = (purchase) => !isErpPurchaseArchived(purchase);
const erpPurchaseNextStatuses = (purchase) => ERP_PURCHASE_NEXT[erpStatusKey(purchase?.status || "draft")] || [];
const erpPurchaseDirectStatuses = (purchase) => erpAllowedStatuses(purchase, erpPurchaseNextStatuses(purchase))
  .filter((status) => ERP_PURCHASE_DIRECT_STATUSES.has(status));
const isErpReservationArchived = (reservation) => erpStatusIn(ERP_ARCHIVED_RESERVATION_STATUSES, reservation?.status || "reserved");
const erpReservationNextStatuses = (reservation) => ERP_RESERVATION_NEXT[erpStatusKey(reservation?.status || "reserved")] || [];
const isBudgetUnlinkedOpen = (doc) => doc?.budget_unlinked_open === true || (doc?.budget_unlinked_open == null && !erpStatusIn(ERP_ARCHIVED_INVENTORY_STATUSES, doc?.status || "draft") && !doc?.confirmed_at && !doc?.cancelled_at && doc?.needs_budget && !doc?.budget_reservation_id);
const erpAllowedStatuses = (row, fallback = []) => {
  if (Array.isArray(row?.allowed_actions)) return row.allowed_actions.map((a) => a?.status).filter(Boolean);
  return fallback;
};
const erpAllowedLabel = (row, status, labels = {}) => {
  const action = Array.isArray(row?.allowed_actions) ? row.allowed_actions.find((a) => a?.status === status) : null;
  return action?.label || labels[status] || erpStatus[status]?.text || status;
};
const isErpInventoryDocumentOpen = (doc) => {
  return !erpStatusIn(ERP_ARCHIVED_INVENTORY_STATUSES, doc?.status || "draft") && !doc?.confirmed_at && !doc?.cancelled_at;
};
const isErpStocktakeOpen = (task) => !erpStatusIn(ERP_ARCHIVED_STOCKTAKE_STATUSES, task?.status || "");

// ============================================================
// SAP Fiori Object Page — ERP 對象詳情頁(對象頭 + 錨點分區導航 + DataTable)
// 信息架構照搬 Fiori 工業標準,視覺沿用現有 Apple 配色底子。
// ============================================================

// Fiori/Carbon 風格數據表:緊湊行高、表頭分隔線、數字右對齊、行 hover
const ErpDataTable = ({ columns, rows, empty }) => {
  if (!rows || !rows.length) return <div className="muted" style={{ padding: "22px 0", fontSize: 13, textAlign: "center" }}>{empty || "暫無數據"}</div>;
  return (
    <div style={{ overflowX: "auto", border: `1px solid ${ERP_APPLE.hair}`, borderRadius: 8 }}>
      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
        <thead>
          <tr style={{ background: "#FAFAFB" }}>
            {columns.map((c) => (
              <th key={c.key} style={{ textAlign: c.align || "left", padding: "9px 13px", borderBottom: `1px solid ${ERP_APPLE.hair}`, color: ERP_APPLE.sub, fontWeight: 800, fontSize: 11, letterSpacing: ".04em", whiteSpace: "nowrap" }}>{c.label}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={i} style={{ borderBottom: i < rows.length - 1 ? `1px solid ${ERP_APPLE.hair}` : "none" }}
              onMouseEnter={(e) => { e.currentTarget.style.background = "#FAFAFB"; }}
              onMouseLeave={(e) => { e.currentTarget.style.background = "transparent"; }}>
              {columns.map((c) => (
                <td key={c.key} style={{ padding: "9px 13px", textAlign: c.align || "left", color: ERP_APPLE.ink, verticalAlign: "middle", whiteSpace: c.wrap ? "normal" : "nowrap" }}>
                  {c.render ? c.render(r) : (r[c.key] == null || r[c.key] === "" ? "—" : r[c.key])}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

// 字段網格(對象基本信息分區用)
const ErpFieldGrid = ({ fields }) => (
  <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "13px 22px" }}>
    {fields.map((f, i) => (
      <div key={i} className="col gap-3">
        <div style={{ fontSize: 11, color: ERP_APPLE.sub, fontWeight: 700, letterSpacing: ".02em" }}>{f.label}</div>
        <div style={{ fontSize: 13.5, fontWeight: 700, color: ERP_APPLE.ink, overflowWrap: "anywhere" }}>{f.value == null || f.value === "" ? "—" : f.value}</div>
      </div>
    ))}
  </div>
);

const FioriObjectPage = ({ obj, onBack, onAsk }) => {
  const bodyRef = useRefErp(null);
  const [activeAnchor, setActiveAnchor] = useStateErp((obj.sections[0] || {}).id);
  const scrollTo = (id) => {
    setActiveAnchor(id);
    const el = bodyRef.current && bodyRef.current.querySelector(`[data-anchor="${id}"]`);
    if (el) el.scrollIntoView({ behavior: "smooth", block: "start" });
  };
  return (
    <div className="col gap-14" style={{ color: ERP_APPLE.ink }}>
      {/* 對象頭 Object Header */}
      <div style={{ borderRadius: 8, border: `1px solid ${ERP_APPLE.hair}`, background: "#fff", padding: "18px 22px", boxShadow: "0 1px 2px rgba(0,0,0,0.04)" }} className="col gap-14">
        <div className="row spread" style={{ alignItems: "flex-start", gap: 12, flexWrap: "wrap" }}>
          <div className="col gap-6" style={{ minWidth: 240 }}>
            <button onClick={onBack} className="row gap-6" style={{ alignSelf: "flex-start", fontSize: 12.5, fontWeight: 800, color: ERP_APPLE.blue, background: "transparent", padding: "2px 0" }}>
              <Icon name="arrow" size={14} style={{ transform: "scaleX(-1)" }}/>返回 ERP 總覽
            </button>
            <div className="row gap-9" style={{ alignItems: "baseline", flexWrap: "wrap" }}>
              <span style={{ fontSize: 12, fontWeight: 800, color: ERP_APPLE.sub, letterSpacing: ".04em" }}>{obj.kind}</span>
              <span className="num" style={{ fontSize: 23, fontWeight: 900, letterSpacing: "-0.01em" }}>{obj.no}</span>
              {obj.status != null && <ErpBadge value={obj.status}/>}
            </div>
            <div style={{ fontSize: 14, color: ERP_APPLE.sub, fontWeight: 650 }}>{obj.title}</div>
            {obj.subtitle && <div style={{ fontSize: 12.5, color: ERP_APPLE.sub }}>{obj.subtitle}</div>}
          </div>
          <div className="row gap-8" style={{ flexWrap: "wrap", justifyContent: "flex-end" }}>
            {(obj.actions || []).map((a, idx) => (
              <button key={idx} className="btn btn-sm" disabled={a.disabled}
                onClick={a.onClick}
                style={{ height: 32, padding: "0 12px", borderRadius: 8, fontWeight: 750, fontSize: 12.5,
                  background: a.primary ? ERP_APPLE.blue : "#fff", color: a.primary ? "#fff" : ERP_APPLE.ink,
                  border: a.primary ? "none" : `1px solid ${ERP_APPLE.hair}`, opacity: a.disabled ? 0.45 : 1 }}>
                {a.label}
              </button>
            ))}
            <button className="btn btn-sm" onClick={onAsk} style={{ height: 32, padding: "0 12px", borderRadius: 8, fontWeight: 750, fontSize: 12.5, background: "#F5F5F7", border: `1px solid ${ERP_APPLE.hair}`, color: ERP_APPLE.ink }}>
              <Icon name="sparkle" size={13}/>問秘書
            </button>
          </div>
        </div>
        {/* KPI 行 */}
        {!!(obj.kpis || []).length && (
          <div style={{ display: "grid", gridTemplateColumns: `repeat(auto-fit, minmax(120px, 1fr))`, gap: 12, paddingTop: 14, borderTop: `1px solid ${ERP_APPLE.hair}` }}>
            {obj.kpis.map((m, i) => <MiniMetric key={i} label={m.label} value={m.value} tone={m.tone || ERP_APPLE.ink}/>)}
          </div>
        )}
      </div>

      {/* 錨點導航 Anchor Bar(sticky) */}
      <div className="row gap-4" style={{ position: "sticky", top: 0, zIndex: 3, background: "rgba(245,245,247,0.92)", backdropFilter: "blur(8px)", padding: "6px 4px", borderRadius: 8, overflowX: "auto", flexWrap: "nowrap" }}>
        {obj.sections.map((s) => (
          <button key={s.id} onClick={() => scrollTo(s.id)}
            style={{ height: 30, padding: "0 13px", borderRadius: 999, fontSize: 12.5, fontWeight: 800, whiteSpace: "nowrap",
              background: activeAnchor === s.id ? ERP_APPLE.ink : "transparent", color: activeAnchor === s.id ? "#fff" : ERP_APPLE.sub, border: "none" }}>
            {s.title}{s.count != null ? ` ${s.count}` : ""}
          </button>
        ))}
      </div>

      {/* 分區內容 Sections */}
      <div ref={bodyRef} className="col gap-14">
        {obj.sections.map((s) => (
          <section key={s.id} data-anchor={s.id} style={{ borderRadius: 8, border: `1px solid ${ERP_APPLE.hair}`, background: "#fff", padding: 16, scrollMarginTop: 52 }} className="col gap-10">
            <div className="row spread" style={{ alignItems: "center" }}>
              <div style={{ fontSize: 15, fontWeight: 900 }}>{s.title}{s.count != null ? ` · ${s.count}` : ""}</div>
              {s.hint && <div style={{ fontSize: 12, color: ERP_APPLE.sub }}>{s.hint}</div>}
            </div>
            {s.node}
          </section>
        ))}
      </div>
    </div>
  );
};

// F1 多層級預算:年/季/月期間樹展示
const PERIOD_TYPE_LABEL = { year: "年度", quarter: "季度", month: "月度" };
// F2 計劃綁定:預算佔用的來源類型(這筆佔用屬於哪個計劃/工單/採購)
const RSV_SOURCE_LABEL = { manual: "手動", collab_idea: "共創計劃", work_task: "工單", purchase_request: "採購", inventory_document: "庫存單據", other: "其他" };
// F3 複式記賬:憑證類型 + 賬戶桶的中文
const JOURNAL_TYPE_LABEL = { appropriation: "撥款", transfer: "劃撥", reserve: "佔用", spend: "支出", release: "釋放", correction: "更正" };
const JOURNAL_BUCKET_LABEL = { available: "可用", reserved: "已佔用", spent: "已支出", source: "來源" };
const ErpBudgetLedger = ({ budgetId }) => {
  const [data, setData] = useStateErp(null);
  useEffectErp(() => { erpJson(`/api/erp/budgets/${budgetId}/ledger`).then(setData).catch(() => setData({ lines: [] })); }, [budgetId]);
  if (!data) return <div className="muted" style={{ fontSize: 13, padding: "14px 0" }}>讀取資金流水賬…</div>;
  return <ErpDataTable rows={data.lines || []} empty="暫無分錄(尚無金流)" columns={[
    { key: "entry_no", label: "憑證號" },
    { key: "entry_type", label: "類型", render: (l) => JOURNAL_TYPE_LABEL[l.entry_type] || l.entry_type },
    { key: "bucket", label: "賬戶", render: (l) => JOURNAL_BUCKET_LABEL[l.bucket] || l.bucket },
    { key: "debit", label: "借方", align: "right", render: (l) => Number(l.debit || 0) > 0 ? erpMoney(l.debit) : "—" },
    { key: "credit", label: "貸方", align: "right", render: (l) => Number(l.credit || 0) > 0 ? erpMoney(l.credit) : "—" },
    { key: "summary", label: "摘要/詳情", wrap: true },
    { key: "entry_date", label: "時間", render: (l) => (l.entry_date || "").slice(0, 16) || "—" },
  ]}/>;
};
const ErpPeriodNode = ({ node, depth }) => {
  const [open, setOpen] = useStateErp(depth === 0);
  const kids = node.children || [];
  const hasKids = kids.length > 0;
  return (
    <div>
      <div className="row" style={{ gap: 7, padding: "5px 8px", paddingLeft: 8 + depth * 18, borderRadius: 7, cursor: hasKids ? "pointer" : "default" }}
        onClick={() => hasKids && setOpen((o) => !o)}
        onMouseEnter={(e) => { e.currentTarget.style.background = "#F5F5F7"; }}
        onMouseLeave={(e) => { e.currentTarget.style.background = "transparent"; }}>
        {hasKids ? <Icon name={open ? "chevronDown" : "chevron"} size={12} color={ERP_APPLE.sub}/> : <span style={{ width: 12, flexShrink: 0 }}/>}
        <span style={{ fontSize: 12.5, fontWeight: depth === 0 ? 800 : 600, color: ERP_APPLE.ink, whiteSpace: "nowrap" }}>{node.period_name}</span>
        <span style={{ fontSize: 10, color: ERP_APPLE.sub }}>{PERIOD_TYPE_LABEL[node.period_type] || ""}</span>
        <span style={{ flex: 1 }}/>
        {Number(node.budget_count || 0) > 0
          ? <span className="num" style={{ fontSize: 12, fontWeight: 700, color: ERP_APPLE.blue }}>{erpMoney(node.budget_total)}</span>
          : <span style={{ fontSize: 11, color: ERP_APPLE.sub }}>未設</span>}
      </div>
      {open && kids.map((k) => <ErpPeriodNode key={k.id} node={k} depth={depth + 1}/>)}
    </div>
  );
};
const ErpPeriodTree = () => {
  const [tree, setTree] = useStateErp(null);
  useEffectErp(() => { erpJson("/api/erp/periods").then((d) => setTree(d.tree || [])).catch(() => setTree([])); }, []);
  if (!tree) return null;
  return (
    <div style={{ borderRadius: 8, border: `1px solid ${ERP_APPLE.hair}`, background: "#fff", padding: 16 }} className="col gap-4">
      <div style={{ fontSize: 16, fontWeight: 900 }}>預算期間</div>
      <div style={{ fontSize: 12, color: ERP_APPLE.sub, marginBottom: 6 }}>年度 → 季度 → 月度。預算可掛任意層級,下級之和受上級約束(超出會提示)。</div>
      {tree.length === 0 && <div className="muted" style={{ fontSize: 13, padding: "12px 0" }}>暫無期間</div>}
      {tree.map((n) => <ErpPeriodNode key={n.id} node={n} depth={0}/>)}
    </div>
  );
};

const PageERP = () => {
  const [data, setData] = useStateErp(null);
  const [state, setState] = useStateErp("loading");
  const [busy, setBusy] = useStateErp("");
  const [error, setError] = useStateErp("");
  const [notice, setNotice] = useStateErp("");
  const [aiText, setAiText] = useStateErp("");
  const [draft, setDraft] = useStateErp(null);
  const [activeObj, setActiveObj] = useStateErp(null); // {type:"budget"|"task"|"purchase", id}
  const [editReq, setEditReq] = useStateErp(null); // 協作改單浮層 {docId, docNo, reason, summary, source_unit, handler}
  const [expandedBudgetCenters, setExpandedBudgetCenters] = useStateErp({});

  const load = () => {
    setState((s) => s === "ok" ? "ok" : "loading");
    setError("");
    return erpJson("/api/erp/overview")
      .then((d) => { setData(d); setState("ok"); })
      .catch((e) => { setError(e.message || String(e)); setState("error"); });
  };
  useEffectErp(() => { load(); }, []);

  const summary = data?.summary || {};
  const costCenters = data?.cost_centers || [];
  const budgets = data?.budgets || [];
  const budgetMovements = data?.budget_movements || [];
  const reservations = data?.reservations || [];
  const workTasks = data?.work_tasks || [];
  const suppliers = data?.suppliers || [];
  const purchaseRequests = data?.purchase_requests || [];
  const inventoryDocuments = data?.inventory_documents || [];
  const openAlerts = data?.open_alerts || [];
  const stocktakeTasks = data?.stocktake_tasks || [];

  const usage = Number(summary.budget_amount || 0)
    ? Math.min(100, Math.round(((Number(summary.budget_reserved || 0) + Number(summary.budget_spent || 0)) / Number(summary.budget_amount || 1)) * 100))
    : 0;
  const openWorkTasks = workTasks.filter((t) => (t.status || "planned") !== "completed" && (t.status || "planned") !== "cancelled");
  const openPurchases = purchaseRequests.filter(isErpPurchaseOpen);
  const archivedPurchases = purchaseRequests.filter(isErpPurchaseArchived);
  const visiblePurchases = openPurchases.slice(0, 12);
  const hiddenPurchaseCount = Math.max(0, openPurchases.length - visiblePurchases.length);
  const activeReservations = reservations.filter((r) => !isErpReservationArchived(r));
  const archivedReservations = reservations.filter(isErpReservationArchived);
  const archivedInventoryDocuments = inventoryDocuments.filter((d) => !isErpInventoryDocumentOpen(d));
  const openStocktakeTasks = stocktakeTasks.filter(isErpStocktakeOpen);
  const archivedStocktakeTasks = stocktakeTasks.filter((t) => !isErpStocktakeOpen(t));
  // 只有採購類消費單據(needs_budget,後端判定)未掛預算才算「未掛預算」;調撥/搬移等內部流轉不算
  const unlinkedDocs = inventoryDocuments.filter(isBudgetUnlinkedOpen);
  const activeClosureCount = activeReservations.length + unlinkedDocs.length + openStocktakeTasks.length;
  const archivedClosureCount = budgetMovements.length + archivedReservations.length + archivedInventoryDocuments.length + archivedStocktakeTasks.length;
  const openAlertCount = Math.max(openAlerts.length, erpCount(summary.open_alerts));
  const inventoryUnlinkedCount = unlinkedDocs.length;
  const budgetReviewCount = budgets.filter((b) => erpBudgetArchiveState(b) === "review").length;
  const budgetExceptionCount = budgets.filter((b) => b.ai_status === "exception").length;
  const purchaseOpenCount = openPurchases.length;
  const pendingSignalCount = openAlertCount + inventoryUnlinkedCount + purchaseOpenCount + budgetReviewCount;
  const healthTone = (openAlertCount || budgetExceptionCount) ? ERP_APPLE.red : pendingSignalCount ? ERP_APPLE.orange : ERP_APPLE.green;
  const healthText = (openAlertCount || budgetExceptionCount) ? "需關注" : pendingSignalCount ? "待閉環" : "穩定";
  const urgentQueue = [
    ...openAlerts.slice(0, 3).map((a) => ({ type: "alert", icon: "alert", tone: ERP_APPLE.red, title: a.item_name || a.alert_type, sub: a.suggestion || `${a.alert_type} · ${a.level}`, right: <span className="badge badge-danger">{a.level || "open"}</span> })),
    ...unlinkedDocs.slice(0, 3).map((d) => ({ type: "doc", docId: d.id, docNo: d.document_no, icon: "link", tone: ERP_APPLE.orange, title: d.document_no, sub: `${d.business_type || d.document_type || "庫存單據"} · ${d.summary || "未掛預算"}`, right: <span className="badge badge-warn">未掛預算</span> })),
    ...openPurchases.slice(0, 2).map((p) => ({ type: "purchase", icon: "inbound", tone: ERP_APPLE.blue, title: p.title, sub: `${p.request_no} · ${purchaseLinePreview(p)} · ${p.supplier_name || "未指定供應商"}`, right: <ErpBadge value={p.status}/> })),
  ];

  const budgetGroups = useMemoErp(() => {
    const buildGroups = (items) => {
    const map = new Map();
    items.forEach((b, index) => {
      const key = b.cost_center_id ? `cc:${b.cost_center_id}` : `name:${b.center_name || "未綁定成本中心"}`;
      if (!map.has(key)) {
        map.set(key, {
          id: key,
          cost_center_id: b.cost_center_id || null,
          center_name: b.center_name || "未綁定成本中心",
          center_code: b.center_code || "",
          currency: b.currency || "CNY",
          firstIndex: index,
          accounts: [],
          children: [],
        });
      }
      const group = map.get(key);
      group.children.push(b);
      const accountName = b.account_name || b.budget_no || "預算";
      if (!group.accounts.includes(accountName)) group.accounts.push(accountName);
    });
    return Array.from(map.values()).map((group) => {
      const totals = group.children.some((b) => (b.budget_kind || "rolling") !== "center")
        ? group.children.filter((b) => (b.budget_kind || "rolling") !== "center")
        : group.children;
      const sum = (field) => totals.reduce((acc, b) => acc + Number(b[field] || 0), 0);
      return {
        ...group,
        amount: sum("amount"),
        reserved: sum("reserved"),
        spent: sum("spent"),
        available: sum("available"),
        pending_count: group.children.filter((b) => b.ai_status === "pending_closure").length,
        exception_count: group.children.filter((b) => b.ai_status === "exception").length,
        children: group.children.slice().sort((a, b) => {
          const ak = (a.budget_kind || "rolling") === "center" ? 0 : 1;
          const bk = (b.budget_kind || "rolling") === "center" ? 0 : 1;
          return ak - bk;
        }),
      };
    }).sort((a, b) => a.firstIndex - b.firstIndex);
    };
    const grouped = { review: [], active: [], archived: [] };
    budgets.forEach((b) => grouped[erpBudgetArchiveState(b)].push(b));
    return {
      review: buildGroups(grouped.review),
      active: buildGroups(grouped.active),
      archived: buildGroups(grouped.archived),
      all: buildGroups(budgets),
      archivedCount: grouped.archived.length,
      reviewCount: grouped.review.length,
      activeCount: grouped.active.length,
    };
  }, [budgets]);

  const planWithAI = (nextText = aiText) => {
    const text = (nextText || "").trim();
    if (!text || busy) return;
    setBusy("ai-plan");
    setError("");
    setNotice("");
    postErp("/api/erp/assistant/plan", { text })
      .then((result) => {
        if (result.overview) setData(result.overview);
        setDraft(result.plan);
        setNotice(result.plan?.executable ? "AI 已生成可確認草稿" : "AI 草稿需要補充信息");
      })
      .catch((e) => setError(e.message || String(e)))
      .finally(() => setBusy(""));
  };

  const confirmDraft = (extra = {}) => {
    if (!draft?.action || busy) return;
    const payload = { ...(draft.action.payload || {}), ...extra };
    // 關聯庫存單據:document_id 是事後補選的,路徑也要跟著補
    let path = draft.action.path;
    if (!path && draft.intent === "link_inventory_document" && payload.document_id) {
      path = `/api/erp/inventory-documents/${payload.document_id}/budget-link`;
    }
    if (!path) return;
    const remaining = (draft.missing_fields || []).filter((k) => payload[k] === undefined || payload[k] === "" || payload[k] === null);
    if (remaining.length) return;
    setBusy("ai-confirm");
    setError("");
    setNotice("");
    postErp(path, payload)
      .then((d) => {
        setData(d);
        setDraft(null);
        setNotice("ERP 動作已執行並寫入審計");
      })
      .catch((e) => setError(e.message || String(e)))
      .finally(() => setBusy(""));
  };

  const askSecretary = (text, autoAsk = true) => {
    const prompt = `ERP 中樞：${text || "請解釋 ERP 中樞當前狀態，並給出下一步建議。"}`;
    if (window.openUnifiedAgent) window.openUnifiedAgent(prompt, { autoAsk });
    else setNotice("公司 AI 秘書尚未載入，請稍後再試");
  };

  // 點擊面板元素 → 就地浮層簡答(秘書 2-4 句),不再自動發固定長話術;想深聊在浮層點「展開對話」
  const explainMetric = (label, value, detail) => {
    if (window.explainInline) {
      window.explainInline({
        label, context: { 模塊: "ERP 中樞", 類型: "指標", 名稱: label, 當前值: value, 說明: detail || "" },
        deepPrompt: `請詳細解釋 ERP「${label}」(當前 ${value})代表什麼、是否有風險、下一步可以怎麼處理。`,
      });
    } else {
      askSecretary(`請解釋「${label}」這個位置。當前值是 ${value}。${detail || ""}`);
    }
  };

  const explainRow = (section, title, sub) => {
    if (window.explainInline) {
      window.explainInline({
        label: title, context: { 模塊: "ERP 中樞", 區塊: section, 標題: title, 信息: sub || "" },
        deepPrompt: `我點擊了 ERP「${section}」中的「${title}」(${sub || ""})。請解釋它的含義、與預算/工單/採購/庫存閉環的關係,以及下一步建議。`,
      });
    } else {
      askSecretary(`我點擊了 ERP「${section}」中的「${title}」。相關信息：${sub || "無"}。`);
    }
  };

  const delegateToAgent = (text = aiText, autoAsk = false) => {
    askSecretary(text || draft?.source_text || draft?.summary || "請協助處理 ERP 待辦", autoAsk);
  };

  // 協作改單:對「有問題的單據」提補充/修改 → AI 秘書按白名單字段審核後即時生效
  const submitEditRequest = () => {
    if (busy) return;
    const fields = {};
    ["summary", "source_unit", "handler"].forEach((k) => { if ((editReq[k] || "").trim()) fields[k] = editReq[k].trim(); });
    if (!editReq.reason?.trim() && Object.keys(fields).length === 0) { setError("請填寫補充說明,或至少修改一個字段"); return; }
    setBusy("editreq");
    setError("");
    postErp("/api/collab/edit-requests", { target_type: "inventory_document", target_id: editReq.docId, reason: editReq.reason || "", changes: { fields } })
      .then((d) => {
        setEditReq(null);
        const msg = d.message || ((d.applied || d.status === "applied") ? "AI 秘書已審核並生效" : "已提交給 AI 秘書審核");
        if (d.status === "failed" || d.status === "rejected") setError(msg);
        else setNotice(msg);
        load();
      })
      .catch((e) => setError(e.message || String(e)))
      .finally(() => setBusy(""));
  };

  const updateReservation = (id, status) => {
    if (busy) return;
    setBusy(`r${id}`);
    setError("");
    postErp(`/api/erp/budget-reservations/${id}/status`, { status })
      .then((d) => { setData(d); setNotice("預算佔用狀態已更新"); })
      .catch((e) => setError(e.message || String(e)))
      .finally(() => setBusy(""));
  };
  const setBudgetKind = (id, kind) => {
    if (busy) return;
    setBusy(`k${id}`);
    setError("");
    postErp(`/api/erp/budgets/${id}/kind`, { budget_kind: kind })
      .then((d) => { setData(d); setNotice(kind === "earmarked" ? "已標為專項預算(花滿即可結項閉環)" : kind === "rolling" ? "已標為雜項/經常性預算" : kind === "center" ? "已標為預算中心(可歸入子預算,按中心彙總監控)" : "已更新預算性質"); })
      .catch((e) => setError(e.message || String(e)))
      .finally(() => setBusy(""));
  };
  const setBudgetParent = (id, parentId) => {
    if (busy) return;
    setBusy(`p${id}`);
    setError("");
    postErp(`/api/erp/budgets/${id}/parent`, { parent_budget_id: parentId })
      .then((d) => { setData(d); setNotice(parentId ? "已歸入預算中心" : "已脫離預算中心"); })
      .catch((e) => setError(e.message || String(e)))
      .finally(() => setBusy(""));
  };
  const closeBudget = (id) => {
    if (busy) return;
    if (typeof window !== "undefined" && window.confirm && !window.confirm("確認結項?結項後該預算不再計入預警(專款已按計劃用滿)。")) return;
    setBusy(`b${id}`);
    setError("");
    postErp(`/api/erp/budgets/${id}/close`, { reason: "專案完成,確認結項" })
      .then((d) => { setData(d); setNotice("預算已結項,閉環完成,不再提示"); setActiveObj(null); })
      .catch((e) => setError(e.message || String(e)))
      .finally(() => setBusy(""));
  };
  const updateWorkTask = (id, status) => {
    if (busy) return;
    setBusy(`w${id}`);
    setError("");
    postErp(`/api/erp/work-tasks/${id}/status`, { status })
      .then((d) => { setData(d); setNotice("工單狀態已更新"); })
      .catch((e) => setError(e.message || String(e)))
      .finally(() => setBusy(""));
  };
  const updatePurchase = (id, status) => {
    if (busy) return;
    if (!ERP_PURCHASE_DIRECT_STATUSES.has(status)) {
      setError("批准與下單只能由採購工作流節點產生；到貨必須從已簽發 PO 建立正式採購收貨單");
      return;
    }
    setBusy(`p${id}`);
    setError("");
    postErp(`/api/erp/purchase-requests/${id}/status`, { status })
      .then((d) => { setData(d); setNotice("採購狀態已更新"); })
      .catch((e) => setError(e.message || String(e)))
      .finally(() => setBusy(""));
  };

  // 推薦詞按本公司實際數據生成:真實單據號、預警物資、成本中心和科目名稱,而非寫死的例句
  const quick = useMemoErp(() => {
    const sug = [];
    const accounts = data?.budget_accounts || [];
    const firstAccount = accounts[0]?.account_name || "";
    // 1) 真實的未掛預算單據
    if (unlinkedDocs.length) {
      sug.push(unlinkedDocs.length > 1
        ? `把 ${unlinkedDocs[0].document_no} 等 ${unlinkedDocs.length} 張未掛預算單據關聯到可用預算`
        : `把單據 ${unlinkedDocs[0].document_no} 關聯到可用預算`);
    }
    // 2) 低庫存預警 → 直接生成補貨採購
    const alertItem = openAlerts.find((a) => a.item_name);
    if (alertItem) {
      const gap = Math.max(0, Number(alertItem.safe_quantity || 0) - Number(alertItem.stock || 0));
      sug.push(`採購 ${alertItem.item_name}${gap ? ` ${gap} 件` : ""}，補足安全庫存，優先級緊急`);
    }
    // 3) 還沒掛預算的成本中心
    const noBudget = costCenters.find((c) => c.active !== 0 && !Number(c.budget_amount || 0));
    if (noBudget) sug.push(`為${noBudget.center_name}建立${firstAccount ? `${firstAccount}` : ""}預算 50000 元`);
    // 4) 用真實成本中心/科目名稱補足泛用例句
    const cc0 = costCenters.find((c) => c.active !== 0) || costCenters[0];
    if (cc0 && firstAccount) sug.push(`為${cc0.center_name}建立${firstAccount}預算 20000 元`);
    if (cc0) sug.push(`新建${cc0.center_name}工單，預算 10000，優先級緊急`);
    if (suppliers[0]?.supplier_name) sug.push(`向${suppliers[0].supplier_name}採購一批物資，預算 8000`);
    sug.push("採購一批辦公用品，預算 5000");
    return [...new Set(sug)].slice(0, 4);
  }, [data]);

  // ——— Fiori Object Page:從 overview 數據按 id 組裝單對象完整檔案 ———
  const rsvOps = (r) => (
    <div className="row gap-4">
      {erpAllowedStatuses(r, erpReservationNextStatuses(r)).map((s) => (
        <button key={s} className="btn btn-sm" disabled={!!busy || r.status === s} onClick={() => updateReservation(r.id, s)} style={{ height: 26, fontSize: 11, padding: "0 7px" }}>{erpAllowedLabel(r, s, ERP_RESERVATION_ACTION_LABEL)}</button>
      ))}
    </div>
  );
  const buildBudgetObject = (b) => {
    const rsv = reservations.filter((r) => r.budget_id === b.id);
    const mov = budgetMovements.filter((m) => m.budget_id === b.id);
    const tasks = workTasks.filter((t) => t.budget_id === b.id);
    const prs = purchaseRequests.filter((p) => p.budget_id === b.id);
    const used = Number(b.amount || 0) ? Math.min(100, Math.round(((Number(b.reserved || 0) + Number(b.spent || 0)) / Number(b.amount || 1)) * 100)) : 0;
    const curKind = b.budget_kind || "rolling";
    const kindLabel = { center: "預算中心", earmarked: "專項預算", rolling: "雜項/經常性" }[curKind];
    const isActive = b.status === "active";
    const isCenter = curKind === "center";
    const children = (budgets || []).filter((x) => x.parent_budget_id === b.id);
    const centers = (budgets || []).filter((x) => x.budget_kind === "center" && x.cost_center_id === b.cost_center_id && x.id !== b.id && x.status === "active");
    const roll = b.rollup || {};
    const budgetActions = [];
    if (isActive && !isCenter) budgetActions.push({ label: "標為預算中心", disabled: !!busy, onClick: () => setBudgetKind(b.id, "center") });
    if (isActive && curKind !== "earmarked" && !isCenter) budgetActions.push({ label: "標為專項", disabled: !!busy, onClick: () => setBudgetKind(b.id, "earmarked") });
    if (isActive && curKind !== "rolling" && !isCenter) budgetActions.push({ label: "標為雜項", disabled: !!busy, onClick: () => setBudgetKind(b.id, "rolling") });
    if (isActive && !isCenter && b.parent_budget_id) budgetActions.push({ label: "脫離中心", disabled: !!busy, onClick: () => setBudgetParent(b.id, null) });
    if (isActive && !isCenter && !b.parent_budget_id) centers.slice(0, 3).forEach((c) => budgetActions.push({ label: `歸入「${c.account_name}」`, disabled: !!busy, onClick: () => setBudgetParent(b.id, c.id) }));
    if (isActive && (curKind === "earmarked" || isCenter)) budgetActions.push({ label: "確認結項", disabled: !!busy || (isCenter && children.some((c) => c.status === "active")), primary: used >= 100, onClick: () => closeBudget(b.id) });
    const aiTone = b.ai_status === "exception" ? ERP_APPLE.red : b.ai_status === "pending_closure" ? ERP_APPLE.orange : b.ai_status === "auto_closed" ? ERP_APPLE.green : ERP_APPLE.blue;
    const aiKpi = { label: "AI 狀態", value: erpStatus[b.ai_status]?.text || (b.status === "closed" ? "已歸檔" : "執行中"), tone: aiTone, sub: b.ai_status_reason || "按 ERP 事實持續校正" };
    const centerKpis = [
      { label: "中心總額", value: erpMoney(b.amount, b.currency) },
      { label: "子預算合計", value: erpMoney(roll.child_amount, b.currency), tone: (roll.child_amount || 0) > Number(b.amount || 0) ? ERP_APPLE.red : ERP_APPLE.ink },
      { label: "子預算已用", value: erpMoney(roll.child_used, b.currency), tone: ERP_APPLE.orange },
      { label: "可下撥", value: erpMoney(Number(b.amount || 0) - Number(roll.child_amount || 0), b.currency), tone: ERP_APPLE.green },
    ];
    const childSection = isCenter ? [{ id: "children", title: "子預算", count: children.length, node: <ErpDataTable rows={children} empty="尚無子預算;在子預算詳情點「歸入本中心」" columns={[
      { key: "budget_no", label: "編號" },
      { key: "account_name", label: "科目/用途", wrap: true },
      { key: "budget_kind", label: "性質", render: (c) => ({ earmarked: "專項", rolling: "雜項", center: "中心" })[c.budget_kind] || c.budget_kind },
      { key: "amount", label: "額度", align: "right", render: (c) => erpMoney(c.amount, c.currency) },
      { key: "used", label: "已用", align: "right", render: (c) => erpMoney(Number(c.reserved || 0) + Number(c.spent || 0), c.currency) },
      { key: "status", label: "狀態", render: (c) => <ErpBadge value={c.status}/> },
    ]}/> }] : [];
    return {
      kind: "預算", no: b.budget_no, status: b.status,
      title: `${isCenter ? "【中心】" : ""}${b.account_name} · ${b.center_name}`,
      subtitle: `${kindLabel}${b.parent_budget_id ? "(已歸入中心)" : ""} · ${b.period_name || "當前期間"} · ${isCenter ? `子預算 ${roll.child_count || 0} 個` : `使用率 ${used}%`} · ${b.currency || "CNY"}`,
      actions: budgetActions,
      kpis: isCenter ? [...centerKpis, aiKpi] : [
        { label: "總額", value: erpMoney(b.amount, b.currency) },
        { label: "可用", value: erpMoney(b.available, b.currency), tone: ERP_APPLE.green },
        { label: "已佔用", value: erpMoney(b.reserved, b.currency), tone: ERP_APPLE.orange },
        { label: "已支出", value: erpMoney(b.spent, b.currency), tone: ERP_APPLE.red },
        aiKpi,
      ],
      sections: [
        ...childSection,
        { id: "reserve", title: "佔用流水", count: rsv.length, node: <ErpDataTable rows={rsv} empty="此預算暫無佔用" columns={[
          { key: "reservation_no", label: "編號" },
          { key: "source_title", label: "用途", wrap: true, render: (r) => r.source_title || r.note || "—" },
          { key: "source_type", label: "來源", render: (r) => RSV_SOURCE_LABEL[r.source_type] || r.source_type || "—" },
          { key: "amount", label: "金額", align: "right", render: (r) => erpMoney(r.amount, r.currency) },
          { key: "status", label: "狀態", render: (r) => <ErpBadge value={r.status}/> },
          { key: "created_at", label: "時間", render: (r) => (r.spent_at || r.created_at || "").slice(0, 16) || "—" },
          { key: "ops", label: "操作", render: rsvOps },
        ]}/> },
        { id: "ledger", title: "資金流水賬", hint: "複式分錄,借貸平衡,可追溯每一塊錢", node: <ErpBudgetLedger budgetId={b.id}/> },
        { id: "movement", title: "變動歷史", count: mov.length, node: <ErpDataTable rows={mov} empty="無變動記錄" columns={[
          { key: "movement_no", label: "流水號" },
          { key: "movement_type", label: "類型", render: (m) => ({ initial: "初始", increase: "追加", decrease: "扣減", set: "重設", correction: "更正" })[m.movement_type] || m.movement_type },
          { key: "amount_delta", label: "變動", align: "right", render: (m) => erpMoney(m.amount_delta, m.currency) },
          { key: "amount_after", label: "變更後", align: "right", render: (m) => erpMoney(m.amount_after, m.currency) },
          { key: "created_by_name", label: "操作人", render: (m) => m.created_by_name || "系統" },
          { key: "created_at", label: "時間" },
        ]}/> },
        { id: "tasks", title: "關聯工單", count: tasks.length, node: <ErpDataTable rows={tasks} empty="無關聯工單" columns={[
          { key: "task_no", label: "工單號", render: (t) => t.task_no || `WO-${t.id}` },
          { key: "task_name", label: "名稱", wrap: true },
          { key: "budget_estimate", label: "估算", align: "right", render: (t) => erpMoney(t.budget_estimate) },
          { key: "status", label: "狀態", render: (t) => <ErpBadge value={t.status || "planned"}/> },
        ]}/> },
        { id: "purchases", title: "關聯採購", count: prs.length, node: <ErpDataTable rows={prs} empty="無關聯採購" columns={[
          { key: "request_no", label: "申請號" },
          { key: "title", label: "標題", wrap: true },
          { key: "total_amount", label: "金額", align: "right", render: (p) => erpMoney(p.total_amount, p.currency) },
          { key: "status", label: "狀態", render: (p) => <ErpBadge value={p.status}/> },
        ]}/> },
      ],
    };
  };
  const buildTaskObject = (t) => {
    const rsv = reservations.filter((r) => r.id === t.budget_reservation_id);
    return {
      kind: "工單", no: t.task_no || `WO-${t.id}`, status: t.status || "planned",
      title: t.task_name,
      subtitle: `${t.center_name || "未綁成本中心"}${t.location_name ? ` · ${t.location_name}` : ""} · 負責人 ${t.owner_name || "—"}`,
      kpis: [
        { label: "預算估算", value: erpMoney(t.budget_estimate) },
        { label: "優先級", value: t.priority === "urgent" ? "緊急" : "普通", tone: t.priority === "urgent" ? ERP_APPLE.red : ERP_APPLE.ink },
        { label: "關聯預算", value: t.budget_no || "—" },
        { label: "狀態", value: erpStatus[t.status || "planned"]?.text || t.status },
      ],
      actions: erpAllowedStatuses(t, ["active", "completed", "cancelled"]).map((s) => ({ label: erpAllowedLabel(t, s), disabled: !!busy || t.status === s, primary: s === "completed", onClick: () => updateWorkTask(t.id, s) })),
      sections: [
        { id: "info", title: "基本信息", node: <ErpFieldGrid fields={[
          { label: "工單名稱", value: t.task_name },
          { label: "工單類型", value: t.task_type },
          { label: "成本中心", value: t.center_name },
          { label: "組織單元", value: t.org_unit_name },
          { label: "作業地點", value: t.location_name },
          { label: "負責人", value: t.owner_name },
          { label: "預算估算", value: erpMoney(t.budget_estimate) },
          { label: "計劃開始", value: t.planned_start },
          { label: "計劃結束", value: t.planned_end },
          { label: "完成時間", value: t.completed_at },
          { label: "說明", value: t.description },
        ]}/> },
        { id: "budget", title: "關聯預算佔用", count: rsv.length, node: <ErpDataTable rows={rsv} empty="未綁定預算佔用" columns={[
          { key: "reservation_no", label: "佔用編號" },
          { key: "budget_no", label: "預算" },
          { key: "amount", label: "金額", align: "right", render: (r) => erpMoney(r.amount, r.currency) },
          { key: "status", label: "狀態", render: (r) => <ErpBadge value={r.status}/> },
        ]}/> },
      ],
    };
  };
  const buildPurchaseObject = (p) => {
    const open = isErpPurchaseOpen(p);
    return {
      kind: "採購申請", no: p.request_no, status: p.status,
      title: p.title,
      subtitle: `${p.supplier_name || "未指定供應商"}${p.center_name ? ` · ${p.center_name}` : ""} · 申請人 ${p.requester_name || "—"}`,
      kpis: [
        { label: "總金額", value: erpMoney(p.total_amount, p.currency) },
        { label: "明細項", value: (p.lines || []).length },
        { label: "關聯預算", value: p.budget_no || "—" },
        { label: "優先級", value: p.priority === "urgent" ? "緊急" : "普通", tone: p.priority === "urgent" ? ERP_APPLE.red : ERP_APPLE.ink },
      ],
      actions: open ? erpPurchaseDirectStatuses(p).map((s) => ({ label: erpAllowedLabel(p, s, ERP_PURCHASE_ACTION_LABEL), disabled: !!busy || p.status === s, primary: s !== "cancelled", onClick: () => updatePurchase(p.id, s) })) : [],
      sections: [
        { id: "lines", title: "採購明細", count: (p.lines || []).length, node: <ErpDataTable rows={p.lines || []} empty="無明細" columns={[
          { key: "item_name", label: "物資", wrap: true },
          { key: "spec_model", label: "規格" },
          { key: "quantity", label: "數量", align: "right", render: (l) => `${erpQtyText(l.quantity)}${l.unit || ""}` },
          { key: "estimated_price", label: "預估單價", align: "right", render: (l) => erpMoney(l.estimated_price) },
        ]}/> },
        { id: "info", title: "申請信息", node: <ErpFieldGrid fields={[
          { label: "申請標題", value: p.title },
          { label: "供應商", value: p.supplier_name },
          { label: "成本中心", value: p.center_name },
          { label: "關聯預算", value: p.budget_no },
          { label: "申請人", value: p.requester_name },
          { label: "理由", value: p.reason },
          { label: "AI 摘要", value: p.ai_summary },
          { label: "流程約束", value: "提交時綁定採購工作流；批准、下單由節點產生，到貨由已簽發 PO 的正式收貨產生" },
        ]}/> },
      ],
    };
  };
  const activeObject = (() => {
    if (!activeObj) return null;
    if (activeObj.type === "budget") { const b = budgets.find((x) => x.id === activeObj.id); return b ? buildBudgetObject(b) : null; }
    if (activeObj.type === "task") { const t = workTasks.find((x) => x.id === activeObj.id); return t ? buildTaskObject(t) : null; }
    if (activeObj.type === "purchase") { const p = purchaseRequests.find((x) => x.id === activeObj.id); return p ? buildPurchaseObject(p) : null; }
    return null;
  })();

  if (state === "loading") return <div className="muted" style={{ fontSize: 13 }}>讀取 ERP 中樞中…</div>;

  if (activeObject) {
    return <FioriObjectPage obj={activeObject} onBack={() => setActiveObj(null)}
      onAsk={() => askSecretary(`請解釋${activeObject.kind} ${activeObject.no}(${activeObject.title})的當前情況、風險和下一步建議。`)}/>;
  }

  return (
    <div className="col gap-18" style={{ color: ERP_APPLE.ink }}>
      {editReq && (
        <div onClick={() => setEditReq(null)} style={{ position: "fixed", inset: 0, zIndex: 60, background: "rgba(15,23,42,0.45)", display: "grid", placeItems: "center", padding: 16 }}>
          <div onClick={(e) => e.stopPropagation()} style={{ width: "min(520px, 96vw)", background: "#fff", borderRadius: 12, border: `1px solid ${ERP_APPLE.hair}`, padding: 20 }} className="col gap-12">
            <div className="row spread">
              <div style={{ fontSize: 16, fontWeight: 900 }}>協作補充 / 修改 · {editReq.docNo}</div>
              <button className="btn btn-sm" onClick={() => setEditReq(null)}>✕</button>
            </div>
            <div style={{ fontSize: 12.5, color: ERP_APPLE.sub }}>
              你的補充會交給 AI 秘書審核;AI 只處理摘要、來源單位、經辦人等補充字段,通過後立即生效。只填要修改的項即可。
            </div>
            <label className="col gap-4" style={{ fontSize: 12.5, fontWeight: 700 }}>補充說明 / 修改理由
              <textarea className="input" rows={3} value={editReq.reason} placeholder="例如:這筆是調撥入庫,不該掛預算;或補充來源單位/經辦人"
                onChange={(e) => setEditReq({ ...editReq, reason: e.target.value })}/></label>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
              <label className="col gap-4" style={{ fontSize: 12, fontWeight: 700 }}>來源單位(可選)
                <input className="input" value={editReq.source_unit} onChange={(e) => setEditReq({ ...editReq, source_unit: e.target.value })}/></label>
              <label className="col gap-4" style={{ fontSize: 12, fontWeight: 700 }}>經辦人(可選)
                <input className="input" value={editReq.handler} onChange={(e) => setEditReq({ ...editReq, handler: e.target.value })}/></label>
            </div>
            <label className="col gap-4" style={{ fontSize: 12, fontWeight: 700 }}>摘要(可選,覆蓋原摘要)
              <input className="input" value={editReq.summary} onChange={(e) => setEditReq({ ...editReq, summary: e.target.value })}/></label>
            <div className="row gap-8" style={{ justifyContent: "flex-end" }}>
              <button className="btn" onClick={() => setEditReq(null)}>取消</button>
              <button className="btn btn-primary" disabled={busy === "editreq"} onClick={submitEditRequest}>{busy === "editreq" ? "AI 審核中…" : "交給 AI 秘書審核"}</button>
            </div>
          </div>
        </div>
      )}
      <section style={{
        position: "relative",
        overflow: "hidden",
        minHeight: 342,
        borderRadius: 8,
        border: `1px solid ${ERP_APPLE.hair}`,
        background: "#FBFBFD",
      }}>
        <ErpCanvas/>
        <div style={{ position: "relative", zIndex: 1, padding: "26px 28px", display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 320px), 1fr))", gap: 22, alignItems: "stretch" }}>
          <div className="col" style={{ justifyContent: "space-between", gap: 20 }}>
            <div className="col gap-12">
              <div className="row gap-8" style={{ flexWrap: "wrap" }}>
                <span style={{ height: 26, padding: "0 10px", borderRadius: 999, background: "#fff", border: `1px solid ${ERP_APPLE.hair}`, display: "inline-flex", alignItems: "center", gap: 6, fontSize: 12, fontWeight: 800, color: ERP_APPLE.blue }}>
                  <Icon name="sparkle" size={13}/>ERP Intelligence
                </span>
                <span style={{ height: 26, padding: "0 10px", borderRadius: 999, background: "#fff", border: `1px solid ${ERP_APPLE.hair}`, display: "inline-flex", alignItems: "center", gap: 6, fontSize: 12, fontWeight: 800, color: healthTone }}>
                  <Icon name="activity" size={13}/>{healthText}
                </span>
              </div>
              <div style={{ maxWidth: 680 }}>
                <h1 style={{ margin: 0, fontSize: 42, lineHeight: 1.05, fontWeight: 900, letterSpacing: 0, color: ERP_APPLE.ink }}>ERP 中樞</h1>
                <div style={{ marginTop: 10, fontSize: 18, lineHeight: 1.45, color: ERP_APPLE.sub, fontWeight: 650 }}>預算、工單、採購與庫存閉環統一交給 AI 草擬，人員只做確認和例外處理。</div>
              </div>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(118px, 1fr))", gap: 14 }}>
              <MiniMetric label="預算總額" value={erpMoney(summary.budget_amount)} tone={ERP_APPLE.ink}/>
              <MiniMetric label="可用" value={erpMoney(summary.budget_available)} tone={ERP_APPLE.green}/>
              <MiniMetric label="使用率" value={`${usage}%`} tone={usage > 90 ? ERP_APPLE.red : usage > 70 ? ERP_APPLE.orange : ERP_APPLE.blue}/>
              <MiniMetric label="待處理" value={pendingSignalCount} tone={healthTone}/>
            </div>
          </div>

          <div style={{ borderRadius: 8, background: "rgba(255,255,255,0.88)", border: `1px solid ${ERP_APPLE.hair}`, boxShadow: "0 18px 50px rgba(0,0,0,0.08)", padding: 16 }} className="col gap-12">
            <div className="row spread" style={{ gap: 12, alignItems: "flex-start" }}>
              <div>
                <div style={{ fontSize: 15, fontWeight: 900 }}>交給 AI 秘書</div>
                <div style={{ marginTop: 4, fontSize: 12, color: ERP_APPLE.sub }}>說人話即可 · 秘書在你權限內實時逐步執行 · 全程審計可回放</div>
              </div>
              <button className="btn btn-ghost btn-sm" onClick={load} disabled={!!busy} style={{ width: 32, padding: 0 }}>
                <Icon name="refresh" size={15}/>
              </button>
            </div>
            <textarea
              className="input"
              value={aiText}
              onChange={(e) => setAiText(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); const t = aiText.trim(); if (t) { delegateToAgent(t, true); setAiText(""); } } }}
              placeholder={quick[0] ? `例如：${quick[0]}` : "例如：給物資採購預算追加 2000、為玉賢線消缺建工單估算 800、申請採購 10 副絕緣手套…"}
              style={{ height: 86, resize: "none", borderRadius: 8, background: "#fff", fontSize: 14, lineHeight: 1.55 }}
            />
            <div className="row gap-8" style={{ flexWrap: "wrap" }}>
              {quick.map((q) => (
                <button key={q} onClick={() => delegateToAgent(q, true)} disabled={!!busy}
                  style={{ minHeight: 30, padding: "0 10px", borderRadius: 999, background: "#F5F5F7", border: `1px solid ${ERP_APPLE.hair}`, color: ERP_APPLE.ink, fontSize: 12, fontWeight: 700 }}>
                  {q}
                </button>
              ))}
            </div>
            <div className="row gap-8" style={{ justifyContent: "flex-end", flexWrap: "wrap" }}>
              <AppleButton primary onClick={() => { const t = (aiText || "請解釋 ERP 中樞當前狀態，並告訴我應該先處理什麼。").trim(); delegateToAgent(t, true); setAiText(""); }} icon="sparkle">交給秘書執行</AppleButton>
            </div>
          </div>
        </div>
      </section>

      {(error || notice) && (
        <div style={{ padding: 12, borderRadius: 8, border: `1px solid ${error ? "rgba(255,59,48,0.28)" : "rgba(52,199,89,0.28)"}`, background: error ? "rgba(255,59,48,0.08)" : "rgba(52,199,89,0.08)", color: error ? ERP_APPLE.red : ERP_APPLE.green, fontSize: 13, fontWeight: 750 }}>
          {error || notice}
        </div>
      )}

      <section style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 12 }}>
        <WorkflowChip icon="layers" label="成本中心" value={summary.cost_centers || 0} tone={ERP_APPLE.blue}
          onClick={() => explainMetric("成本中心", summary.cost_centers || 0, "成本中心決定預算、工單、採購歸屬。")}/>
        <WorkflowChip icon="clipboard" label="進行工單" value={openWorkTasks.length} tone={ERP_APPLE.blue}
          onClick={() => explainMetric("進行工單", openWorkTasks.length, "這代表尚未完成或取消的 ERP 工單。")}/>
        <WorkflowChip icon="inbound" label="採購申請" value={purchaseOpenCount} tone={ERP_APPLE.green}
          onClick={() => explainMetric("採購申請", purchaseOpenCount, "這代表仍在審批、下單或到貨流程中的採購。")}/>
        <WorkflowChip icon="link" label="庫存未掛預算" value={inventoryUnlinkedCount} tone={inventoryUnlinkedCount ? ERP_APPLE.orange : ERP_APPLE.green}
          onClick={() => explainMetric("庫存未掛預算", inventoryUnlinkedCount, "這代表庫存單據還沒有和 ERP 預算佔用閉環關聯。")}/>
      </section>

      <section style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 340px), 1fr))", gap: 16, alignItems: "start" }}>
        <div style={{ borderRadius: 8, border: `1px solid ${ERP_APPLE.hair}`, background: "#fff", padding: 16 }} className="col gap-10">
          <div className="row spread" style={{ alignItems: "flex-start", gap: 12 }}>
            <div>
              <div style={{ fontSize: 16, fontWeight: 900 }}>預算健康</div>
              <div style={{ fontSize: 12, color: ERP_APPLE.sub, marginTop: 4 }}>
                {summary.active_period?.period_name || "當前期間"} · {budgetGroups.all.length} 個中心 · 進行中 {budgetGroups.activeCount} · 待閉環 {budgetGroups.reviewCount} · 已歸檔 {budgetGroups.archivedCount}
              </div>
            </div>
            <div className="num" style={{ color: ERP_APPLE.blue, fontSize: 24, fontWeight: 900 }}>{erpMoney(summary.budget_available)}</div>
          </div>
          <div style={{ height: 10, borderRadius: 999, background: "#F5F5F7", overflow: "hidden" }}>
            <div style={{ height: "100%", width: `${usage}%`, background: usage > 90 ? ERP_APPLE.red : usage > 70 ? ERP_APPLE.orange : ERP_APPLE.blue }}/>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(130px, 1fr))", gap: 10 }}>
            <MiniMetric label="已佔用" value={erpMoney(summary.budget_reserved)} tone={ERP_APPLE.orange}/>
            <MiniMetric label="已支出" value={erpMoney(summary.budget_spent)} tone={ERP_APPLE.red}/>
            <MiniMetric label="創意預算" value={erpMoney(summary.collab_budget_planned)} tone={ERP_APPLE.ink}/>
          </div>
          <div>
            {budgetGroups.all.length === 0 && <div className="muted" style={{ padding: "18px 0", fontSize: 13 }}>暫無預算資料</div>}
            {budgetGroups.review.length > 0 && (
              <div style={{ paddingTop: 6 }}>
                <div style={{ fontSize: 12, color: ERP_APPLE.orange, fontWeight: 900, marginBottom: 2 }}>AI 待閉環 / 異常</div>
                {budgetGroups.review.map((group) => {
                  const open = expandedBudgetCenters[`review:${group.id}`] ?? true;
                  return (
                    <BudgetCenterGroup
                      key={`review-${group.id}`}
                      group={group}
                      open={open}
                      onToggle={() => setExpandedBudgetCenters((next) => ({ ...next, [`review:${group.id}`]: !open }))}
                      onOpenBudget={(id) => setActiveObj({ type: "budget", id })}
                    />
                  );
                })}
              </div>
            )}
            {budgetGroups.active.map((group, idx) => {
              const open = expandedBudgetCenters[group.id] ?? idx < 2;
              return (
                <BudgetCenterGroup
                  key={group.id}
                  group={group}
                  open={open}
                  onToggle={() => setExpandedBudgetCenters((next) => ({ ...next, [group.id]: !open }))}
                  onOpenBudget={(id) => setActiveObj({ type: "budget", id })}
                />
              );
            })}
            <ArchiveBlock title="已歸檔預算" count={budgetGroups.archivedCount}>
              {budgetGroups.archived.map((group) => {
                const key = `archive:${group.id}`;
                const open = expandedBudgetCenters[key] ?? false;
                return (
                  <BudgetCenterGroup
                    key={key}
                    group={group}
                    open={open}
                    onToggle={() => setExpandedBudgetCenters((next) => ({ ...next, [key]: !open }))}
                    onOpenBudget={(id) => setActiveObj({ type: "budget", id })}
                  />
                );
              })}
            </ArchiveBlock>
          </div>
        </div>

        <div style={{ borderRadius: 8, border: `1px solid ${ERP_APPLE.hair}`, background: "#fff", padding: 16 }} className="col gap-10">
          <div className="row spread" style={{ alignItems: "flex-start", gap: 12 }}>
            <div>
              <div style={{ fontSize: 16, fontWeight: 900 }}>AI 待辦流</div>
              <div style={{ fontSize: 12, color: ERP_APPLE.sub, marginTop: 4 }}>預警、未掛預算、採購和例外</div>
            </div>
            <span className="badge badge-info" style={{ height: 22 }}>{urgentQueue.length}</span>
          </div>
          {urgentQueue.length === 0 && <div className="muted" style={{ padding: "18px 0", fontSize: 13 }}>暫無高優先級待辦</div>}
          {urgentQueue.map((item, idx) => (
            <StreamRow key={`${item.type}-${idx}`} icon={item.icon} title={item.title} sub={item.sub} right={item.right} tone={item.tone}
              onClick={() => explainRow("AI 待辦流", item.title, item.sub)}
              actions={item.type === "doc" ? [
                <button key="collab" className="btn btn-sm" disabled={!!busy}
                  onClick={(e) => { e.stopPropagation(); setEditReq({ docId: item.docId, docNo: item.docNo, reason: "", summary: "", source_unit: "", handler: "" }); }}>
                  協作補充 / 修改
                </button>,
              ] : undefined}/>
          ))}
        </div>
      </section>

      <section>
        <ErpPeriodTree/>
      </section>

      <section style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 280px), 1fr))", gap: 16, alignItems: "start" }}>
        <div style={{ borderRadius: 8, border: `1px solid ${ERP_APPLE.hair}`, background: "#fff", padding: 16 }}>
          <div style={{ fontSize: 16, fontWeight: 900, marginBottom: 4 }}>工單</div>
          <div style={{ fontSize: 12, color: ERP_APPLE.sub, marginBottom: 8 }}>AI 草擬，人員流轉狀態</div>
          {openWorkTasks.length === 0 && <div className="muted" style={{ fontSize: 13, padding: "16px 0" }}>暫無進行中工單</div>}
          {openWorkTasks.slice(0, 6).map((task) => (
            <StreamRow
              key={task.id}
              icon="clipboard"
              tone={task.priority === "urgent" ? ERP_APPLE.red : ERP_APPLE.blue}
              title={task.task_name}
              sub={`${task.task_no || `WO-${task.id}`} · ${task.center_name || "未綁成本中心"} · ${erpMoney(task.budget_estimate)}`}
              right={<ErpBadge value={task.status || "planned"}/>}
              onClick={() => setActiveObj({ type: "task", id: task.id })}
              actions={erpAllowedStatuses(task, ["active", "completed", "cancelled"]).map((status) => (
                <button key={status} className="btn btn-sm" disabled={!!busy || task.status === status} onClick={(e) => { e.stopPropagation(); updateWorkTask(task.id, status); }}>{erpAllowedLabel(task, status)}</button>
              ))}
            />
          ))}
        </div>

        <div style={{ borderRadius: 8, border: `1px solid ${ERP_APPLE.hair}`, background: "#fff", padding: 16 }}>
          <div style={{ fontSize: 16, fontWeight: 900, marginBottom: 4 }}>採購</div>
          <div style={{ fontSize: 12, color: ERP_APPLE.sub, marginBottom: 8 }}>
            進行中 {openPurchases.length} · 已歸檔 {archivedPurchases.length} · 供應商 {summary.suppliers_active || 0}
            {hiddenPurchaseCount ? ` · 已隱藏更早 ${hiddenPurchaseCount} 條` : ""}
          </div>
          {visiblePurchases.length === 0 && <div className="muted" style={{ fontSize: 13, padding: "16px 0" }}>暫無進行中採購</div>}
          {visiblePurchases.map((pr) => {
            const open = isErpPurchaseOpen(pr);
            const linePreview = purchaseLinePreview(pr);
            return (
            <StreamRow
              key={pr.id}
              icon="inbound"
              tone={pr.priority === "urgent" ? ERP_APPLE.red : open ? ERP_APPLE.green : ERP_APPLE.sub}
              title={pr.title}
              sub={`${pr.request_no} · ${linePreview} · ${pr.supplier_name || "未指定供應商"} · ${erpMoney(pr.total_amount, pr.currency)}`}
              right={<ErpBadge value={pr.status}/>}
              onClick={() => setActiveObj({ type: "purchase", id: pr.id })}
              actions={open && erpPurchaseDirectStatuses(pr).map((status) => (
                <button key={status} className="btn btn-sm" disabled={!!busy || pr.status === status} onClick={(e) => { e.stopPropagation(); updatePurchase(pr.id, status); }}>{erpAllowedLabel(pr, status, ERP_PURCHASE_ACTION_LABEL)}</button>
              ))}
            />
          );})}
          <ArchiveBlock title="歸檔採購" count={archivedPurchases.length}>
            {archivedPurchases.slice(0, 8).map((pr) => (
              <StreamRow
                key={`archive-pr-${pr.id}`}
                icon="inbound"
                tone={ERP_APPLE.sub}
                title={pr.title}
                sub={`${pr.request_no} · ${purchaseLinePreview(pr)} · ${pr.supplier_name || "未指定供應商"} · ${erpMoney(pr.total_amount, pr.currency)}`}
                right={<ErpBadge value={pr.status}/>}
                onClick={() => setActiveObj({ type: "purchase", id: pr.id })}
              />
            ))}
            {archivedPurchases.length > 8 && <div className="muted" style={{ fontSize: 12, paddingTop: 8 }}>還有 {archivedPurchases.length - 8} 筆已歸檔採購在明細視圖中。</div>}
          </ArchiveBlock>
        </div>

        <div style={{ borderRadius: 8, border: `1px solid ${ERP_APPLE.hair}`, background: "#fff", padding: 16 }}>
          <div style={{ fontSize: 16, fontWeight: 900, marginBottom: 4 }}>閉環</div>
          <div style={{ fontSize: 12, color: ERP_APPLE.sub, marginBottom: 8 }}>待處理 {activeClosureCount} · 已歸檔 {archivedClosureCount}</div>
          {activeClosureCount === 0 && <div className="muted" style={{ fontSize: 13, padding: "16px 0" }}>暫無待閉環事項</div>}
          {activeReservations.slice(0, 4).map((r) => (
            <StreamRow
              key={r.id}
              icon="clock"
              tone={ERP_APPLE.orange}
              title={r.source_title || r.note || "預算佔用"}
              sub={`${r.reservation_no} · ${r.center_name || "—"} · ${erpMoney(r.amount, r.currency)}`}
              right={<ErpBadge value={r.status}/>}
              onClick={() => explainRow("閉環 / 預算佔用", r.source_title || r.note || "預算佔用", `${r.reservation_no} · ${r.center_name || "—"} · 狀態 ${erpStatus[r.status]?.text || r.status || "—"} · 金額 ${erpMoney(r.amount, r.currency)}`)}
              actions={erpAllowedStatuses(r, erpReservationNextStatuses(r)).map((status) => (
                <button key={status} className="btn btn-sm" disabled={!!busy || r.status === status} onClick={(e) => { e.stopPropagation(); updateReservation(r.id, status); }}>{erpAllowedLabel(r, status, ERP_RESERVATION_ACTION_LABEL)}</button>
              ))}
            />
          ))}
          {unlinkedDocs.slice(0, 3).map((d) => (
            <StreamRow
              key={`doc-${d.id}`}
              icon={isBudgetUnlinkedOpen(d) ? "link" : "box"}
              tone={isBudgetUnlinkedOpen(d) ? ERP_APPLE.orange : ERP_APPLE.blue}
              title={d.document_no}
              sub={`${d.business_type || d.document_type || "庫存單據"} · ${d.summary || "待處理"} · 明細 ${d.line_count || 0}`}
              right={isBudgetUnlinkedOpen(d) ? <span className="badge badge-warn" style={{ height: 22 }}>未掛預算</span> : <ErpBadge value={d.status}/>}
              onClick={() => explainRow("閉環 / 庫存單據", d.document_no, `${d.business_type || d.document_type || "庫存單據"} · ${d.summary || "—"}`)}
            />
          ))}
          {openStocktakeTasks.slice(0, 2).map((t) => (
            <StreamRow key={t.task_no} icon="scan" tone={ERP_APPLE.blue} title={t.task_name} sub={`${t.task_no} · ${t.area || "全庫"} · 差異 ${t.diff_count || 0}`} right={<span className="num muted">{Number(t.progress || 0)}%</span>}
              onClick={() => explainRow("閉環 / 盤點任務", t.task_name, `${t.task_no} · ${t.area || "全庫"} · 差異 ${t.diff_count || 0} · 進度 ${Number(t.progress || 0)}%`)}/>
          ))}
          <ArchiveBlock title="閉環歸檔" count={archivedClosureCount}>
            {budgetMovements.slice(0, 4).map((m) => (
              <StreamRow
                key={`bm-${m.id}`}
                icon="chart"
                tone={Number(m.amount_delta || 0) < 0 ? ERP_APPLE.red : ERP_APPLE.green}
                title={m.note || `${m.center_name || "預算"} · ${m.account_name || ""}`}
                sub={`${m.movement_no} · ${m.budget_no || "—"} · 變動 ${erpMoney(m.amount_delta, m.currency)} · 變更後 ${erpMoney(m.amount_after, m.currency)}`}
                right={<span className="badge badge-info" style={{ height: 22 }}>{({ initial: "初始", increase: "追加", decrease: "扣減", set: "重設", correction: "更正" })[m.movement_type] || m.movement_type}</span>}
                onClick={() => explainRow("閉環 / 預算流水", m.note || `${m.center_name || "預算"} · ${m.account_name || ""}`, `${m.movement_no} · ${m.budget_no || "—"} · 變動 ${erpMoney(m.amount_delta, m.currency)} · 變更後 ${erpMoney(m.amount_after, m.currency)}`)}
              />
            ))}
            {archivedReservations.slice(0, 4).map((r) => (
              <StreamRow
                key={`archive-rsv-${r.id}`}
                icon="clock"
                tone={ERP_APPLE.sub}
                title={r.source_title || r.note || "預算佔用"}
                sub={`${r.reservation_no} · ${r.center_name || "—"} · ${erpMoney(r.amount, r.currency)}`}
                right={<ErpBadge value={r.status}/>}
                onClick={() => explainRow("閉環 / 歸檔佔用", r.source_title || r.note || "預算佔用", `${r.reservation_no} · ${r.center_name || "—"} · 狀態 ${erpStatus[r.status]?.text || r.status || "—"} · 金額 ${erpMoney(r.amount, r.currency)}`)}
              />
            ))}
            {archivedInventoryDocuments.slice(0, 3).map((d) => (
              <StreamRow
                key={`archive-doc-${d.id}`}
                icon="box"
                tone={ERP_APPLE.sub}
                title={d.document_no}
                sub={`${d.business_type || d.document_type || "庫存單據"} · ${d.summary || "已閉環"} · 明細 ${d.line_count || 0}`}
                right={<ErpBadge value={d.status}/>}
                onClick={() => explainRow("閉環 / 歸檔單據", d.document_no, `${d.business_type || d.document_type || "庫存單據"} · ${d.summary || "—"}`)}
              />
            ))}
            {archivedStocktakeTasks.slice(0, 2).map((t) => (
              <StreamRow key={`archive-st-${t.task_no}`} icon="scan" tone={ERP_APPLE.sub} title={t.task_name} sub={`${t.task_no} · ${t.area || "全庫"} · 差異 ${t.diff_count || 0}`} right={<span className="badge badge-gray" style={{ height: 22 }}>{t.status || "已歸檔"}</span>}
                onClick={() => explainRow("閉環 / 歸檔盤點", t.task_name, `${t.task_no} · ${t.area || "全庫"} · 差異 ${t.diff_count || 0} · 進度 ${Number(t.progress || 0)}%`)}/>
            ))}
            {archivedClosureCount > 13 && <div className="muted" style={{ fontSize: 12, paddingTop: 8 }}>還有更多歸檔流水可在對象明細或台賬中查看。</div>}
          </ArchiveBlock>
          {suppliers.length > 0 && (
            <div style={{ paddingTop: 12, borderTop: `1px solid ${ERP_APPLE.hair}`, marginTop: 2 }}>
              <div style={{ fontSize: 12, color: ERP_APPLE.sub, marginBottom: 8 }}>主要供應商</div>
              <div className="row gap-6" style={{ flexWrap: "wrap" }}>
                {suppliers.slice(0, 6).map((s) => <span key={s.id} className="badge badge-gray" style={{ height: 22 }}>{s.supplier_name}</span>)}
              </div>
            </div>
          )}
        </div>
      </section>
    </div>
  );
};

window.PageERP = PageERP;
