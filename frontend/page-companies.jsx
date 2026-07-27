/* ============================================================
   公司管理 — 主應用內完成公司開通、租戶 DB 初始化、申請審批與成員維護
   ============================================================ */
const { useState: useStateCo, useEffect: useEffectCo } = React;

const coJson = async (path, options) => {
  const res = await window.authFetch(path, options);
  const data = await res.json().catch(() => ({}));
  return { ok: res.ok, status: res.status, data };
};

const CO_TEMPLATES_FALLBACK = [{ key: "generic_warehouse", name: "通用倉儲" }, { key: "power_grid_uhv", name: "超高壓電網" }];
const SIGNUP_BADGE_CO = { pending: "badge-warn", approved: "badge-ok", rejected: "badge-danger" };
const SIGNUP_LABEL_CO = { pending: "待審批", approved: "已開通", rejected: "已駁回" };

const CompanyField = ({ label, type = "text", value, onChange, placeholder }) => (
  <label className="col gap-6" style={{ fontSize: 12.5, fontWeight: 700 }}>{label}
    <input className="input" type={type} value={value} onChange={onChange} placeholder={placeholder}/>
  </label>
);

const CompanyCreateModal = ({ onClose, onCreated }) => {
  const [templates, setTemplates] = useStateCo(CO_TEMPLATES_FALLBACK);
  const [form, setForm] = useStateCo({
    company_name: "",
    slug: "",
    industry_template: "generic_warehouse",
    admin_username: "",
    admin_display_name: "",
    admin_password: "",
  });
  const [busy, setBusy] = useStateCo(false);
  const [err, setErr] = useStateCo("");
  const [result, setResult] = useStateCo(null);
  const up = (key) => (e) => setForm({ ...form, [key]: key === "slug" ? e.target.value.toLowerCase() : e.target.value });

  useEffectCo(() => {
    coJson("/api/platform/templates")
      .then(({ data }) => {
        const list = data.templates || CO_TEMPLATES_FALLBACK;
        setTemplates(list);
        if (list[0]) setForm((prev) => ({ ...prev, industry_template: prev.industry_template || list[0].key }));
      })
      .catch(() => {});
  }, []);

  const submit = (e) => {
    e.preventDefault();
    if (busy) return;
    setBusy(true); setErr(""); setResult(null);
    coJson("/api/platform/tenants", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(form),
    })
      .then(({ ok, data }) => {
        if (!ok) throw new Error(data.error || "開通失敗");
        setResult(data);
        onCreated && onCreated();
      })
      .catch((e2) => setErr(e2.message || String(e2)))
      .finally(() => setBusy(false));
  };

  return (
    <div className="center" style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,.4)", zIndex: 50, padding: 24 }} onClick={onClose}>
      <form className="card col gap-14" style={{ width: "min(520px, 100%)", padding: 24, maxHeight: "88vh", overflowY: "auto" }} onClick={(e) => e.stopPropagation()} onSubmit={submit}>
        <div className="row spread">
          <div className="col gap-3">
            <div style={{ fontSize: 17, fontWeight: 800 }}>新增公司</div>
            <div className="muted" style={{ fontSize: 12.5 }}>立即創建租戶資料庫、初始化表結構、建立初始系統管理員。</div>
          </div>
          <button type="button" onClick={onClose} style={{ background: "none", border: "none", cursor: "pointer" }}><Icon name="x" size={18} color="var(--ink-3)"/></button>
        </div>
        {result ? (
          <>
            <div style={{ color: "var(--ok)", fontSize: 13, fontWeight: 700 }}>{result.message || "公司已開通"}</div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(170px, 1fr))", gap: 10, fontSize: 12.5 }}>
              <div className="col gap-3"><span className="muted">企業代碼</span><span className="num">/{result.slug}</span></div>
              <div className="col gap-3"><span className="muted">資料庫</span><span className="num">{result.db_path}</span></div>
              <div className="col gap-3"><span className="muted">管理員帳號</span><span className="num">@{result.admin_username}</span></div>
              <div className="col gap-3"><span className="muted">密碼狀態</span><span>{result.temp_password ? "已生成臨時密碼" : "沿用既有密碼或手動填寫密碼"}</span></div>
            </div>
            {result.temp_password && (
              <div className="col gap-8" style={{ padding: 14, borderRadius: 8, background: "var(--ok-soft)", border: "1px solid rgba(16,185,129,.22)" }}>
                <div style={{ fontSize: 12.5, fontWeight: 700 }}>臨時密碼只顯示一次，請告知初始管理員。</div>
                <div className="num" style={{ fontSize: 22, fontWeight: 800, textAlign: "center", padding: "10px 0", background: "var(--surface)", borderRadius: 8 }}>{result.temp_password}</div>
              </div>
            )}
            <button type="button" className="btn btn-primary" onClick={onClose} style={{ height: 40 }}>完成</button>
          </>
        ) : (
          <>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(190px, 1fr))", gap: 10 }}>
              <CompanyField label="公司名稱" value={form.company_name} onChange={up("company_name")} placeholder="例如:ACME 倉儲"/>
              <CompanyField label="企業代碼" value={form.slug} onChange={up("slug")} placeholder="acme"/>
            </div>
            <label className="col gap-6" style={{ fontSize: 12.5, fontWeight: 700 }}>行業模板
              <select className="input" value={form.industry_template} onChange={up("industry_template")}>
                {templates.map((t) => <option key={t.key} value={t.key}>{t.name}</option>)}
              </select>
            </label>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(190px, 1fr))", gap: 10 }}>
              <CompanyField label="初始管理員帳號" value={form.admin_username} onChange={up("admin_username")} placeholder="帳號或郵箱"/>
              <CompanyField label="顯示名稱" value={form.admin_display_name} onChange={up("admin_display_name")} placeholder="姓名"/>
            </div>
            <CompanyField label="初始密碼（可留空自動生成）" type="password" value={form.admin_password} onChange={up("admin_password")} placeholder="至少 8 位"/>
            {err && <div style={{ color: "var(--danger)", fontSize: 13, fontWeight: 700 }}>⚠ {err}</div>}
            <button className="btn btn-primary" type="submit" disabled={busy} style={{ height: 40 }}>{busy ? "開通中…" : "創建公司與資料庫"}</button>
          </>
        )}
      </form>
    </div>
  );
};

const CompanyManageModal = ({ slug, onClose, onChanged }) => {
  const [data, setData] = useStateCo(null);
  const [templates, setTemplates] = useStateCo(CO_TEMPLATES_FALLBACK);
  const [form, setForm] = useStateCo({ name: "", industry_template: "" });
  const [busy, setBusy] = useStateCo(false);
  const [err, setErr] = useStateCo("");
  const [savedMsg, setSavedMsg] = useStateCo("");
  const [resetInfo, setResetInfo] = useStateCo(null);

  const reload = () => {
    coJson(`/api/platform/tenants/${slug}/detail`).then(({ ok, data }) => {
      if (!ok) { setErr(data.error || "載入失敗"); return; }
      setData(data);
      setForm({ name: data.tenant.name, industry_template: data.tenant.industry_template || "generic_warehouse" });
    });
  };
  useEffectCo(() => {
    reload();
    coJson("/api/platform/templates").then(({ data }) => data.templates && setTemplates(data.templates)).catch(() => {});
  }, [slug]);

  const saveEdit = () => {
    const templateChanged = !!(data && data.tenant && form.industry_template !== data.tenant.industry_template);
    if (templateChanged && !window.confirm("切換行業模板會同步新部門與崗位,並封存未使用的舊模板項。確認繼續?")) return;
    setBusy(true); setErr(""); setSavedMsg("");
    coJson(`/api/platform/tenants/${slug}/edit`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ ...form, confirm_template_change: templateChanged }) })
      .then(({ ok, data }) => { if (!ok) throw new Error(data.error || "保存失敗"); setSavedMsg("已保存"); reload(); onChanged && onChanged(); })
      .catch((e) => setErr(e.message || String(e))).finally(() => setBusy(false));
  };
  const resetMember = (m) => {
    if (!window.confirm(`重置 ${m.display_name}(@${m.username})的密碼?其登入會立即失效。`)) return;
    setBusy(true); setErr("");
    coJson(`/api/platform/tenants/${slug}/members/${m.global_user_id}/reset-password`, { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" })
      .then(({ ok, data }) => { if (!ok) throw new Error(data.error || "重置失敗"); setResetInfo({ name: m.display_name, username: m.username, password: data.temp_password }); })
      .catch((e) => setErr(e.message || String(e))).finally(() => setBusy(false));
  };

  const st = data && data.stats;
  return (
    <div className="center" style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,.4)", zIndex: 50, padding: 24 }} onClick={onClose}>
      <div className="card col gap-16" style={{ width: "min(720px, 100%)", padding: 24, maxHeight: "88vh", overflowY: "auto" }} onClick={(e) => e.stopPropagation()}>
        <div className="row spread"><div style={{ fontSize: 17, fontWeight: 800 }}>公司管理 · {data ? data.tenant.name : slug}</div>
          <button onClick={onClose} style={{ background: "none", border: "none", cursor: "pointer" }}><Icon name="x" size={18} color="var(--ink-3)"/></button></div>
        {err && <div style={{ color: "var(--danger)", fontSize: 13, fontWeight: 700 }}>⚠ {err}</div>}
        {!data ? <div className="muted" style={{ fontSize: 13 }}>載入中…</div> : (
          <>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(120px, 1fr))", gap: 10 }}>
              {[["成員", st.members], ["用戶", st.users], ["物資", st.items], ["倉庫", st.warehouses]].map(([k, v]) => (
                <div key={k} className="col gap-2" style={{ padding: 12, borderRadius: 8, background: "var(--surface-2)" }}>
                  <span className="muted" style={{ fontSize: 11 }}>{k}</span><span className="num" style={{ fontSize: 22, fontWeight: 800 }}>{v}</span>
                </div>
              ))}
            </div>
            <div className="col gap-8">
              <div style={{ fontSize: 13.5, fontWeight: 800 }}>編輯</div>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(190px, 1fr))", gap: 10 }}>
                <label className="col gap-6" style={{ fontSize: 12.5, fontWeight: 700 }}>公司名稱
                  <input className="input" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })}/></label>
                <label className="col gap-6" style={{ fontSize: 12.5, fontWeight: 700 }}>行業模板
                  <select className="input" value={form.industry_template} onChange={(e) => setForm({ ...form, industry_template: e.target.value })}>
                    {templates.map((t) => <option key={t.key} value={t.key}>{t.name}</option>)}
                  </select></label>
              </div>
              <div className="row gap-8" style={{ alignItems: "center" }}>
                <button className="btn btn-primary btn-sm" disabled={busy} onClick={saveEdit}>保存修改</button>
                {savedMsg && <span style={{ color: "var(--ok)", fontSize: 12.5, fontWeight: 700 }}>{savedMsg}</span>}
                <span className="num muted" style={{ fontSize: 11 }}>代碼 /{data.tenant.slug} · 狀態 {data.tenant.status}</span>
              </div>
            </div>
            <div className="col gap-8">
              <div style={{ fontSize: 13.5, fontWeight: 800 }}>成員({data.members.length})</div>
              <div style={{ padding: 0, overflow: "hidden", border: "1px solid var(--line)", borderRadius: 8 }}>
                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12.5 }}>
                  <thead><tr style={{ background: "var(--surface-2)", textAlign: "left" }}>{["成員", "帳號", "角色", "狀態", "操作"].map((h) => <th key={h} style={{ padding: "10px 14px", fontWeight: 700, fontSize: 11.5 }}>{h}</th>)}</tr></thead>
                  <tbody>
                    {data.members.map((m) => (
                      <tr key={m.global_user_id} style={{ borderTop: "1px solid var(--line)" }}>
                        <td style={{ padding: "10px 14px", fontWeight: 700 }}>{m.display_name}</td>
                        <td className="num muted" style={{ padding: "10px 14px" }}>@{m.username}</td>
                        <td style={{ padding: "10px 14px" }}>{m.role || "—"}</td>
                        <td style={{ padding: "10px 14px" }}><span className={`badge ${m.status === "active" ? "badge-ok" : "badge-gray"}`} style={{ height: 19 }}>{m.status}</span></td>
                        <td style={{ padding: "10px 14px" }}><button className="btn btn-sm" disabled={busy} onClick={() => resetMember(m)}>重置密碼</button></td>
                      </tr>
                    ))}
                    {data.members.length === 0 && <tr><td colSpan={5} className="muted" style={{ padding: 14, textAlign: "center" }}>暫無成員</td></tr>}
                  </tbody>
                </table>
              </div>
            </div>
          </>
        )}
        {resetInfo && (
          <div className="col gap-8" style={{ padding: 14, borderRadius: 8, background: "var(--ok-soft)", border: "1px solid rgba(16,185,129,.2)" }}>
            <div style={{ fontSize: 13, fontWeight: 700 }}>已重置 {resetInfo.name}(@{resetInfo.username})的密碼,臨時密碼(只顯示一次):</div>
            <div className="num" style={{ fontSize: 20, fontWeight: 800, letterSpacing: 1, textAlign: "center", padding: "10px 0", background: "var(--surface)", borderRadius: 8 }}>{resetInfo.password}</div>
          </div>
        )}
      </div>
    </div>
  );
};

const CompanySignupPanel = ({ signups, busyId, note, setNote, onDecide }) => (
  <div className="col gap-12">
    {signups.length === 0 && <div className="muted" style={{ padding: 28, textAlign: "center", fontSize: 13, border: "1px dashed var(--line)", borderRadius: 8 }}>暫無待審批公司申請</div>}
    {signups.map((s) => (
      <div key={s.id} className="card" style={{ padding: 18 }}>
        <div className="row spread" style={{ marginBottom: 12 }}>
          <div style={{ fontSize: 15, fontWeight: 800 }}>{s.company_name} <span className="num muted" style={{ fontSize: 12 }}>/{s.slug}</span></div>
          <span className={`badge ${SIGNUP_BADGE_CO[s.status] || "badge-gray"}`} style={{ height: 22 }}>{SIGNUP_LABEL_CO[s.status] || s.status}</span>
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: 10, marginBottom: 12, fontSize: 12.5 }}>
          {[["行業模板", s.template_name], ["申請人/管理員", s.admin_display_name], ["帳號", s.admin_username], ["聯繫方式", s.contact], ["申請時間", s.created_at], ["備註", s.reason]].map(([k, v], i) => (
            <div key={i} className="col gap-3"><span className="muted" style={{ fontSize: 11 }}>{k}</span><span>{v || "—"}</span></div>
          ))}
        </div>
        <div className="col gap-10" style={{ borderTop: "1px solid var(--line)", paddingTop: 12 }}>
          <input className="input" placeholder="審批備註 / 駁回理由(可選)" value={note[s.id] || ""} onChange={(e) => setNote({ ...note, [s.id]: e.target.value })}/>
          <div className="row gap-8">
            <button className="btn btn-primary btn-sm" disabled={busyId === s.id} onClick={() => onDecide(s, "approve")}>通過並開通公司</button>
            <button className="btn btn-sm" disabled={busyId === s.id} style={{ color: "var(--danger)" }} onClick={() => onDecide(s, "reject")}>駁回</button>
          </div>
        </div>
      </div>
    ))}
  </div>
);

const PageCompanies = () => {
  const [tab, setTab] = useStateCo("tenants");
  const [tenants, setTenants] = useStateCo([]);
  const [signups, setSignups] = useStateCo([]);
  const [pendingCount, setPendingCount] = useStateCo(0);
  const [loading, setLoading] = useStateCo(true);
  const [forbidden, setForbidden] = useStateCo(false);
  const [error, setError] = useStateCo("");
  const [busyId, setBusyId] = useStateCo(null);
  const [note, setNote] = useStateCo({});
  const [manageSlug, setManageSlug] = useStateCo(null);
  const [showCreate, setShowCreate] = useStateCo(false);

  const load = () => {
    setLoading(true); setError("");
    Promise.all([coJson("/api/platform/tenants"), coJson("/api/platform/signups?status=pending")])
      .then(([tenantRes, signupRes]) => {
        if ([tenantRes.status, signupRes.status].includes(403) || [tenantRes.status, signupRes.status].includes(401)) {
          setForbidden(true);
          return;
        }
        if (!tenantRes.ok) throw new Error(tenantRes.data.error || "公司列表載入失敗");
        if (!signupRes.ok) throw new Error(signupRes.data.error || "申請列表載入失敗");
        setTenants(tenantRes.data.tenants || []);
        setSignups(signupRes.data.signups || []);
        setPendingCount(signupRes.data.pending_count || 0);
      })
      .catch((e) => setError(e.message || String(e)))
      .finally(() => setLoading(false));
  };
  useEffectCo(() => { load(); }, []);

  const setStatus = (slug, status) => {
    if (busyId) return;
    const action = status === "suspended" ? "suspended" : "active";
    setBusyId(slug); setError("");
    coJson(`/api/platform/tenants/${slug}/status/${action}`, { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" })
      .then(({ ok, data }) => { if (!ok) throw new Error(data.error || "操作失敗"); load(); })
      .catch((e) => setError(e.message || String(e))).finally(() => setBusyId(null));
  };

  const decideSignup = (s, action) => {
    if (busyId) return;
    setBusyId(s.id); setError("");
    coJson(`/api/platform/signups/${s.id}/${action}`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ note: note[s.id] || "" }) })
      .then(({ ok, data }) => { if (!ok) throw new Error(data.error || "操作失敗"); load(); })
      .catch((e) => setError(e.message || String(e))).finally(() => setBusyId(null));
  };

  const Tab = ({ id, label, count }) => (
    <button className="btn btn-sm" onClick={() => setTab(id)} style={{ background: tab === id ? "var(--blue)" : "var(--surface-2)", color: tab === id ? "#fff" : "var(--ink-2)" }}>
      {label}{count ? ` (${count})` : ""}
    </button>
  );

  if (forbidden) {
    return (
      <div className="col gap-18">
        <PageHead title="公司管理" sub="跨公司管理"/>
        <div className="card col center" style={{ padding: 40, gap: 12 }}>
          <Icon name="layers" size={32} color="var(--ink-4)"/>
          <div style={{ fontWeight: 700 }}>當前帳號沒有平台管理權限</div>
          <div className="muted" style={{ fontSize: 13 }}>只有系統管理員或平台運營員能管理所有公司。</div>
        </div>
      </div>
    );
  }

  return (
    <div className="col gap-18">
      <PageHead title="公司管理" sub="公司開通 · 租戶資料庫 · 入駐審批 · 成員維護"
        actions={<div className="row gap-8"><button className="btn btn-primary btn-sm" onClick={() => setShowCreate(true)}><Icon name="plus" size={14}/>新增公司</button><button className="btn btn-sm" onClick={load}><Icon name="refresh" size={14}/>刷新</button></div>}/>
      <div className="row gap-8">
        <Tab id="tenants" label="公司列表" count={tenants.length}/>
        <Tab id="signups" label="公司申請" count={pendingCount}/>
      </div>
      {error && <div className="card" style={{ padding: 12, color: "var(--danger)", fontWeight: 700, fontSize: 13 }}>{error}</div>}
      {loading && <div className="muted" style={{ fontSize: 13 }}>載入中…</div>}
      {!loading && tab === "signups" && (
        <CompanySignupPanel signups={signups} busyId={busyId} note={note} setNote={setNote} onDecide={decideSignup}/>
      )}
      {!loading && tab === "tenants" && (
        <div className="card fade-up" style={{ padding: 0, overflow: "hidden" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
            <thead><tr style={{ background: "var(--surface-2)", textAlign: "left" }}>
              {["公司", "企業代碼", "行業模板", "成員", "狀態", "操作"].map((h) => <th key={h} style={{ padding: "12px 16px", fontWeight: 700, fontSize: 12 }}>{h}</th>)}
            </tr></thead>
            <tbody>
              {tenants.map((t) => (
                <tr key={t.id} style={{ borderTop: "1px solid var(--line)" }}>
                  <td style={{ padding: "12px 16px", fontWeight: 700 }}>{t.name}</td>
                  <td className="num muted" style={{ padding: "12px 16px" }}>/{t.slug}</td>
                  <td style={{ padding: "12px 16px" }}>{t.template_name || t.industry_template || "—"}</td>
                  <td className="num" style={{ padding: "12px 16px" }}>{t.member_count != null ? t.member_count : "—"}</td>
                  <td style={{ padding: "12px 16px" }}><span className={`badge ${t.status === "active" ? "badge-ok" : "badge-danger"}`} style={{ height: 20 }}>{t.status === "active" ? "啟用" : "停用"}</span></td>
                  <td style={{ padding: "12px 16px" }}>
                    <div className="row gap-6">
                      <button className="btn btn-sm" onClick={() => setManageSlug(t.slug)}>管理</button>
                      {t.status === "active"
                        ? <button className="btn btn-sm" disabled={busyId === t.slug} style={{ color: "var(--danger)" }} onClick={() => setStatus(t.slug, "suspended")}>停用</button>
                        : <button className="btn btn-sm" disabled={busyId === t.slug} style={{ color: "var(--ok)" }} onClick={() => setStatus(t.slug, "active")}>恢復</button>}
                    </div>
                  </td>
                </tr>
              ))}
              {tenants.length === 0 && <tr><td colSpan={6} className="muted" style={{ padding: 24, textAlign: "center" }}>暫無公司</td></tr>}
            </tbody>
          </table>
        </div>
      )}
      {showCreate && <CompanyCreateModal onClose={() => setShowCreate(false)} onCreated={load}/>}
      {manageSlug && <CompanyManageModal slug={manageSlug} onClose={() => setManageSlug(null)} onChanged={load}/>}
    </div>
  );
};

window.PageCompanies = PageCompanies;
