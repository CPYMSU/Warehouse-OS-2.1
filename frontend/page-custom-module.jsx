/* ============================================================
   自定義數據模塊 — 通用增刪改查頁(由平台運營員定義的模塊驅動)
   active = "custom:<key>";字段與結構來自 bootstrap 的 CUSTOM_MODULES
   ============================================================ */
const { useState: useStateCM, useEffect: useEffectCM, useMemo: useMemoCM } = React;

const cmFetch = async (url, options) => {
  const res = await (window.authFetch || fetch)(url, options);
  const data = await res.json().catch(() => ({}));
  return { ok: res.ok, data };
};

const cmFindModule = (key) => (window.CUSTOM_MODULES || []).find((m) => m.key === key) || null;

const cmEmptyForm = (fields) => {
  const f = {};
  (fields || []).forEach((x) => { f[x.key] = x.type === "checkbox" ? false : ""; });
  return f;
};

const cmFieldInput = (field, value, onChange) => {
  const common = { className: "input", value: value == null ? "" : value, onChange: (e) => onChange(e.target.value) };
  if (field.type === "textarea") return <textarea {...common} rows={3} style={{ height: "auto", padding: 10, resize: "none" }}/>;
  if (field.type === "number") return <input {...common} type="number"/>;
  if (field.type === "date") return <input {...common} type="date"/>;
  if (field.type === "select") return (
    <select {...common}><option value="">— 請選擇 —</option>{(field.options || []).map((o) => <option key={o} value={o}>{o}</option>)}</select>
  );
  if (field.type === "checkbox") return (
    <button type="button" className="btn btn-sm" onClick={() => onChange(!value)}
      style={{ background: value ? "var(--blue)" : "var(--surface-2)", color: value ? "#fff" : "var(--ink-2)", width: 72 }}>{value ? "是 ✓" : "否"}</button>
  );
  return <input {...common}/>;
};

const PageCustomModule = ({ moduleKey }) => {
  const [mod, setMod] = useStateCM(cmFindModule(moduleKey));
  const [records, setRecords] = useStateCM([]);
  const [loading, setLoading] = useStateCM(true);
  const [err, setErr] = useStateCM("");
  const [editing, setEditing] = useStateCM(null); // null | {id?} 編輯中的記錄
  const [form, setForm] = useStateCM({});
  const [saving, setSaving] = useStateCM(false);

  const fields = (mod && mod.fields) || [];

  const load = () => {
    setLoading(true); setErr("");
    cmFetch(`/api/custom/${moduleKey}/records`).then(({ ok, data }) => {
      if (!ok) { setErr(data.error || "載入失敗"); return; }
      if (data.module) setMod(data.module);
      setRecords(data.records || []);
    }).catch((e) => setErr(e.message || String(e))).finally(() => setLoading(false));
  };
  useEffectCM(() => { setMod(cmFindModule(moduleKey)); load(); }, [moduleKey]);

  const openNew = () => { setEditing({}); setForm(cmEmptyForm(fields)); setErr(""); };
  const openEdit = (rec) => { setEditing(rec); setForm({ ...cmEmptyForm(fields), ...(rec.data || {}) }); setErr(""); };
  const closeForm = () => setEditing(null);

  const save = () => {
    setSaving(true); setErr("");
    const isEdit = editing && editing.id;
    const url = isEdit ? `/api/custom/${moduleKey}/records/${editing.id}` : `/api/custom/${moduleKey}/records`;
    cmFetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(form) })
      .then(({ ok, data }) => { if (!ok) throw new Error(data.error || "保存失敗"); closeForm(); load(); })
      .catch((e) => setErr(e.message || String(e))).finally(() => setSaving(false));
  };
  const remove = (rec) => {
    if (!window.confirm("確定刪除這條記錄?")) return;
    cmFetch(`/api/custom/${moduleKey}/records/${rec.id}/delete`, { method: "POST", body: "{}" })
      .then(({ ok, data }) => { if (!ok) throw new Error(data.error || "刪除失敗"); load(); })
      .catch((e) => setErr(e.message || String(e)));
  };

  const fmt = (field, v) => {
    if (field.type === "checkbox") return v ? "✓" : "—";
    return (v == null || v === "") ? "—" : String(v);
  };

  if (!mod) return <Stub title="模塊未找到(可能已被移除)"/>;

  return (
    <div className="col gap-18">
      <PageHead title={mod.name} sub={`自定義模塊 · 共 ${records.length} 條記錄`}
        actions={<button className="btn btn-primary btn-sm" onClick={openNew}><Icon name="plus" size={14}/>新增記錄</button>}/>
      {err && <div className="card" style={{ padding: 12, color: "var(--danger)", fontWeight: 700, fontSize: 13 }}>⚠ {err}</div>}

      <div className="card" style={{ padding: 0, overflow: "hidden" }}>
        <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
            <thead><tr style={{ background: "var(--surface-2)", textAlign: "left" }}>
              {fields.map((f) => <th key={f.key} style={{ padding: "12px 16px", fontWeight: 700, fontSize: 12, whiteSpace: "nowrap" }}>{f.label}</th>)}
              <th style={{ padding: "12px 16px", fontWeight: 700, fontSize: 12 }}>操作</th>
            </tr></thead>
            <tbody>
              {loading && <tr><td colSpan={fields.length + 1} className="muted" style={{ padding: 18, textAlign: "center" }}>載入中…</td></tr>}
              {!loading && records.length === 0 && <tr><td colSpan={fields.length + 1} className="muted" style={{ padding: 22, textAlign: "center" }}>暫無記錄,點右上角「新增記錄」開始錄入。</td></tr>}
              {records.map((rec) => (
                <tr key={rec.id} style={{ borderTop: "1px solid var(--line)" }}>
                  {fields.map((f) => <td key={f.key} style={{ padding: "11px 16px" }}>{fmt(f, (rec.data || {})[f.key])}</td>)}
                  <td style={{ padding: "11px 16px" }}>
                    <div className="row gap-6">
                      <button className="btn btn-sm" onClick={() => openEdit(rec)}>編輯</button>
                      <button className="btn btn-sm" style={{ color: "var(--danger)" }} onClick={() => remove(rec)}>刪除</button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {editing && (
        <div className="center" style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,.4)", zIndex: 50, padding: 24 }} onClick={closeForm}>
          <div className="card col gap-14" style={{ width: "min(520px, 100%)", padding: 24, maxHeight: "88vh", overflowY: "auto" }} onClick={(e) => e.stopPropagation()}>
            <div className="row spread"><div style={{ fontSize: 16, fontWeight: 800 }}>{editing.id ? "編輯記錄" : "新增記錄"} · {mod.name}</div>
              <button onClick={closeForm} style={{ background: "none", border: "none", cursor: "pointer", fontSize: 16, fontWeight: 700, color: "var(--ink-3)" }}>✕</button></div>
            {fields.map((f) => (
              <label key={f.key} className="col gap-6" style={{ fontSize: 12.5, fontWeight: 700 }}>
                {f.label}{f.required ? <span style={{ color: "var(--danger)" }}> *</span> : ""}
                {cmFieldInput(f, form[f.key], (v) => setForm({ ...form, [f.key]: v }))}
              </label>
            ))}
            {err && <div style={{ color: "var(--danger)", fontSize: 13, fontWeight: 700 }}>{err}</div>}
            <div className="row gap-8">
              <button className="btn btn-primary" style={{ flex: 1, height: 42 }} disabled={saving} onClick={save}>{saving ? "保存中…" : "保存"}</button>
              <button className="btn" style={{ height: 42 }} onClick={closeForm}>取消</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

window.PageCustomModule = PageCustomModule;
