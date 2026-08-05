/* ============================================================
   9 · 用戶管理台 — 註冊審批 + 用戶/角色管理
   ============================================================ */
const { useState: useStatePerm, useEffect: useEffectPerm } = React;

const REG_STATUS_LABEL = { pending: "待審批", approved: "已通過", rejected: "已駁回" };
const REG_STATUS_BADGE = { pending: "badge-warn", approved: "badge-ok", rejected: "badge-danger" };

const PagePerms = () => {
  const [tab, setTab] = useStatePerm("memberships");
  const [requests, setRequests] = useStatePerm([]);
  const [pendingCount, setPendingCount] = useStatePerm(0);
  const [users, setUsers] = useStatePerm([]);
  const [roles, setRoles] = useStatePerm([]);
  const [loading, setLoading] = useStatePerm(true);
  const [forbidden, setForbidden] = useStatePerm(false);
  const [showImport, setShowImport] = useStatePerm(false);
  const [selected, setSelected] = useStatePerm([]);
  const [error, setError] = useStatePerm("");
  const [busyId, setBusyId] = useStatePerm(null);
  // 每條申請選擇的角色與駁回備註（鍵為申請 id）
  const [roleChoice, setRoleChoice] = useStatePerm({});
  const [noteDraft, setNoteDraft] = useStatePerm({});
  const [resetInfo, setResetInfo] = useStatePerm(null); // 重置後展示臨時密碼
  const [memberships, setMemberships] = useStatePerm([]); // MB-4 加入申請
  const [memberCount, setMemberCount] = useStatePerm(0);

  const roleName = (id) => (roles.find((r) => String(r.id) === String(id)) || {}).role_name || "—";
  const roleColor = (id) => (roles.find((r) => String(r.id) === String(id)) || {}).color || "var(--ink-3)";

  const loadAll = () => {
    setLoading(true);
    setError("");
    const status = (tab === "users" || tab === "memberships" || tab === "topology") ? "pending" : tab;
    Promise.all([
      window.authFetch(`/api/auth/registrations?status=${status}`).then((res) => ({ res, key: "reg" })),
      window.authFetch("/api/users").then((res) => ({ res, key: "users" })),
      window.authFetch("/api/memberships/pending").then((res) => ({ res, key: "mem" })),
    ])
      .then(async (results) => {
        for (const { res } of results) {
          if (res.status === 403) { setForbidden(true); return; }
        }
        const reg = await results[0].res.json();
        const usr = await results[1].res.json();
        const mem = await results[2].res.json();
        setForbidden(false);
        setRequests(reg.requests || []);
        setPendingCount(reg.pending_count || 0);
        setUsers(usr.users || []);
        setRoles(usr.roles || []);
        setMemberships(mem.requests || []);
        setMemberCount(mem.pending_count || 0);
      })
      .catch((err) => setError(err.message || String(err)))
      .finally(() => setLoading(false));
  };

  const decideMembership = (m, action) => {
    if (busyId) return;
    setBusyId("m" + m.id);
    setError("");
    const body = action === "approve" ? { role_id: roleChoice["m" + m.id] || m.requested_role_id || "" } : {};
    window.authFetch(`/api/memberships/${m.id}/${action}`, {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
    })
      .then((res) => res.json().then((data) => ({ ok: res.ok, data })))
      .then(({ ok, data }) => { if (!ok) throw new Error(data.error || "操作失敗"); loadAll(); })
      .catch((err) => setError(err.message || String(err)))
      .finally(() => setBusyId(null));
  };

  useEffectPerm(() => { loadAll(); }, [tab]);

  const decide = (req, action) => {
    if (busyId) return;
    setBusyId(req.id);
    setError("");
    const body = action === "approve"
      ? { role_id: roleChoice[req.id] || req.requested_role_id || "", note: noteDraft[req.id] || "" }
      : { note: noteDraft[req.id] || "" };
    window.authFetch(`/api/auth/registrations/${req.id}/${action}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    })
      .then((res) => res.json().then((data) => ({ ok: res.ok, data })))
      .then(({ ok, data }) => {
        if (!ok) throw new Error(data.error || "操作失敗");
        loadAll();
      })
      .catch((err) => setError(err.message || String(err)))
      .finally(() => setBusyId(null));
  };

  const updateUser = (user, kind, value) => {
    if (busyId) return;
    setBusyId("u" + user.id);
    setError("");
    const path = kind === "active" ? `/api/users/${user.id}/active` : `/api/users/${user.id}/role`;
    const body = kind === "active" ? { active: value } : { role_id: value };
    window.authFetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    })
      .then((res) => res.json().then((data) => ({ ok: res.ok, data })))
      .then(({ ok, data }) => {
        if (!ok) throw new Error(data.error || "操作失敗");
        loadAll();
      })
      .catch((err) => setError(err.message || String(err)))
      .finally(() => setBusyId(null));
  };

  const resetPassword = (user) => {
    if (busyId) return;
    if (!window.confirm(`確定重置「${user.display_name}」的密碼?該用戶當前登入會立即失效,你需要把臨時密碼告知本人。`)) return;
    setBusyId("u" + user.id);
    setError("");
    window.authFetch(`/api/users/${user.id}/reset-password`, { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" })
      .then((res) => res.json().then((data) => ({ ok: res.ok, data })))
      .then(({ ok, data }) => {
        if (!ok) throw new Error(data.error || "重置失敗");
        setResetInfo({ name: user.display_name, username: user.username, password: data.temp_password });
      })
      .catch((err) => setError(err.message || String(err)))
      .finally(() => setBusyId(null));
  };

  const toggleSel = (id) => setSelected((s) => s.includes(id) ? s.filter((x) => x !== id) : [...s, id]);
  const toggleAll = () => setSelected((s) => s.length === users.length ? [] : users.map((u) => u.id));

  const bulkAction = (action) => {
    if (busyId || !selected.length) return;
    const label = action === "delete" ? "刪除" : "停用";
    if (!window.confirm(`確定批量${label}所選 ${selected.length} 個帳號?${action === "delete" ? "\n刪除不可恢復。" : ""}\n(當前登入帳號、最後一個系統管理員會自動跳過)`)) return;
    setBusyId("bulk");
    setError("");
    window.authFetch("/api/users/bulk-action", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ ids: selected, action }) })
      .then((res) => res.json().then((data) => ({ ok: res.ok, data })))
      .then(({ ok, data }) => {
        if (!ok) throw new Error(data.error || "批量操作失敗");
        setSelected([]);
        if (data.failed_count) setError(`成功${label} ${data.done_count} 個;${data.failed_count} 個跳過:` + data.failed.map((f) => `#${f.id}(${f.reason})`).join("、"));
        loadAll();
      })
      .catch((err) => setError(err.message || String(err)))
      .finally(() => setBusyId(null));
  };

  const deleteUser = (user) => {
    if (busyId) return;
    if (!window.confirm(`確定刪除帳號「${user.display_name}」(@${user.username})?\n此操作不可恢復:該帳號將被移除,登入立即失效。`)) return;
    setBusyId("u" + user.id);
    setError("");
    window.authFetch(`/api/users/${user.id}/delete`, { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" })
      .then((res) => res.json().then((data) => ({ ok: res.ok, data })))
      .then(({ ok, data }) => {
        if (!ok) throw new Error(data.error || "刪除失敗");
        loadAll();
      })
      .catch((err) => setError(err.message || String(err)))
      .finally(() => setBusyId(null));
  };

  if (forbidden) {
    return (
      <div className="col gap-18">
        <PageHead title="用戶管理台" sub="註冊審批 · 用戶與角色管理"/>
        <div className="card col center" style={{ padding: 40, gap: 12 }}>
          <Icon name="shield" size={32} color="var(--ink-4)"/>
          <div style={{ fontWeight: 700 }}>當前帳號沒有用戶管理權限</div>
          <div className="muted" style={{ fontSize: 13 }}>需要「users.manage」權限（系統管理員）才能審批註冊與管理用戶。</div>
        </div>
      </div>
    );
  }

  const TabBtn = ({ id, label, count }) => (
    <button onClick={() => setTab(id)} className="btn btn-sm" style={{
      background: tab === id ? "var(--blue)" : "var(--surface-2)", color: tab === id ? "#fff" : "var(--ink-2)",
    }}>
      {label}{count ? <span className="badge" style={{ marginLeft: 6, height: 18, background: "rgba(255,255,255,.25)", color: "inherit" }}>{count}</span> : null}
    </button>
  );

  return (
    <div className="col gap-18">
      <PageHead title="用戶管理台" sub="註冊審批 → 角色分配 → 用戶啟用 · 全流程管理"
        actions={<>
          <button className="btn btn-sm" onClick={loadAll}><Icon name="refresh" size={14}/>刷新</button>
          <button className="btn btn-primary btn-sm" onClick={() => setShowImport(true)}><Icon name="inbound" size={14}/>批量導入</button>
        </>}/>
      {showImport && <BulkImportModal roles={roles} onClose={() => setShowImport(false)} onDone={loadAll}/>}

      <div className="row gap-8">
        <TabBtn id="memberships" label="註冊/加入申請" count={memberCount}/>
        <TabBtn id="pending" label="舊註冊申請" count={pendingCount}/>
        <TabBtn id="approved" label="已通過"/>
        <TabBtn id="rejected" label="已駁回"/>
        <TabBtn id="users" label="用戶列表" count={users.length}/>
        <TabBtn id="topology" label="權限拓撲"/>
      </div>

      {error && <div className="card" style={{ padding: 12, color: "var(--danger)", fontWeight: 700, fontSize: 13 }}>{error}</div>}
      {loading && <div className="muted" style={{ fontSize: 13 }}>載入中…</div>}

      {/* 加入申請(MB-4:全局用戶用企業代碼加入本公司)*/}
      {!loading && tab === "memberships" && (
        <div className="col gap-12">
          {memberships.length === 0 && <div className="card muted" style={{ padding: 28, textAlign: "center", fontSize: 13 }}>暫無加入申請</div>}
          {memberships.map((m) => (
            <div key={m.id} className="card fade-up" style={{ padding: 18 }}>
              <div className="row spread" style={{ marginBottom: 12 }}>
                <div className="col gap-2">
                  <span style={{ fontSize: 14.5, fontWeight: 700 }}>{m.display_name} <span className="num muted" style={{ fontSize: 12 }}>@{m.username}</span></span>
                  <span className="muted" style={{ fontSize: 11.5 }}>申請加入本公司 · {m.created_at}</span>
                </div>
                <span className="badge badge-warn" style={{ height: 22 }}>待審批</span>
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: 10, marginBottom: 12 }}>
                {[["企業代碼", m.tenant_slug], ["部門/班組", m.department], ["聯繫方式", m.contact], ["期望角色", m.requested_role_name], ["申請理由", m.reason]].map(([k, v], i) => (
                  <div key={i} className="col gap-3" style={{ fontSize: 12.5 }}>
                    <span className="muted" style={{ fontSize: 11 }}>{k}</span>
                    <span>{v || "—"}</span>
                  </div>
                ))}
              </div>
              <div className="row gap-10" style={{ borderTop: "1px solid var(--line)", paddingTop: 12, flexWrap: "wrap", alignItems: "center" }}>
                <span className="muted" style={{ fontSize: 12, fontWeight: 700 }}>分配角色</span>
                <select className="input" style={{ maxWidth: 200 }} value={roleChoice["m" + m.id] || m.requested_role_id || ""} onChange={(e) => setRoleChoice({ ...roleChoice, ["m" + m.id]: e.target.value })}>
                  <option value="">默認(最小權限)</option>
                  {roles.map((r) => <option key={r.id} value={r.id}>{r.role_name}</option>)}
                </select>
                <button className="btn btn-primary btn-sm" disabled={busyId === "m" + m.id} onClick={() => decideMembership(m, "approve")}><Icon name="check" size={14}/>通過</button>
                <button className="btn btn-sm" disabled={busyId === "m" + m.id} style={{ color: "var(--danger)" }} onClick={() => decideMembership(m, "reject")}>駁回</button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* 註冊申請列表 */}
      {!loading && tab !== "users" && tab !== "memberships" && tab !== "topology" && (
        <div className="col gap-12">
          {requests.length === 0 && <div className="card muted" style={{ padding: 28, textAlign: "center", fontSize: 13 }}>暫無{REG_STATUS_LABEL[tab]}申請</div>}
          {requests.map((req) => (
            <div key={req.id} className="card fade-up" style={{ padding: 18 }}>
              <div className="row spread" style={{ marginBottom: 12 }}>
                <div className="row gap-12">
                  <div style={{ width: 40, height: 40, borderRadius: 11, background: "var(--grad-soft)", color: "var(--blue)", display: "grid", placeItems: "center", fontWeight: 700 }}>
                    {(req.display_name || req.username || "?").slice(0, 1)}
                  </div>
                  <div className="col gap-2">
                    <span style={{ fontSize: 14.5, fontWeight: 700 }}>{req.display_name} <span className="num muted" style={{ fontSize: 12 }}>@{req.username}</span></span>
                    <span className="muted" style={{ fontSize: 11.5 }}>{req.created_at}</span>
                  </div>
                </div>
                <span className={`badge ${REG_STATUS_BADGE[req.status]}`} style={{ height: 22 }}>{REG_STATUS_LABEL[req.status]}</span>
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: 10, marginBottom: 12 }}>
                {[["部門/班組", req.department], ["聯繫方式", req.contact], ["期望角色", req.requested_role_name], ["申請理由", req.reason]].map(([k, v], i) => (
                  <div key={i} className="col gap-3" style={{ fontSize: 12.5 }}>
                    <span className="muted" style={{ fontSize: 11 }}>{k}</span>
                    <span>{v || "—"}</span>
                  </div>
                ))}
              </div>

              {req.status === "pending" ? (
                <div className="col gap-10" style={{ borderTop: "1px solid var(--line)", paddingTop: 12 }}>
                  <div className="row gap-10" style={{ flexWrap: "wrap", alignItems: "center" }}>
                    <span className="muted" style={{ fontSize: 12, fontWeight: 700 }}>分配角色</span>
                    <select className="input" style={{ maxWidth: 200 }}
                      value={roleChoice[req.id] || req.requested_role_id || ""}
                      onChange={(e) => setRoleChoice({ ...roleChoice, [req.id]: e.target.value })}>
                      <option value="">請選擇角色</option>
                      {roles.map((r) => <option key={r.id} value={r.id}>{r.role_name}</option>)}
                    </select>
                  </div>
                  <input className="input" placeholder="審批備註 / 駁回理由（可選）"
                    value={noteDraft[req.id] || ""} onChange={(e) => setNoteDraft({ ...noteDraft, [req.id]: e.target.value })}/>
                  <div className="row gap-8">
                    <button className="btn btn-primary btn-sm" disabled={busyId === req.id} onClick={() => decide(req, "approve")}>
                      <Icon name="check" size={14}/>通過並建立帳號
                    </button>
                    <button className="btn btn-sm" disabled={busyId === req.id} style={{ color: "var(--danger)" }} onClick={() => decide(req, "reject")}>
                      駁回
                    </button>
                  </div>
                </div>
              ) : (
                <div className="muted" style={{ fontSize: 12, borderTop: "1px solid var(--line)", paddingTop: 10 }}>
                  {req.reviewer_name ? `審批人：${req.reviewer_name}` : ""}
                  {req.assigned_role_name ? ` · 角色：${req.assigned_role_name}` : ""}
                  {req.review_note ? ` · 備註：${req.review_note}` : ""}
                  {req.reviewed_at ? ` · ${req.reviewed_at}` : ""}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* 用戶列表 */}
      {!loading && tab === "users" && (
        <div className="col gap-12">
        {selected.length > 0 && (
          <div className="card row spread" style={{ padding: "10px 16px", background: "var(--blue-soft)", border: "1px solid rgba(27,107,255,.2)" }}>
            <span style={{ fontSize: 13, fontWeight: 700, color: "var(--blue)" }}>已選 {selected.length} 個帳號</span>
            <div className="row gap-8">
              <button className="btn btn-sm" disabled={busyId === "bulk"} onClick={() => bulkAction("deactivate")}>批量停用</button>
              <button className="btn btn-sm" disabled={busyId === "bulk"} style={{ color: "var(--danger)" }} onClick={() => bulkAction("delete")}>批量刪除</button>
              <button className="btn btn-sm" onClick={() => setSelected([])}>取消選擇</button>
            </div>
          </div>
        )}
        <div className="card fade-up" style={{ padding: 0, overflow: "hidden" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
            <thead>
              <tr style={{ background: "var(--surface-2)", textAlign: "left" }}>
                <th style={{ padding: "12px 16px", width: 36 }}>
                  <input type="checkbox" checked={users.length > 0 && selected.length === users.length} onChange={toggleAll}/>
                </th>
                {["用戶", "帳號", "角色", "狀態", "操作"].map((h) => (
                  <th key={h} style={{ padding: "12px 16px", fontWeight: 700, fontSize: 12 }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id} style={{ borderTop: "1px solid var(--line)", background: selected.includes(u.id) ? "var(--blue-soft)" : undefined }}>
                  <td style={{ padding: "12px 16px" }}>
                    <input type="checkbox" checked={selected.includes(u.id)} onChange={() => toggleSel(u.id)}/>
                  </td>
                  <td style={{ padding: "12px 16px", fontWeight: 700 }}>{u.display_name}</td>
                  <td style={{ padding: "12px 16px" }} className="num muted">@{u.username}</td>
                  <td style={{ padding: "12px 16px" }}>
                    <select className="input" style={{ maxWidth: 180, height: 34 }}
                      value={(u.roles[0] || {}).id || ""}
                      disabled={busyId === "u" + u.id}
                      onChange={(e) => updateUser(u, "role", e.target.value)}>
                      <option value="">（無角色）</option>
                      {roles.map((r) => <option key={r.id} value={r.id}>{r.role_name}</option>)}
                    </select>
                  </td>
                  <td style={{ padding: "12px 16px" }}>
                    <span className={`badge ${u.active ? "badge-ok" : "badge-gray"}`} style={{ height: 20 }}>{u.active ? "啟用" : "停用"}</span>
                  </td>
                  <td style={{ padding: "12px 16px" }}>
                    <div className="row gap-6">
                      <button className="btn btn-sm" disabled={busyId === "u" + u.id} onClick={() => updateUser(u, "active", !u.active)}
                        style={{ color: u.active ? "var(--danger)" : "var(--ok)" }}>
                        {u.active ? "停用" : "啟用"}
                      </button>
                      <button className="btn btn-sm" disabled={busyId === "u" + u.id} onClick={() => resetPassword(u)}>重置密碼</button>
                      <button className="btn btn-sm" disabled={busyId === "u" + u.id} style={{ color: "var(--danger)" }} onClick={() => deleteUser(u)}>刪除</button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        </div>
      )}

      {!loading && tab === "topology" && <PermissionTopologyPanel/>}

      {resetInfo && (
        <div className="center" style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,.4)", zIndex: 50, padding: 24 }} onClick={() => setResetInfo(null)}>
          <div className="card col gap-12" style={{ width: "min(380px, 100%)", padding: 24 }} onClick={(e) => e.stopPropagation()}>
            <div style={{ fontSize: 16, fontWeight: 800 }}>密碼已重置</div>
            <div className="muted" style={{ fontSize: 12.5 }}>請把下面的臨時密碼當面/線下告知 <b>{resetInfo.name}</b>（@{resetInfo.username}）。此密碼只顯示這一次,該用戶登入後應立即修改。</div>
            <div className="num" style={{ fontSize: 22, fontWeight: 800, letterSpacing: 1, textAlign: "center", padding: "14px 0", background: "var(--surface-2)", borderRadius: 12 }}>{resetInfo.password}</div>
            <button className="btn btn-primary" onClick={() => setResetInfo(null)} style={{ height: 40 }}>我已記下,關閉</button>
          </div>
        </div>
      )}
    </div>
  );
};

const topoJson = (res, fallback) => res.json().catch(() => ({})).then((data) => {
  if (!res.ok) throw new Error(data.error || fallback || `HTTP ${res.status}`);
  return data;
});

const PermissionTopologyPanel = () => {
  const [data, setData] = useStatePerm(null);
  const [loading, setLoading] = useStatePerm(true);
  const [error, setError] = useStatePerm("");
  const [busy, setBusy] = useStatePerm("");
  const [levelDraft, setLevelDraft] = useStatePerm({ user_id: "", level: 3, title: "" });
  const [shareDraft, setShareDraft] = useStatePerm({ grantee: "", permission_key: "", expires_at: "", reason: "" });
  const canvasRef = React.useRef(null);

  const load = () => {
    setLoading(true);
    setError("");
    window.authFetch("/api/permissions/topology")
      .then((res) => topoJson(res, "權限拓撲載入失敗"))
      .then((payload) => {
        setData(payload);
        const first = (payload.users || [])[0];
        const perm = ((payload.permissions || []).find((p) => !(payload.protected_permissions || []).includes(p.key)) || {}).key || "";
        if (first) setLevelDraft((d) => ({ ...d, user_id: d.user_id || first.id, level: d.level || first.topology_level || 1 }));
        setShareDraft((d) => ({ ...d, permission_key: d.permission_key || perm }));
      })
      .catch((err) => setError(err.message || String(err)))
      .finally(() => setLoading(false));
  };

  useEffectPerm(() => { load(); }, []);

  React.useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !data) return undefined;
    const draw = () => {
      const box = canvas.parentElement.getBoundingClientRect();
      const dpr = window.devicePixelRatio || 1;
      const w = Math.max(760, Math.floor(box.width));
      const h = Math.max(430, Math.floor(box.height || 430));
      canvas.width = Math.floor(w * dpr);
      canvas.height = Math.floor(h * dpr);
      canvas.style.width = `${w}px`;
      canvas.style.height = `${h}px`;
      const ctx = canvas.getContext("2d");
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.clearRect(0, 0, w, h);
      const grad = ctx.createLinearGradient(0, 0, w, h);
      grad.addColorStop(0, "#f8fafc");
      grad.addColorStop(0.5, "#eef6f4");
      grad.addColorStop(1, "#f7f3ea");
      ctx.fillStyle = grad;
      ctx.fillRect(0, 0, w, h);
      ctx.globalAlpha = 0.72;
      ctx.strokeStyle = "rgba(14,26,43,.055)";
      for (let x = 40; x < w; x += 72) {
        ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, h); ctx.stroke();
      }
      for (let y = 36; y < h; y += 64) {
        ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke();
      }
      ctx.globalAlpha = 1;

      const roles = (data.nodes || []).filter((n) => n.type === "role").sort((a, b) => (b.level || 0) - (a.level || 0));
      const users = (data.nodes || []).filter((n) => n.type === "user").sort((a, b) => (b.level || 0) - (a.level || 0));
      const pos = {};
      const roleX = Math.max(130, w * 0.18);
      const minY = 62;
      const spanY = h - 124;
      roles.forEach((n, i) => {
        pos[n.id] = { x: roleX, y: minY + (spanY * (i + 0.5)) / Math.max(roles.length, 1), r: 32 };
      });
      users.forEach((n, i) => {
        const level = Math.max(1, Math.min(10, Number(n.level || 1)));
        const band = (10 - level) / 9;
        const x = w * 0.42 + band * w * 0.43;
        const y = minY + (spanY * (i + 0.5)) / Math.max(users.length, 1);
        pos[n.id] = { x, y, r: 26 };
      });

      (data.edges || []).forEach((e) => {
        const a = pos[e.from], b = pos[e.to];
        if (!a || !b) return;
        ctx.beginPath();
        ctx.moveTo(a.x, a.y);
        const cx1 = a.x + (b.x - a.x) * 0.42;
        const cx2 = a.x + (b.x - a.x) * 0.72;
        ctx.bezierCurveTo(cx1, a.y, cx2, b.y, b.x, b.y);
        ctx.lineWidth = e.type === "delegation" ? 2.4 : 1.35;
        ctx.strokeStyle = e.type === "delegation" ? "rgba(245,158,11,.72)" : "rgba(27,107,255,.2)";
        ctx.stroke();
        if (e.type === "delegation") {
          const mx = (a.x + b.x) / 2, my = (a.y + b.y) / 2;
          ctx.fillStyle = "rgba(245,158,11,.13)";
          ctx.beginPath(); ctx.arc(mx, my, 7, 0, Math.PI * 2); ctx.fill();
        }
      });

      const drawNode = (n) => {
        const p = pos[n.id];
        if (!p) return;
        const isRole = n.type === "role";
        ctx.save();
        ctx.shadowColor = "rgba(14,26,43,.16)";
        ctx.shadowBlur = 18;
        ctx.shadowOffsetY = 8;
        ctx.fillStyle = isRole ? (n.color || "#1B6BFF") : "#ffffff";
        ctx.strokeStyle = isRole ? "rgba(255,255,255,.75)" : "rgba(14,26,43,.08)";
        ctx.lineWidth = 1.2;
        ctx.beginPath(); ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2); ctx.fill(); ctx.stroke();
        ctx.restore();
        ctx.fillStyle = isRole ? "#fff" : "#0E1A2B";
        ctx.font = `700 ${isRole ? 12 : 11}px ${getComputedStyle(document.body).fontFamily}`;
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        const label = String(n.label || "").slice(0, isRole ? 5 : 4);
        ctx.fillText(label, p.x, p.y - (isRole ? 4 : 3));
        ctx.fillStyle = isRole ? "rgba(255,255,255,.78)" : "rgba(60,74,94,.72)";
        ctx.font = "600 10px system-ui";
        ctx.fillText(`L${n.level || n.role_level || 1}`, p.x, p.y + 12);
      };
      roles.forEach(drawNode);
      users.forEach(drawNode);
      ctx.fillStyle = "rgba(14,26,43,.58)";
      ctx.font = "700 12px system-ui";
      ctx.textAlign = "left";
      ctx.fillText("Roles", 28, 32);
      ctx.fillText("Users by topology level", w * 0.4, 32);
    };
    draw();
    const ro = new ResizeObserver(draw);
    ro.observe(canvas.parentElement);
    return () => ro.disconnect();
  }, [data]);

  const post = (path, body, label) => {
    setBusy(label);
    setError("");
    return window.authFetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body || {}),
    })
      .then((res) => topoJson(res, "操作失敗"))
      .then((payload) => setData(payload))
      .catch((err) => setError(err.message || String(err)))
      .finally(() => setBusy(""));
  };

  const users = (data && data.users) || [];
  const delegations = (data && data.delegations) || [];
  const protectedSet = new Set((data && data.protected_permissions) || []);
  const currentPerms = new Set(((window.CURRENT_USER || {}).permissions) || []);
  const shareable = ((data && data.permissions) || []).filter((p) => !protectedSet.has(p.key) && (!currentPerms.size || currentPerms.has(p.key)));
  const actor = (data && data.actor) || {};

  if (loading) return <div className="muted" style={{ fontSize: 13 }}>權限拓撲載入中…</div>;

  return (
    <div className="perm-topology col gap-16">
      {error && <div className="card" style={{ padding: 12, color: "var(--danger)", fontWeight: 700, fontSize: 13 }}>{error}</div>}
      <div className="perm-topology-head">
        <div className="col gap-6">
          <span className="eyebrow">PERMISSION GRAPH</span>
          <div className="perm-topology-title">權限拓撲</div>
          <div className="muted" style={{ fontSize: 13 }}>角色級別、用戶職級、權限分享與審計來源統一在同一張圖內。</div>
        </div>
        <div className="perm-topology-kpis">
          <div><b>{(data.summary || {}).roles || 0}</b><span>角色</span></div>
          <div><b>{(data.summary || {}).users || 0}</b><span>用戶</span></div>
          <div><b>{(data.summary || {}).delegations || 0}</b><span>分享</span></div>
          <button className="btn btn-sm" onClick={load}><Icon name="refresh" size={14}/>刷新</button>
        </div>
      </div>

      <div className="perm-topology-canvas">
        <canvas ref={canvasRef}/>
      </div>

      <div className="perm-topology-workbench">
        <section className="perm-topology-panel">
          <div className="row spread">
            <div>
              <div className="sec-title">職級視圖</div>
              <div className="muted" style={{ fontSize: 12 }}>拓撲級別不提升角色權限。</div>
            </div>
            <span className="badge badge-info">L{actor.level || 0}</span>
          </div>
          <select className="input" value={levelDraft.user_id} onChange={(e) => setLevelDraft({ ...levelDraft, user_id: e.target.value })}>
            {users.map((u) => <option key={u.id} value={u.id}>{u.display_name || u.username} · L{u.topology_level}</option>)}
          </select>
          <div className="row gap-8">
            <input className="input" type="number" min="1" max="10" value={levelDraft.level} onChange={(e) => setLevelDraft({ ...levelDraft, level: e.target.value })}/>
            <input className="input" placeholder="職位標籤" value={levelDraft.title} onChange={(e) => setLevelDraft({ ...levelDraft, title: e.target.value })}/>
          </div>
          <button className="btn btn-primary" disabled={!!busy || !levelDraft.user_id} onClick={() => post(`/api/permissions/topology/users/${levelDraft.user_id}/level`, { level: levelDraft.level, title: levelDraft.title }, "level")}>
            <Icon name="check" size={14}/>保存職級
          </button>
        </section>

        <section className="perm-topology-panel">
          <div>
            <div className="sec-title">權限分享</div>
            <div className="muted" style={{ fontSize: 12 }}>只能分享自己持有且非核心控制類的權限。</div>
          </div>
          <select className="input" value={shareDraft.grantee} onChange={(e) => setShareDraft({ ...shareDraft, grantee: e.target.value })}>
            <option value="">選擇被授權用戶</option>
            {users.filter((u) => u.id !== actor.id).map((u) => <option key={u.id} value={u.id}>{u.display_name || u.username} · L{u.topology_level}</option>)}
          </select>
          <select className="input" value={shareDraft.permission_key} onChange={(e) => setShareDraft({ ...shareDraft, permission_key: e.target.value })}>
            <option value="">選擇權限</option>
            {shareable.map((p) => <option key={p.key} value={p.key}>{p.key}</option>)}
          </select>
          <div className="row gap-8">
            <input className="input" type="date" value={shareDraft.expires_at} onChange={(e) => setShareDraft({ ...shareDraft, expires_at: e.target.value })}/>
            <input className="input" placeholder="原因" value={shareDraft.reason} onChange={(e) => setShareDraft({ ...shareDraft, reason: e.target.value })}/>
          </div>
          <button className="btn btn-primary" disabled={!!busy || !actor.can_delegate || !shareDraft.grantee || !shareDraft.permission_key} onClick={() => post("/api/permissions/share", shareDraft, "share")}>
            <Icon name="link" size={14}/>分享權限
          </button>
        </section>

        <section className="perm-topology-panel perm-topology-list">
          <div className="row spread">
            <div>
              <div className="sec-title">分享記錄</div>
              <div className="muted" style={{ fontSize: 12 }}>審計日誌會標記委託權限來源。</div>
            </div>
            <span className="badge badge-gray">{delegations.length}</span>
          </div>
          <div className="col gap-8">
            {delegations.length === 0 && <div className="muted" style={{ fontSize: 12 }}>暫無有效分享</div>}
            {delegations.slice(0, 8).map((d) => (
              <div key={d.id} className="perm-delegation-row">
                <div className="col gap-2" style={{ minWidth: 0 }}>
                  <b>{d.permission_key}</b>
                  <span className="muted">{d.grantor_name || d.grantor_username} → {d.grantee_name || d.grantee_username}{d.expires_at ? ` · 至 ${d.expires_at.slice(0, 10)}` : ""}</span>
                </div>
                <button className="btn btn-sm" disabled={!!busy} onClick={() => post(`/api/permissions/share/${d.id}/revoke`, {}, "revoke")}>撤回</button>
              </div>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
};

const BulkImportModal = ({ roles, onClose, onDone }) => {
  const [file, setFile] = useStatePerm(null);
  const [defaultRoleId, setDefaultRoleId] = useStatePerm("");
  const [busy, setBusy] = useStatePerm(false);
  const [error, setError] = useStatePerm("");
  const [result, setResult] = useStatePerm(null);

  const downloadTemplate = () => {
    window.authFetch("/api/users/import-template")
      .then((res) => { if (!res.ok) throw new Error("模板下載失敗"); return res.blob(); })
      .then((blob) => {
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url; a.download = "用戶批量導入模板.xlsx";
        document.body.appendChild(a); a.click(); document.body.removeChild(a);
        URL.revokeObjectURL(url);
      })
      .catch((e) => setError(e.message || String(e)));
  };

  const submit = () => {
    if (busy || !file) { if (!file) setError("請先選擇文件"); return; }
    setBusy(true); setError(""); setResult(null);
    const fd = new FormData();
    fd.append("file", file);
    if (defaultRoleId) fd.append("default_role_id", defaultRoleId);
    // 不手動設 Content-Type,讓瀏覽器帶 multipart boundary
    window.authFetch("/api/users/bulk-import", { method: "POST", body: fd })
      .then((res) => res.json().then((d) => ({ ok: res.ok, d })))
      .then(({ ok, d }) => { if (!ok) throw new Error(d.error || "導入失敗"); setResult(d); onDone && onDone(); })
      .catch((e) => setError(e.message || String(e)))
      .finally(() => setBusy(false));
  };

  const created = (result && result.created) || [];
  const skipped = (result && result.skipped) || [];
  const genList = created.filter((c) => c.generated);

  return (
    <div className="center" style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,.4)", zIndex: 50, padding: 24 }} onClick={onClose}>
      <div className="card col gap-14" style={{ width: "min(620px, 100%)", padding: 24, maxHeight: "88vh", overflowY: "auto" }} onClick={(e) => e.stopPropagation()}>
        <div className="row spread">
          <div className="col gap-2"><div style={{ fontSize: 17, fontWeight: 800 }}>批量導入用戶</div>
            <div className="muted" style={{ fontSize: 12 }}>上傳名單(.csv / .xls / .xlsx),AI 自動識別帳號、密碼、角色並建立帳號</div></div>
          <button onClick={onClose} style={{ background: "none", border: "none", cursor: "pointer" }}><Icon name="x" size={18} color="var(--ink-3)"/></button>
        </div>

        {!result && (
          <>
            <div className="col gap-8" style={{ padding: 14, borderRadius: 12, border: "1px dashed var(--line)", background: "var(--surface-2)" }}>
              <input type="file" accept=".csv,.txt,.xls,.xlsx" onChange={(e) => { setFile(e.target.files[0] || null); setError(""); }}/>
              {file && <span className="num muted" style={{ fontSize: 12 }}>已選:{file.name}</span>}
              <div className="muted" style={{ fontSize: 11.5, lineHeight: 1.6 }}>表頭可任意(帳號/姓名/密碼/角色,中英皆可)。無密碼者自動生成臨時密碼;帳號已存在或格式無效會自動跳過。</div>
              <button className="btn btn-sm" style={{ alignSelf: "flex-start" }} onClick={downloadTemplate}><Icon name="outbound" size={14}/>下載標準模板 (.xlsx)</button>
            </div>
            <label className="col gap-6" style={{ fontSize: 12.5, fontWeight: 700 }}>默認角色(文件未指定角色時使用)
              <select className="input" value={defaultRoleId} onChange={(e) => setDefaultRoleId(e.target.value)}>
                <option value="">自動(普通員工)</option>
                {(roles || []).map((r) => <option key={r.id} value={r.id}>{r.role_name}</option>)}
              </select>
            </label>
            {error && <div style={{ color: "var(--danger)", fontSize: 13, fontWeight: 700 }}>⚠ {error}</div>}
            <button className="btn btn-primary" disabled={busy || !file} onClick={submit} style={{ height: 42 }}>{busy ? "識別並建立中…" : "開始導入"}</button>
          </>
        )}

        {result && (
          <>
            <div className="row gap-10">
              <span className="badge badge-ok" style={{ height: 24 }}>成功建立 {result.created_count}</span>
              <span className="badge badge-gray" style={{ height: 24 }}>跳過 {result.skipped_count}</span>
            </div>
            {genList.length > 0 && (
              <div className="col gap-8" style={{ padding: 12, borderRadius: 10, background: "var(--ok-soft)", border: "1px solid rgba(16,185,129,.2)" }}>
                <div style={{ fontSize: 12.5, fontWeight: 700 }}>以下帳號由系統生成臨時密碼(只顯示一次,請複製通知本人):</div>
                <div className="card" style={{ padding: 0, overflow: "hidden", border: "1px solid var(--line)" }}>
                  <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12.5 }}>
                    <thead><tr style={{ background: "var(--surface)", textAlign: "left" }}>{["帳號", "姓名", "角色", "臨時密碼"].map((h) => <th key={h} style={{ padding: "8px 12px", fontWeight: 700, fontSize: 11.5 }}>{h}</th>)}</tr></thead>
                    <tbody>{genList.map((c, i) => (
                      <tr key={i} style={{ borderTop: "1px solid var(--line)" }}>
                        <td className="num" style={{ padding: "8px 12px" }}>{c.username}</td>
                        <td style={{ padding: "8px 12px" }}>{c.display_name}</td>
                        <td style={{ padding: "8px 12px" }}>{c.role}</td>
                        <td className="num" style={{ padding: "8px 12px", fontWeight: 800, color: "var(--blue)" }}>{c.password}</td>
                      </tr>
                    ))}</tbody>
                  </table>
                </div>
              </div>
            )}
            {created.filter((c) => !c.generated).length > 0 && (
              <div className="muted" style={{ fontSize: 12.5 }}>另有 {created.filter((c) => !c.generated).length} 個帳號使用文件中自帶的密碼建立。</div>
            )}
            {skipped.length > 0 && (
              <div className="col gap-4">
                <div style={{ fontSize: 12.5, fontWeight: 700 }}>跳過明細:</div>
                {skipped.map((s, i) => <div key={i} className="muted" style={{ fontSize: 12 }}>· <span className="num">{s.username}</span> — {s.reason}</div>)}
              </div>
            )}
            <button className="btn btn-primary" onClick={onClose} style={{ height: 40 }}>完成</button>
          </>
        )}
      </div>
    </div>
  );
};

window.PagePerms = PagePerms;
