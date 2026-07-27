/* ============================================================
   倉庫地圖 GIS — 真實倉庫 / 庫位 / 預警聯動工作台
   ============================================================ */
const {
  useState: useStateGis,
  useEffect: useEffectGis,
  useMemo: useMemoGis,
  useRef: useRefGis,
} = React;

const GIS_API_BASE = typeof window.WAREHOUSE_API_BASE === "string" ? window.WAREHOUSE_API_BASE : "http://127.0.0.1:8090";
const GIS_STYLE_OF = (k) => `https://tiles.openfreemap.org/styles/${k}`;
const GIS_STYLES = [["liberty", "標準"], ["bright", "明亮"], ["positron", "淡色"], ["dark", "暗色"]];
const GIS_EMPTY = { summary: {}, warehouses: [], zones: [], locations: [], areas: [], alerts: [] };
const GIS_STATUS = [
  ["all", "全部狀態"],
  ["normal", "正常"],
  ["low_stock", "低庫存"],
  ["risk", "有風險"],
  ["empty", "空庫位"],
];
const GIS_LEVEL_LABEL = { red: "重大", orange: "高", yellow: "中", blue: "提示" };

const gisFetch = (path, options) => (window.authFetch || fetch)(`${GIS_API_BASE}${path}`, options);
const gisNum = (v, digits = 0) => {
  const n = Number(v);
  if (!Number.isFinite(n)) return "—";
  return digits ? n.toFixed(digits) : Math.round(n).toString();
};
const gisTone = (v) => {
  const n = Number(v || 0);
  if (n >= 90) return "danger";
  if (n >= 70) return "warn";
  return "ok";
};
const gisStatusTone = (s) => s === "risk" || s === "low_stock" || s === "empty" ? "danger" : "ok";
const gisHasPerm = (perm) => {
  const p = new Set(((window.CURRENT_USER || {}).permissions || []));
  return p.has(perm);
};
const gisEsc = (s) => String(s == null ? "—" : s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const gisWhPopup = (w) => `
  <div style="min-width:210px">
    <div style="font-weight:800;font-size:14px;margin-bottom:4px">${gisEsc(w.name)}</div>
    <div style="font-size:12px;color:#5b6b7f;line-height:1.7">
      <div>${gisEsc(w.code || "未編碼")} · ${gisEsc(w.warehouse_type || "未分類")}</div>
      <div>物資 ${gisEsc(w.item_count || 0)} 種 · 庫存 ${gisEsc(gisNum(w.stock_total))}</div>
      <div>庫位 ${gisEsc(w.locations_count || 0)} · 預警 ${gisEsc(w.open_alerts || 0)}</div>
    </div>
  </div>`;

const gisHaversine = (a, b) => {
  const R = 6371000, rad = Math.PI / 180;
  const dLat = (b[1] - a[1]) * rad, dLng = (b[0] - a[0]) * rad;
  const s = Math.sin(dLat / 2) ** 2 + Math.cos(a[1] * rad) * Math.cos(b[1] * rad) * Math.sin(dLng / 2) ** 2;
  return 2 * R * Math.asin(Math.min(1, Math.sqrt(s)));
};
const gisLineLen = (pts) => pts.reduce((d, p, i) => i ? d + gisHaversine(pts[i - 1], p) : 0, 0);
const gisFmtLen = (m) => m >= 1000 ? `${(m / 1000).toFixed(2)} 公里` : `${Math.round(m)} 米`;
const gisDraftGeo = (pts, mode) => {
  const features = pts.map((p, i) => ({ type: "Feature", geometry: { type: "Point", coordinates: p }, properties: { idx: i + 1 } }));
  if (pts.length >= 2) features.push({ type: "Feature", geometry: { type: "LineString", coordinates: mode === "area" && pts.length >= 3 ? pts.concat([pts[0]]) : pts }, properties: {} });
  if (mode === "area" && pts.length >= 3) features.push({ type: "Feature", geometry: { type: "Polygon", coordinates: [pts.concat([pts[0]])] }, properties: {} });
  return { type: "FeatureCollection", features };
};

const PageWarehouseGIS = () => {
  const mapNode = useRefGis(null);
  const mapRef = useRefGis(null);
  const editMarkerRef = useRefGis(null);
  const modeRef = useRefGis(null);
  const placingRef = useRefGis(false);
  const draftRef = useRefGis([]);
  const whRef = useRefGis([]);
  const fitOnceRef = useRefGis(false);

  const [data, setData] = useStateGis(GIS_EMPTY);
  const [loading, setLoading] = useStateGis(true);
  const [error, setError] = useStateGis("");
  const [msg, setMsg] = useStateGis("");
  const [busy, setBusy] = useStateGis(false);
  const [selectedWhId, setSelectedWhId] = useStateGis(null);
  const [selectedLoc, setSelectedLoc] = useStateGis(null);
  const [query, setQuery] = useStateGis("");
  const [riskOnly, setRiskOnly] = useStateGis(false);
  const [status, setStatus] = useStateGis("all");
  const [styleKey, setStyleKey] = useStateGis("liberty");
  const [mode, setMode] = useStateGis(null);
  const [draftN, setDraftN] = useStateGis(0);
  const [placing, setPlacing] = useStateGis(false);
  const [noMap, setNoMap] = useStateGis(!window.maplibregl);
  const [zoneName, setZoneName] = useStateGis("服務範圍");
  const [addr, setAddr] = useStateGis("");
  const [geoResults, setGeoResults] = useStateGis([]);
  const [geoBusy, setGeoBusy] = useStateGis(false);
  const [aiText, setAiText] = useStateGis("");
  const [aiBusy, setAiBusy] = useStateGis(false);
  const [aiItems, setAiItems] = useStateGis([]);
  const [pinForm, setPinForm] = useStateGis({ name: "", lat: "", lng: "", address: "" });
  const [locForm, setLocForm] = useStateGis(null);
  const [aiLayoutResult, setAiLayoutResult] = useStateGis(null);

  const canLocate = gisHasPerm("gis.locate") || gisHasPerm("gis.manage");
  const canManage = gisHasPerm("gis.manage");
  const canAiDelegate = gisHasPerm("gis.ai_delegate") || gisHasPerm("ai.write") || canManage;

  const selectedWh = useMemoGis(() => {
    const list = data.warehouses || [];
    return list.find((w) => String(w.id) === String(selectedWhId)) || list[0] || null;
  }, [data, selectedWhId]);

  const selectedZones = useMemoGis(() => (data.zones || []).filter((z) => selectedWh && String(z.warehouse_id) === String(selectedWh.id)), [data, selectedWh]);
  const selectedLocations = useMemoGis(() => (data.locations || []).filter((l) => selectedWh && String(l.warehouse_id) === String(selectedWh.id)), [data, selectedWh]);
  const whAlerts = useMemoGis(() => {
    if (!selectedWh) return [];
    return (data.alerts || []).filter((a) => String(a.scope || "").includes(selectedWh.name)).slice(0, 8);
  }, [data, selectedWh]);

  const filteredLocations = useMemoGis(() => {
    const q = query.trim().toLowerCase();
    return selectedLocations.filter((l) => {
      const hit = !q || [l.location_code, l.zone_name, l.rack_code, ...(l.sample_items || [])].some((v) => String(v || "").toLowerCase().includes(q));
      const riskHit = !riskOnly || Number(l.low_stock_count || 0) > 0 || ["risk", "low_stock", "empty"].includes(l.alert_status);
      const stHit = status === "all" || l.alert_status === status;
      return hit && riskHit && stHit;
    });
  }, [selectedLocations, query, riskOnly, status]);

  const summaryCards = [
    ["倉庫", data.summary.warehouses || 0, `${data.summary.located || 0} 已定位`, "map2"],
    ["庫位", data.summary.locations || 0, `${data.summary.unlocatedLocations || 0} 未定位`, "grid"],
    ["預警", data.summary.openAlerts || 0, `${data.summary.highAlerts || 0} 高風險`, "alert"],
    ["低庫存庫位", data.summary.lowStockLocations || 0, "需優先處理", "box"],
  ];

  const load = () => {
    setLoading(true); setError("");
    gisFetch("/api/gis/overview")
      .then((r) => r.json().then((d) => ({ ok: r.ok, d })))
      .then(({ ok, d }) => {
        if (!ok) throw new Error(d.error || "GIS 資料載入失敗");
        setData(d || GIS_EMPTY);
        if (!selectedWhId && d.warehouses && d.warehouses[0]) setSelectedWhId(d.warehouses[0].id);
      })
      .catch((e) => setError(e.message || String(e)))
      .finally(() => setLoading(false));
  };

  useEffectGis(() => { load(); }, []);

  const setSourceData = (id, geo) => {
    const map = mapRef.current;
    if (map && map.getSource(id)) map.getSource(id).setData(geo);
  };

  const whGeo = (list) => ({
    type: "FeatureCollection",
    features: (list || []).filter((w) => w.lat != null && w.lng != null).map((w) => ({
      type: "Feature",
      geometry: { type: "Point", coordinates: [+w.lng, +w.lat] },
      properties: {
        id: w.id, name: w.name, popup: gisWhPopup(w),
        cap: Number(w.capacity_usage || 0), alerts: Number(w.high_alerts || w.open_alerts || 0),
        selected: selectedWh && String(selectedWh.id) === String(w.id) ? 1 : 0,
      },
    })),
  });
  const areaGeo = (areas) => ({
    type: "FeatureCollection",
    features: (areas || []).filter((a) => a.geojson).map((a) => ({
      type: "Feature", geometry: a.geojson.geometry || a.geojson,
      properties: { id: a.id, name: a.name, color: a.color || "#1B6BFF" },
    })),
  });

  const addLayers = () => {
    const map = mapRef.current;
    if (!map || !map.isStyleLoaded()) return;
    const EMPTY = { type: "FeatureCollection", features: [] };
    if (!map.getSource("gis-areas")) map.addSource("gis-areas", { type: "geojson", data: areaGeo(data.areas || []) });
    if (!map.getLayer("gis-area-fill")) map.addLayer({ id: "gis-area-fill", type: "fill", source: "gis-areas", paint: { "fill-color": ["coalesce", ["get", "color"], "#1B6BFF"], "fill-opacity": 0.2 } });
    if (!map.getLayer("gis-area-line")) map.addLayer({ id: "gis-area-line", type: "line", source: "gis-areas", paint: { "line-color": ["coalesce", ["get", "color"], "#1B6BFF"], "line-width": 2.5 } });
    if (!map.getLayer("gis-area-label")) map.addLayer({ id: "gis-area-label", type: "symbol", source: "gis-areas", layout: { "text-field": ["get", "name"], "text-size": 12, "text-allow-overlap": true }, paint: { "text-color": "#0f3d88", "text-halo-color": "#fff", "text-halo-width": 2 } });
    if (!map.getSource("gis-whs")) map.addSource("gis-whs", { type: "geojson", data: whGeo(data.warehouses || []), cluster: true, clusterRadius: 46, clusterMaxZoom: 11 });
    if (!map.getLayer("gis-clusters")) map.addLayer({ id: "gis-clusters", type: "circle", source: "gis-whs", filter: ["has", "point_count"], paint: { "circle-color": "#1B6BFF", "circle-radius": ["step", ["get", "point_count"], 17, 10, 23, 40, 31], "circle-opacity": 0.86 } });
    if (!map.getLayer("gis-cluster-count")) map.addLayer({ id: "gis-cluster-count", type: "symbol", source: "gis-whs", filter: ["has", "point_count"], layout: { "text-field": ["get", "point_count_abbreviated"], "text-size": 12 }, paint: { "text-color": "#fff" } });
    if (!map.getLayer("gis-wh-points")) map.addLayer({ id: "gis-wh-points", type: "circle", source: "gis-whs", filter: ["!", ["has", "point_count"]], paint: { "circle-radius": ["case", ["==", ["get", "selected"], 1], 13, 9], "circle-stroke-width": 2.5, "circle-stroke-color": "#fff", "circle-color": ["case", [">", ["get", "alerts"], 0], "#ef4444", [">=", ["get", "cap"], 90], "#f59e0b", "#1B6BFF"] } });
    if (!map.getLayer("gis-wh-label")) map.addLayer({ id: "gis-wh-label", type: "symbol", source: "gis-whs", filter: ["!", ["has", "point_count"]], layout: { "text-field": ["get", "name"], "text-size": 12, "text-offset": [0, 1.2], "text-anchor": "top" }, paint: { "text-color": "#172033", "text-halo-color": "#fff", "text-halo-width": 1.5 } });
    if (!map.getSource("gis-draft")) map.addSource("gis-draft", { type: "geojson", data: EMPTY });
    if (!map.getLayer("gis-draft-fill")) map.addLayer({ id: "gis-draft-fill", type: "fill", source: "gis-draft", filter: ["==", "$type", "Polygon"], paint: { "fill-color": "#f59e0b", "fill-opacity": 0.16 } });
    if (!map.getLayer("gis-draft-line")) map.addLayer({ id: "gis-draft-line", type: "line", source: "gis-draft", filter: ["==", "$type", "LineString"], paint: { "line-color": "#f59e0b", "line-width": 2 } });
    if (!map.getLayer("gis-draft-pt")) map.addLayer({ id: "gis-draft-pt", type: "circle", source: "gis-draft", filter: ["==", "$type", "Point"], paint: { "circle-radius": 5, "circle-color": "#f59e0b", "circle-stroke-color": "#fff", "circle-stroke-width": 2 } });
  };

  useEffectGis(() => {
    if (!window.maplibregl) { setNoMap(true); return; }
    if (mapRef.current || !mapNode.current) return;
    const gl = window.maplibregl;
    const map = new gl.Map({ container: mapNode.current, style: GIS_STYLE_OF(styleKey), center: [111.7490, 40.8417], zoom: 4 });
    map.addControl(new gl.NavigationControl({ visualizePitch: true }), "top-right");
    map.addControl(new gl.FullscreenControl(), "top-right");
    map.addControl(new gl.ScaleControl({ unit: "metric" }), "bottom-left");
    map.on("styleimagemissing", (e) => { try { if (e && e.id && !map.hasImage(e.id)) map.addImage(e.id, { width: 1, height: 1, data: new Uint8Array(4) }); } catch (_) {} });
    map.on("error", (e) => { if (e && e.error) setError("地圖瓦片加載較慢或失敗，資料工作台仍可正常使用。"); });
    map.on("load", addLayers);
    map.on("click", (e) => {
      if (modeRef.current) {
        draftRef.current = draftRef.current.concat([[+e.lngLat.lng, +e.lngLat.lat]]);
        setDraftN(draftRef.current.length);
        setSourceData("gis-draft", gisDraftGeo(draftRef.current, modeRef.current));
        return;
      }
      if (placingRef.current) {
        const lat = +e.lngLat.lat.toFixed(6), lng = +e.lngLat.lng.toFixed(6);
        setPinForm((f) => ({ ...f, lat, lng }));
        placingRef.current = false; setPlacing(false);
      }
    });
    map.on("click", "gis-clusters", (e) => {
      const f = map.queryRenderedFeatures(e.point, { layers: ["gis-clusters"] })[0];
      if (!f) return;
      map.getSource("gis-whs").getClusterExpansionZoom(f.properties.cluster_id).then((z) => map.easeTo({ center: f.geometry.coordinates, zoom: z })).catch(() => {});
    });
    map.on("click", "gis-wh-points", (e) => {
      const f = e.features && e.features[0];
      if (!f) return;
      setSelectedWhId(f.properties.id);
      new gl.Popup({ offset: 14, closeButton: false }).setLngLat(f.geometry.coordinates).setHTML(f.properties.popup).addTo(map);
    });
    ["gis-clusters", "gis-wh-points"].forEach((lyr) => {
      map.on("mouseenter", lyr, () => { map.getCanvas().style.cursor = "pointer"; });
      map.on("mouseleave", lyr, () => { map.getCanvas().style.cursor = ""; });
    });
    mapRef.current = map;
    setTimeout(() => map.resize(), 80);
    return () => { map.remove(); mapRef.current = null; };
  }, []);

  useEffectGis(() => {
    whRef.current = data.warehouses || [];
    setSourceData("gis-whs", whGeo(data.warehouses || []));
    setSourceData("gis-areas", areaGeo(data.areas || []));
    const map = mapRef.current, gl = window.maplibregl;
    if (map && gl && !fitOnceRef.current) {
      const located = (data.warehouses || []).filter((w) => w.lat != null && w.lng != null);
      if (located.length) {
        try {
          const b = new gl.LngLatBounds();
          located.forEach((w) => b.extend([+w.lng, +w.lat]));
          map.fitBounds(b, { padding: 70, maxZoom: 12, duration: 0 });
          fitOnceRef.current = true;
        } catch (_) {}
      }
    }
  }, [data, selectedWhId]);

  useEffectGis(() => {
    const map = mapRef.current;
    if (!map || !selectedWh) return;
    if (selectedWh.lat != null && selectedWh.lng != null) {
      map.easeTo({ center: [+selectedWh.lng, +selectedWh.lat], zoom: Math.max(map.getZoom(), 9), duration: 450 });
    }
    setPinForm({ name: selectedWh.name || "", lat: selectedWh.lat ?? "", lng: selectedWh.lng ?? "", address: selectedWh.address || "" });
  }, [selectedWhId]);

  useEffectGis(() => {
    const gl = window.maplibregl, map = mapRef.current;
    if (!gl || !map) return;
    if (editMarkerRef.current) { editMarkerRef.current.remove(); editMarkerRef.current = null; }
    const lat = parseFloat(pinForm.lat), lng = parseFloat(pinForm.lng);
    if (Number.isFinite(lat) && Number.isFinite(lng)) {
      const m = new gl.Marker({ draggable: true, color: "#07B6A2" }).setLngLat([lng, lat]).addTo(map);
      m.on("dragend", () => {
        const ll = m.getLngLat();
        setPinForm((f) => ({ ...f, lat: +ll.lat.toFixed(6), lng: +ll.lng.toFixed(6) }));
      });
      editMarkerRef.current = m;
    }
  }, [pinForm.lat, pinForm.lng]);

  const switchStyle = (k) => {
    setStyleKey(k);
    const map = mapRef.current;
    if (!map) return;
    map.setStyle(GIS_STYLE_OF(k));
    map.once("style.load", () => {
      addLayers();
      setSourceData("gis-whs", whGeo(data.warehouses || []));
      setSourceData("gis-areas", areaGeo(data.areas || []));
      setSourceData("gis-draft", gisDraftGeo(draftRef.current, modeRef.current));
    });
  };

  const setTool = (next) => {
    const m = mode === next ? null : next;
    setMode(m); modeRef.current = m;
    draftRef.current = []; setDraftN(0); setSourceData("gis-draft", { type: "FeatureCollection", features: [] });
    placingRef.current = false; setPlacing(false);
  };
  const clearDraft = () => { draftRef.current = []; setDraftN(0); setSourceData("gis-draft", { type: "FeatureCollection", features: [] }); };

  const saveArea = () => {
    if (!canManage) { setError("當前帳號沒有 GIS 圖層管理權限"); return; }
    const pts = draftRef.current;
    if (!pts || pts.length < 3) { setError("區域至少需要 3 個頂點"); return; }
    const name = (zoneName || "服務範圍").trim();
    const ring = pts.concat([pts[0]]);
    setBusy(true); setError(""); setMsg("");
    gisFetch("/api/map/zones", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, kind: "area", warehouse_id: selectedWh ? selectedWh.id : null, color: "#1B6BFF", geojson: { type: "Polygon", coordinates: [ring] } }),
    })
      .then((r) => r.json().then((d) => ({ ok: r.ok, d })))
      .then(({ ok, d }) => { if (!ok) throw new Error(d.error || "保存區域失敗"); setMsg(`已保存區域「${name}」`); setTool(null); load(); })
      .catch((e) => setError(e.message || String(e)))
      .finally(() => setBusy(false));
  };

  const autoLayout = () => {
    if (!canManage) { setError("當前帳號沒有 GIS 管理權限"); return; }
    setBusy(true); setError(""); setMsg("");
    gisFetch("/api/gis/auto-layout", { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" })
      .then((r) => r.json().then((d) => ({ ok: r.ok, d })))
      .then(({ ok, d }) => {
        if (!ok) throw new Error(d.error || "整理庫位失敗");
        setMsg(`已整理 ${d.linked_balances || 0} 條庫存，新增 ${d.created_locations || 0} 個庫位`);
        load(); if (window.reloadData) window.reloadData();
      })
      .catch((e) => setError(e.message || String(e)))
      .finally(() => setBusy(false));
  };

  const aiLayout = () => {
    if (!canAiDelegate) { setError("當前帳號不能委託 AI 托管分庫"); return; }
    setBusy(true); setError(""); setMsg("");
    gisFetch("/api/gis/ai-layout", { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" })
      .then((r) => r.json().then((d) => ({ ok: r.ok, d })))
      .then(({ ok, d }) => {
        if (!ok) throw new Error(d.error || "AI 托管分庫失敗");
        setAiLayoutResult(d);
        setMsg(d.message || "AI 已完成分庫與庫位整理");
        load(); if (window.reloadData) window.reloadData();
      })
      .catch((e) => setError(e.message || String(e)))
      .finally(() => setBusy(false));
  };

  const savePin = () => {
    if (!canLocate) { setError("當前帳號沒有 GIS 定位權限"); return; }
    if (!pinForm.name.trim()) { setError("請填寫倉庫名稱"); return; }
    if (pinForm.lat === "" || pinForm.lng === "") { setError("請設置坐標"); return; }
    setBusy(true); setError(""); setMsg("");
    gisFetch("/api/warehouses/gis-pin", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: pinForm.name.trim(), lat: pinForm.lat, lng: pinForm.lng, address: pinForm.address || null }),
    })
      .then((r) => r.json().then((d) => ({ ok: r.ok, d })))
      .then(({ ok, d }) => { if (!ok) throw new Error(d.error || "保存定位失敗"); setMsg(d.linked ? "已更新倉庫定位" : "已新建倉庫定位"); load(); if (window.reloadData) window.reloadData(); })
      .catch((e) => setError(e.message || String(e)))
      .finally(() => setBusy(false));
  };

  const geocode = () => {
    const q = (addr || pinForm.address || pinForm.name || "").trim();
    if (!q) { setError("請輸入地址或地名"); return; }
    setGeoBusy(true); setError(""); setGeoResults([]);
    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), 7000);
    fetch(`https://nominatim.openstreetmap.org/search?format=json&limit=5&accept-language=zh&q=${encodeURIComponent(q)}`, { signal: ctrl.signal })
      .then((r) => r.json())
      .then((rows) => { setGeoResults(rows || []); if (!rows || !rows.length) setError("未找到地址，可改用點選或直接填經緯度"); })
      .catch((e) => setError(e && e.name === "AbortError" ? "地址搜索超時，可改用點選" : "地址搜索失敗，可改用點選"))
      .finally(() => { clearTimeout(timer); setGeoBusy(false); });
  };

  const parseAiWarehouses = () => {
    const text = aiText.trim();
    if (!text) { setError("請輸入倉庫描述"); return; }
    setAiBusy(true); setError(""); setMsg("");
    gisFetch("/api/warehouses/ai-parse", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    })
      .then((r) => r.json().then((d) => ({ ok: r.ok, d })))
      .then(({ ok, d }) => {
        if (!ok) throw new Error(d.error || "AI 識別失敗");
        const rows = d.warehouses || [];
        setAiItems(rows);
        setMsg(rows.length ? `AI 已識別 ${rows.length} 個倉庫，可載入後定位` : "AI 未識別出倉庫，請補充描述");
      })
      .catch((e) => setError(e.message || String(e)))
      .finally(() => setAiBusy(false));
  };

  const pickGeo = (g) => {
    const lat = parseFloat(g.lat), lng = parseFloat(g.lon);
    setPinForm((f) => ({ ...f, lat: +lat.toFixed(6), lng: +lng.toFixed(6), address: g.display_name || f.address }));
    setGeoResults([]);
    if (mapRef.current) mapRef.current.easeTo({ center: [lng, lat], zoom: 13 });
  };

  const openLocationForm = (loc) => {
    const source = loc || {};
    setSelectedLoc(loc || null);
    setLocForm({
      id: typeof source.id === "number" ? source.id : "",
      warehouse_id: selectedWh ? selectedWh.id : source.warehouse_id || "",
      zone_id: typeof source.zone_id === "number" ? source.zone_id : "",
      location_code: source.location_code || "",
      rack_code: source.rack_code || "",
      floor_no: source.floor_no || "1F",
      x_pos: source.x_pos ?? "",
      y_pos: source.y_pos ?? "",
      z_pos: source.z_pos ?? "",
      capacity_usage: source.capacity_usage ?? "",
      alert_status: source.alert_status || "normal",
    });
  };

  const saveLocation = () => {
    if (!canManage || !locForm) return;
    const id = locForm.id;
    const path = id ? `/api/gis/locations/${id}` : "/api/gis/locations";
    setBusy(true); setError(""); setMsg("");
    gisFetch(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(locForm) })
      .then((r) => r.json().then((d) => ({ ok: r.ok, d })))
      .then(({ ok, d }) => { if (!ok) throw new Error(d.error || "保存庫位失敗"); setMsg("庫位已保存"); setLocForm(null); load(); if (window.reloadData) window.reloadData(); })
      .catch((e) => setError(e.message || String(e)))
      .finally(() => setBusy(false));
  };

  const deleteLocation = () => {
    if (!canManage || !locForm || !locForm.id) return;
    if (!window.confirm(`刪除庫位「${locForm.location_code}」?`)) return;
    setBusy(true); setError(""); setMsg("");
    gisFetch(`/api/gis/locations/${locForm.id}/delete`, { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" })
      .then((r) => r.json().then((d) => ({ ok: r.ok, d })))
      .then(({ ok, d }) => { if (!ok) throw new Error(d.error || "刪除庫位失敗"); setMsg(d.deactivated ? "庫位已停用" : "庫位已刪除"); setLocForm(null); load(); if (window.reloadData) window.reloadData(); })
      .catch((e) => setError(e.message || String(e)))
      .finally(() => setBusy(false));
  };

  const pruneEmptyLocations = () => {
    if (!canManage) { setError("當前帳號沒有 GIS 管理權限"); return; }
    if (!window.confirm("清理所有沒有任何庫存餘額引用的空庫位？\n這會把 BUG 產生的空殼庫位清出地圖；有庫存引用的真實庫位不會被處理。")) return;
    setBusy(true); setError(""); setMsg("");
    gisFetch("/api/gis/locations/prune-empty", { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" })
      .then((r) => r.json().then((d) => ({ ok: r.ok, d })))
      .then(({ ok, d }) => {
        if (!ok) throw new Error(d.error || "清理空庫位失敗");
        setMsg(d.message || `已清理 ${d.deleted || 0} 個空庫位`);
        load(); if (window.reloadData) window.reloadData();
      })
      .catch((e) => setError(e.message || String(e)))
      .finally(() => setBusy(false));
  };

  const draftDistance = mode === "measure" && draftN >= 2 ? gisFmtLen(gisLineLen(draftRef.current)) : "";

  return (
    <div className="gis-workbench">
      <PageHead title="倉庫地圖 GIS" sub="倉庫點位、庫內庫位、預警風險與區域圖層一體化"
        actions={<>
          <button className="btn btn-sm" onClick={load} disabled={loading || busy}><Icon name="refresh" size={14}/>刷新</button>
          {canAiDelegate && <button className="btn btn-primary btn-sm" onClick={aiLayout} disabled={busy}><Icon name="sparkle" size={14}/>AI 托管分庫</button>}
          {canManage && <button className="btn btn-primary btn-sm" onClick={autoLayout} disabled={busy}><Icon name="layers" size={14}/>自動整理庫位</button>}
          {canManage && <button className="btn btn-sm" onClick={pruneEmptyLocations} disabled={busy}><Icon name="x" size={14}/>清理空庫位</button>}
        </>}/>

      {error && <div className="gis-notice gis-notice-error">{error}</div>}
      {msg && <div className="gis-notice gis-notice-ok">{msg}</div>}

      <section className="gis-summary">
        {summaryCards.map(([label, value, sub, icon]) => (
          <div className="gis-metric" key={label}>
            <span className="gis-metric-icon"><Icon name={icon} size={17}/></span>
            <span className="gis-metric-label">{label}</span>
            <strong className="num">{value}</strong>
            <small>{sub}</small>
          </div>
        ))}
      </section>

      <section className="gis-main">
        <div className="gis-map-shell">
          <div className="gis-map-top">
            <div className="gis-segments">
              {GIS_STYLES.map(([k, label]) => <button key={k} className={styleKey === k ? "active" : ""} onClick={() => switchStyle(k)}>{label}</button>)}
            </div>
            <div className="gis-tool-row">
              {canManage && <button className={mode === "area" ? "active" : ""} onClick={() => setTool("area")}><Icon name="edit" size={14}/>畫區域</button>}
              <button className={mode === "measure" ? "active" : ""} onClick={() => setTool("measure")}><Icon name="scan" size={14}/>測距</button>
              {draftN > 0 && <button onClick={clearDraft}><Icon name="x" size={14}/>清除</button>}
            </div>
          </div>
          <div ref={mapNode} className="gis-map-canvas"/>
          {noMap && <div className="gis-map-fallback">地圖庫未載入，請刷新頁面或檢查網絡。</div>}
          {(mode || placing) && <div className="gis-pick-hint">{mode === "area" ? "點擊地圖添加區域頂點" : mode === "measure" ? "點擊地圖添加測距點" : "點擊地圖選擇倉庫坐標"}</div>}
          {mode === "measure" && draftDistance && <div className="gis-measure-readout">距離：<b>{draftDistance}</b></div>}
          {mode === "area" && draftN >= 3 && (
            <div className="gis-area-save">
              <input className="input" value={zoneName} onChange={(e) => setZoneName(e.target.value)} placeholder="區域名稱"/>
              <button className="btn btn-primary btn-sm" onClick={saveArea} disabled={busy}>保存區域</button>
            </div>
          )}
        </div>

        <aside className="gis-side">
          <div className="gis-panel">
            <div className="gis-panel-head">
              <span>倉庫</span>
              <small>{data.warehouses.length}</small>
            </div>
            <div className="gis-warehouse-list">
              {(data.warehouses || []).map((w) => (
                <button key={w.id} className={"gis-warehouse-row " + (selectedWh && selectedWh.id === w.id ? "active" : "")} onClick={() => setSelectedWhId(w.id)}>
                  <span>
                    <b>{w.name}</b>
                    <small>{w.code || "未編碼"} · {w.warehouse_type || "未分類"}</small>
                  </span>
                  <em className={"gis-pill " + (w.high_alerts ? "danger" : w.open_alerts ? "warn" : "ok")}>{w.open_alerts || 0}</em>
                </button>
              ))}
              {!loading && !data.warehouses.length && <div className="muted" style={{ fontSize: 13 }}>暫無倉庫資料。</div>}
            </div>
          </div>

          {canAiDelegate && (
            <div className="gis-panel">
              <div className="gis-panel-head"><span>AI 分庫托管</span><small>GIS v1</small></div>
              <div className="gis-kpi-line">
                <div><small>規範庫位</small><b>{aiLayoutResult?.summary?.normalized_balance_locations || 0}</b></div>
                <div><small>新增庫區</small><b>{aiLayoutResult?.summary?.created_zones || 0}</b></div>
                <div><small>新增庫位</small><b>{aiLayoutResult?.summary?.created_locations || 0}</b></div>
                <div><small>關聯庫存</small><b>{aiLayoutResult?.summary?.linked_balances || 0}</b></div>
              </div>
              <button className="btn btn-primary btn-sm" onClick={aiLayout} disabled={busy} style={{ width: "100%", marginTop: 10 }}><Icon name="sparkle" size={14}/>交給 AI 執行</button>
            </div>
          )}

          {canLocate && (
            <div className="gis-panel">
              <div className="gis-panel-head"><span>AI 識別定位</span><small>DeepSeek</small></div>
              <textarea className="input gis-ai-textarea" value={aiText} onChange={(e) => setAiText(e.target.value)}
                placeholder="例如：在呼和浩特設中心庫，在鄂爾多斯設搶修庫 EDS-01"/>
              <div className="gis-inline">
                <button className="btn btn-primary btn-sm" onClick={parseAiWarehouses} disabled={aiBusy}><Icon name="sparkle" size={14}/>{aiBusy ? "識別中" : "AI 識別"}</button>
                {aiItems.length > 0 && <button className="btn btn-sm" onClick={() => setAiItems([])}><Icon name="x" size={14}/>清空</button>}
              </div>
              {!!aiItems.length && (
                <div className="gis-ai-result">
                  {aiItems.map((item, i) => (
                    <button key={i} onClick={() => {
                      setPinForm({ name: item.name || "", lat: "", lng: "", address: item.address || "" });
                      setAddr(item.address || item.name || "");
                    }}>
                      <b>{item.name}</b>
                      <small>{item.warehouse_type || "未分類"} · {item.address || "待定位"}</small>
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}

          {canLocate && (
            <div className="gis-panel">
              <div className="gis-panel-head"><span>手動定位</span><small>{placing ? "點選中" : "WGS-84"}</small></div>
              <div className="gis-form-grid">
                <label>倉庫名稱<input className="input" value={pinForm.name} onChange={(e) => setPinForm({ ...pinForm, name: e.target.value })}/></label>
                <label>地址<input className="input" value={pinForm.address} onChange={(e) => setPinForm({ ...pinForm, address: e.target.value })}/></label>
                <label>緯度<input className="input" value={pinForm.lat} onChange={(e) => setPinForm({ ...pinForm, lat: e.target.value })}/></label>
                <label>經度<input className="input" value={pinForm.lng} onChange={(e) => setPinForm({ ...pinForm, lng: e.target.value })}/></label>
              </div>
              <div className="gis-inline">
                <input className="input" value={addr} onChange={(e) => setAddr(e.target.value)} placeholder="地址/地名搜索"/>
                <button className="btn btn-sm" onClick={geocode} disabled={geoBusy}><Icon name="search" size={14}/>{geoBusy ? "搜索中" : "搜索"}</button>
              </div>
              {!!geoResults.length && (
                <div className="gis-geocode-list">
                  {geoResults.map((g, i) => <button key={i} onClick={() => pickGeo(g)}>{g.display_name}</button>)}
                </div>
              )}
              <div className="gis-inline">
                <button className="btn btn-sm" onClick={() => { setTool(null); placingRef.current = true; setPlacing(true); }}><Icon name="map" size={14}/>點地圖取點</button>
                <button className="btn btn-primary btn-sm" onClick={savePin} disabled={busy}><Icon name="check" size={14}/>保存定位</button>
              </div>
            </div>
          )}

          <div className="gis-panel">
            <div className="gis-panel-head"><span>預警聯動</span><small>{whAlerts.length}</small></div>
            <div className="gis-alert-list">
              {whAlerts.map((a) => (
                <div className={"gis-alert-row " + (a.level || "blue")} key={a.id}>
                  <span>{GIS_LEVEL_LABEL[a.level] || "提示"}</span>
                  <b>{a.item_name || a.alert_type}</b>
                  <small>{a.suggestion || a.scope}</small>
                </div>
              ))}
              {!whAlerts.length && <div className="muted" style={{ fontSize: 13 }}>當前倉庫暫無直接關聯預警。</div>}
            </div>
          </div>
        </aside>
      </section>

      <section className="gis-detail-grid">
        <div className="gis-detail-panel">
          <div className="gis-panel-head">
            <span>{selectedWh ? selectedWh.name : "倉庫詳情"}</span>
            <small>{selectedWh ? `${selectedWh.locations_count || 0} 庫位` : "—"}</small>
          </div>
          {selectedWh ? (
            <>
              <div className="gis-kpi-line">
                <div><small>物資種類</small><b>{selectedWh.item_count || 0}</b></div>
                <div><small>庫存量</small><b>{gisNum(selectedWh.stock_total)}</b></div>
                <div><small>容量</small><b className={gisTone(selectedWh.capacity_usage)}>{selectedWh.capacity_usage == null ? "—" : `${gisNum(selectedWh.capacity_usage)}%`}</b></div>
                <div><small>低庫存</small><b className={selectedWh.low_stock_count ? "danger" : "ok"}>{selectedWh.low_stock_count || 0}</b></div>
              </div>
              <div className="gis-zone-strip">
                {selectedZones.map((z) => (
                  <span key={z.id} style={{ borderColor: z.color || "#1B6BFF" }}>
                    <b>{z.zone_code}</b>{z.zone_name} · {z.rack_count || 0} 庫位 · {z.alert_count || 0} 風險
                  </span>
                ))}
                {!selectedZones.length && <span>暫無庫區資料，可點「自動整理庫位」從庫存資料生成。</span>}
              </div>
            </>
          ) : <div className="muted">請選擇倉庫。</div>}
        </div>

        <div className="gis-detail-panel">
          <div className="gis-panel-head">
            <span>庫內庫位圖</span>
            <div className="gis-filterline">
              <input className="input" value={query} onChange={(e) => setQuery(e.target.value)} placeholder="搜索庫位/物資"/>
              <select className="input" value={status} onChange={(e) => setStatus(e.target.value)}>
                {GIS_STATUS.map(([k, label]) => <option key={k} value={k}>{label}</option>)}
              </select>
              <button className={"btn btn-sm " + (riskOnly ? "btn-primary" : "")} onClick={() => setRiskOnly((v) => !v)}><Icon name="filter" size={14}/>風險</button>
              {canManage && <button className="btn btn-sm" onClick={() => openLocationForm(null)}><Icon name="plus" size={14}/>新增庫位</button>}
            </div>
          </div>

          <div className="gis-location-grid">
            {filteredLocations.map((loc) => (
              <button key={loc.id} className={"gis-location-cell " + gisStatusTone(loc.alert_status)} onClick={() => canManage ? openLocationForm(loc) : setSelectedLoc(loc)}>
                <span className="gis-location-code">{loc.location_code}</span>
                <span className="gis-location-meta">{loc.zone_code || "未分區"} · {loc.item_count || 0} 種</span>
                <span className="gis-capbar"><i style={{ width: `${Math.min(100, Number(loc.capacity_usage || 0))}%` }}/></span>
                <span className="gis-location-items">{(loc.sample_items || []).slice(0, 2).join("、") || "暫無物資"}</span>
                {loc.low_stock_count > 0 && <em>{loc.low_stock_count}</em>}
              </button>
            ))}
            {!filteredLocations.length && <div className="gis-empty">暫無匹配庫位。</div>}
          </div>
        </div>
      </section>

      {locForm && (
        <div className="gis-modal" onClick={() => setLocForm(null)}>
          <div className="gis-modal-body" onClick={(e) => e.stopPropagation()}>
            <div className="gis-panel-head">
              <span>{locForm.id ? "編輯庫位" : "新增庫位"}</span>
              <button className="btn btn-sm" onClick={() => setLocForm(null)}><Icon name="x" size={14}/>關閉</button>
            </div>
            <div className="gis-form-grid">
              <label>庫位碼<input className="input" value={locForm.location_code} onChange={(e) => setLocForm({ ...locForm, location_code: e.target.value })}/></label>
              <label>庫區<select className="input" value={locForm.zone_id} onChange={(e) => setLocForm({ ...locForm, zone_id: e.target.value })}>
                <option value="">按庫位碼自動判斷</option>
                {selectedZones.filter((z) => typeof z.id === "number").map((z) => <option key={z.id} value={z.id}>{z.zone_code} · {z.zone_name}</option>)}
              </select></label>
              <label>貨架<input className="input" value={locForm.rack_code} onChange={(e) => setLocForm({ ...locForm, rack_code: e.target.value })}/></label>
              <label>樓層<input className="input" value={locForm.floor_no} onChange={(e) => setLocForm({ ...locForm, floor_no: e.target.value })}/></label>
              <label>X 坐標<input className="input" type="number" value={locForm.x_pos} onChange={(e) => setLocForm({ ...locForm, x_pos: e.target.value })}/></label>
              <label>Y 坐標<input className="input" type="number" value={locForm.y_pos} onChange={(e) => setLocForm({ ...locForm, y_pos: e.target.value })}/></label>
              <label>容量使用率<input className="input" type="number" min="0" max="140" value={locForm.capacity_usage} onChange={(e) => setLocForm({ ...locForm, capacity_usage: e.target.value })}/></label>
              <label>狀態<select className="input" value={locForm.alert_status} onChange={(e) => setLocForm({ ...locForm, alert_status: e.target.value })}>
                {GIS_STATUS.filter(([k]) => k !== "all").map(([k, label]) => <option key={k} value={k}>{label}</option>)}
              </select></label>
            </div>
            <div className="gis-inline" style={{ justifyContent: "flex-end" }}>
              {locForm.id && <button className="btn btn-sm" style={{ color: "var(--danger)" }} onClick={deleteLocation} disabled={busy}>刪除</button>}
              <button className="btn btn-primary" onClick={saveLocation} disabled={busy}><Icon name="check" size={15}/>保存庫位</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

window.PageWarehouseGIS = PageWarehouseGIS;
