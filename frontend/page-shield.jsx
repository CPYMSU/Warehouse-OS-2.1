/* ============================================================
   SHIELD 安全中樞 — 服務端安全態勢 + 消防員事件 + AI 高風險操作
   ============================================================ */
const {
  useEffect: useEffectShield,
  useMemo: useMemoShield,
  useRef: useRefShield,
  useState: useStateShield,
} = React;

const SHIELD_API_BASE = typeof window.WAREHOUSE_API_BASE === "string" ? window.WAREHOUSE_API_BASE : "http://127.0.0.1:8090";

const shieldRequest = (path, options = {}) => {
  const url = window.authFetch ? path : `${SHIELD_API_BASE}${path}`;
  return (window.authFetch || fetch)(url, options);
};

const shieldReadJson = (res, msg) => res.json().catch(() => ({})).then((data) => {
  if (!res.ok) throw new Error(data.error || msg || `HTTP ${res.status}`);
  return data;
});

// NDJSON 流式:SHIELD 超級終端逐事件回調(駐場 AI 對話式多步執行 / 自主診斷)
const shieldStream = (path, payload, onEvent) => {
  const url = window.authFetch ? path : `${SHIELD_API_BASE}${path}`;
  return (window.authFetch || fetch)(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  }).then((res) => {
    if (!res.ok || !res.body) {
      return res.json().catch(() => ({})).then((d) => { throw new Error(d.error || `HTTP ${res.status}`); });
    }
    const reader = res.body.getReader();
    const dec = new TextDecoder();
    let buf = "";
    const pump = () => reader.read().then(({ done, value }) => {
      if (done) return undefined;
      buf += dec.decode(value, { stream: true });
      let idx;
      while ((idx = buf.indexOf("\n")) >= 0) {
        const line = buf.slice(0, idx).trim();
        buf = buf.slice(idx + 1);
        if (line) { try { onEvent(JSON.parse(line)); } catch (e) {} }
      }
      return pump();
    });
    return pump();
  });
};

const SHIELD_STATE = {
  healthy: { label: "健康", color: "#10B981", soft: "rgba(16,185,129,.12)" },
  watch: { label: "觀察", color: "#3B82F6", soft: "rgba(59,130,246,.12)" },
  degraded: { label: "降級", color: "#EAB308", soft: "rgba(234,179,8,.14)" },
  "capacity-risk": { label: "容量風險", color: "#F59E0B", soft: "rgba(245,158,11,.14)" },
  "runtime-flapping": { label: "運行抖動", color: "#F59E0B", soft: "rgba(245,158,11,.14)" },
  incident: { label: "事件中", color: "#EF4444", soft: "rgba(239,68,68,.12)" },
  "integrity-alert": { label: "完整性告警", color: "#DC2626", soft: "rgba(220,38,38,.14)" },
  "under-attack": { label: "攻擊態勢", color: "#B91C1C", soft: "rgba(185,28,28,.14)" },
  offline: { label: "未接入", color: "#64748B", soft: "rgba(100,116,139,.12)" },
};

const shieldStateMeta = (state) => SHIELD_STATE[state] || SHIELD_STATE.watch;
const shieldTime = (value) => value ? String(value).replace("T", " ").slice(0, 19) : "—";
const shieldCompact = (value, max = 180) => {
  if (value == null || value === "") return "—";
  const text = typeof value === "object" ? JSON.stringify(value) : String(value);
  return text.length > max ? text.slice(0, max) + "..." : text;
};

const ShieldTopologyCanvas = ({ status, height = 520, topology, selectedNodeId, onSelectNode }) => {
  const ref = useRefShield(null);
  const selectRef = useRefShield(onSelectNode);
  const state = status && status.state;
  const severity = Number((status && status.severity) || 0);
  const openRisk = Number((status && status.open_ai_risk_events) || 0);
  const topologyNodes = (topology && topology.nodes) || [];

  useEffectShield(() => {
    selectRef.current = onSelectNode;
  }, [onSelectNode]);

  useEffectShield(() => {
    const canvas = ref.current;
    if (!canvas) return undefined;
    const ctx = canvas.getContext("2d", { alpha: false });
    const staticCanvas = document.createElement("canvas");
    const staticCtx = staticCanvas.getContext("2d", { alpha: false });
    const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
    let raf = 0;
    let width = 0;
    let height = 0;
    let dpr = 1;
    let nodes = [];
    let edges = [];
    let endpointDots = [];
    let packets = [];
    let bursts = [];
    let pulses = [];
    let nodeEdgeMap = [];
    let hoverNode = -1;
    let selectedNode = -1;
    const nodeMeta = {};
    topologyNodes.forEach((node) => {
      if (node && node.id) nodeMeta[node.id] = node;
    });
    const dangerBoost = Math.min(1, severity / 5 + Math.min(openRisk, 8) * .05);
    // 實時數據流強度(真實 req_rate + 事件密度,後端計)→ 驅動封包密度/速度,非裝飾隨機
    const flowRate = Math.max(.12, Math.min(1, Number((topology && topology.flow_rate) || .35)));
    const nodeActivity = (id) => Math.max(0, Math.min(1, Number((nodeMeta[id] && nodeMeta[id].activity) || 0)));
    const pointer = { x: 0, y: 0, tx: 0, ty: 0, active: false };
    const palette = {
      foundation: [229, 147, 18],
      governance: [209, 72, 60],
      collaboration: [31, 196, 179],
      intelligence: [132, 87, 231],
      boundary: [144, 158, 178],
      research: [58, 132, 255],
      validation: [128, 255, 236],
      reserved: [214, 174, 92],
      danger: [239, 68, 68],
    };
    const clamp = (value, min, max) => Math.max(min, Math.min(max, value));
    const lerp = (a, b, t) => a + (b - a) * t;
    const seededRandom = (seed) => {
      let value = seed >>> 0;
      return () => {
        value += 0x6d2b79f5;
        let next = value;
        next = Math.imul(next ^ (next >>> 15), next | 1);
        next ^= next + Math.imul(next ^ (next >>> 7), next | 61);
        return ((next ^ (next >>> 14)) >>> 0) / 4294967296;
      };
    };
    const color = (group, alpha) => {
      const rgb = dangerBoost > .58 && group === "governance" ? palette.danger : (palette[group] || palette.validation);
      return `rgba(${rgb[0]}, ${rgb[1]}, ${rgb[2]}, ${alpha})`;
    };
    const scalePoint = (x, y) => {
      const usableW = width * .86;
      const usableH = height * .82;
      return { x: width * .07 + x * usableW, y: height * .09 + y * usableH };
    };
    const addNode = (id, x, y, group, radius, kind = "primary") => {
      const point = scalePoint(x, y);
      const meta = nodeMeta[id] || {};
      nodes.push({ id, x: point.x, y: point.y, group, r: radius, kind, phase: nodes.length * .71, meta });
    };
    const effectiveGroup = (node) => {
      const nodeState = (node.meta && node.meta.state) || "";
      const nodeSeverity = Number((node.meta && node.meta.severity) || 0);
      if (nodeState === "incident" || nodeState === "under-attack" || nodeSeverity >= 4) return "danger";
      if (nodeState === "degraded" || nodeState === "watch" || nodeSeverity >= 2) return "governance";
      return node.group;
    };
    const sampleEdge = (edge, progress) => {
      const max = edge.samples.length - 1;
      const raw = clamp(progress, 0, 1) * max;
      const index = Math.floor(raw);
      const next = Math.min(index + 1, max);
      const t = raw - index;
      const a = edge.samples[index];
      const b = edge.samples[next];
      return { x: lerp(a.x, b.x, t), y: lerp(a.y, b.y, t) };
    };
    const createEdge = (aIndex, bIndex, strength, bend) => {
      const a = nodes[aIndex];
      const b = nodes[bIndex];
      const dx = b.x - a.x;
      const dy = b.y - a.y;
      const distance = Math.hypot(dx, dy) || 1;
      const control = {
        x: (a.x + b.x) * .5 + (-dy / distance) * distance * bend,
        y: (a.y + b.y) * .5 + (dx / distance) * distance * bend,
      };
      const samples = [];
      for (let i = 0; i <= 64; i += 1) {
        const t = i / 64;
        const q = 1 - t;
        samples.push({
          x: q * q * a.x + 2 * q * t * control.x + t * t * b.x,
          y: q * q * a.y + 2 * q * t * control.y + t * t * b.y,
        });
      }
      return { a: aIndex, b: bIndex, control, samples, strength };
    };
    const addEdge = (aId, bId, strength = 1, bend = 0) => {
      const a = nodes.findIndex((node) => node.id === aId);
      const b = nodes.findIndex((node) => node.id === bId);
      if (a >= 0 && b >= 0) edges.push(createEdge(a, b, strength, bend));
    };
    const addEndpointCloud = (count, centerId, group, spreadX, spreadY, seed, alpha, reserved = false) => {
      const random = seededRandom(seed);
      const center = nodes.find((node) => node.id === centerId);
      if (!center) return;
      for (let i = 0; i < count; i += 1) {
        const angle = random() * Math.PI * 2;
        const radius = Math.sqrt(random());
        endpointDots.push({
          x: clamp(center.x + Math.cos(angle) * radius * spreadX + (random() - .5) * spreadX * .18, width * .04, width * .96),
          y: clamp(center.y + Math.sin(angle) * radius * spreadY + (random() - .5) * spreadY * .18, height * .05, height * .95),
          r: reserved ? .75 + random() * .65 : .55 + random() * .75,
          group,
          alpha,
        });
      }
    };
    const buildTopology = () => {
      nodes = [];
      edges = [];
      endpointDots = [];
      packets = [];
      bursts = [];
      pulses = [];
      hoverNode = -1;
      selectedNode = -1;

      addNode("wcs", .50, .92, "foundation", 7.2);
      addNode("registry", .50, .78, "foundation", 6.4);
      addNode("governance", .50, .64, "governance", 7.6);
      addNode("api", .50, .50, "foundation", 6.8);
      addNode("event", .27, .38, "collaboration", 6.6);
      addNode("workflow", .27, .53, "collaboration", 6.2);
      addNode("agent", .73, .38, "intelligence", 7.4);
      addNode("lessons", .73, .53, "intelligence", 6.1);
      addNode("tenant", .50, .14, "boundary", 8.2);
      addNode("prompt_platform", .82, .19, "research", 4.2, "support");
      addNode("prompt_industry", .88, .31, "collaboration", 4.2, "support");
      addNode("prompt_account", .89, .44, "reserved", 4.2, "support");
      addNode("prompt_session", .83, .59, "governance", 4.2, "support");
      addNode("rq1", .11, .36, "research", 4.6, "support");
      addNode("rq2", .10, .52, "research", 4.6, "support");
      addNode("rq3", .12, .68, "research", 4.6, "support");
      addNode("structural", .36, .25, "validation", 5.1, "support");
      addNode("behavioral", .64, .25, "validation", 5.1, "support");
      addNode("l1", .66, .78, "validation", 3.8, "support");
      addNode("l2", .74, .83, "governance", 3.8, "support");
      addNode("l3", .82, .77, "collaboration", 3.8, "support");

      addEdge("wcs", "registry", 1.35);
      addEdge("registry", "governance", 1.3);
      addEdge("governance", "api", 1.35);
      addEdge("api", "event", 1.05, -.12);
      addEdge("api", "workflow", 1.0, -.08);
      addEdge("api", "agent", 1.1, .12);
      addEdge("agent", "lessons", .9);
      addEdge("event", "tenant", .9, .18);
      addEdge("workflow", "tenant", .82, .08);
      addEdge("agent", "tenant", .95, -.18);
      addEdge("lessons", "tenant", .85, -.08);
      addEdge("governance", "tenant", .8);
      addEdge("agent", "prompt_platform", .65);
      addEdge("agent", "prompt_industry", .65);
      addEdge("lessons", "prompt_account", .58);
      addEdge("lessons", "prompt_session", .58);
      addEdge("rq1", "wcs", .55, -.05);
      addEdge("rq2", "governance", .55, .05);
      addEdge("rq3", "tenant", .55, .11);
      addEdge("structural", "governance", .6);
      addEdge("behavioral", "agent", .6);
      addEdge("l1", "agent", .44);
      addEdge("l2", "governance", .44);
      addEdge("l3", "workflow", .44);

      nodeEdgeMap = Array.from({ length: nodes.length }, () => []);
      edges.forEach((edge, index) => {
        nodeEdgeMap[edge.a].push(index);
        nodeEdgeMap[edge.b].push(index);
      });
      selectedNode = nodes.findIndex((node) => node.id === selectedNodeId);

      addEndpointCloud(58, "wcs", "foundation", width * .20, height * .08, 101, .24);
      addEndpointCloud(54, "registry", "foundation", width * .18, height * .09, 102, .22);
      addEndpointCloud(35, "api", "foundation", width * .20, height * .11, 103, .24);
      addEndpointCloud(20, "tenant", "reserved", width * .22, height * .12, 104, .18, true);
      addEndpointCloud(45, "agent", "intelligence", width * .18, height * .14, 105, .18);
      addEndpointCloud(18, "rq2", "boundary", width * .10, height * .20, 106, .13);
      addEndpointCloud(12, "tenant", "governance", width * .12, height * .08, 107, .15);
      addEndpointCloud(25, "prompt_industry", "collaboration", width * .10, height * .16, 108, .14);

      const random = seededRandom(22063);
      // 封包數與速度由真實數據流強度(flowRate)驅動;每條邊的權重 = 兩端節點真實活躍度
      // → 流量集中在真正在動的鏈路上(API/治理/事件…),不再是均勻隨機裝飾。
      const edgeFlow = edges.map((e) => .3 + nodeActivity(nodes[e.a].id) + nodeActivity(nodes[e.b].id));
      const flowTotal = edgeFlow.reduce((s, w) => s + w, 0) || 1;
      const pickEdge = () => {
        let r = random() * flowTotal;
        for (let i = 0; i < edgeFlow.length; i += 1) { r -= edgeFlow[i]; if (r <= 0) return i; }
        return edges.length - 1;
      };
      const packetCount = Math.round(clamp(edges.length * (.5 + flowRate * 1.3), 14, 64));
      packets = Array.from({ length: packetCount }, (_, index) => ({
        edge: pickEdge(),
        progress: random(),
        speed: .00006 + random() * .0001 + flowRate * .00022 + dangerBoost * .00006,
        size: 1.0 + random() * 1.3,
        phase: index * .41,
      }));
    };
    const renderStaticLayer = () => {
      const bg = staticCtx.createLinearGradient(0, 0, width, height);
      bg.addColorStop(0, "#010304");
      bg.addColorStop(.48, "#061112");
      bg.addColorStop(1, "#080906");
      staticCtx.fillStyle = bg;
      staticCtx.fillRect(0, 0, width, height);

      const glow = staticCtx.createRadialGradient(width * .5, height * .5, 0, width * .5, height * .5, Math.min(width, height) * .75);
      glow.addColorStop(0, `rgba(${dangerBoost > .45 ? "239, 68, 68" : "82, 255, 239"}, .095)`);
      glow.addColorStop(.48, "rgba(56, 142, 135, .032)");
      glow.addColorStop(1, "rgba(82, 255, 239, 0)");
      staticCtx.fillStyle = glow;
      staticCtx.fillRect(0, 0, width, height);
      staticCtx.save();
      staticCtx.globalCompositeOperation = "lighter";
      staticCtx.lineCap = "round";
      staticCtx.lineJoin = "round";
      endpointDots.forEach((dot) => {
        staticCtx.fillStyle = color(dot.group, dot.alpha);
        staticCtx.beginPath();
        staticCtx.arc(dot.x, dot.y, dot.r, 0, Math.PI * 2);
        staticCtx.fill();
      });
      edges.forEach((edge) => {
        const a = nodes[edge.a];
        const b = nodes[edge.b];
        const gradient = staticCtx.createLinearGradient(a.x, a.y, b.x, b.y);
        gradient.addColorStop(0, color(effectiveGroup(a), 0));
        gradient.addColorStop(.18, color(effectiveGroup(a), .09 * edge.strength));
        gradient.addColorStop(.74, color(effectiveGroup(b), .075 * edge.strength));
        gradient.addColorStop(1, color(effectiveGroup(b), 0));
        staticCtx.strokeStyle = gradient;
        staticCtx.lineWidth = edge.strength > 1 ? 1.25 : .85;
        staticCtx.beginPath();
        staticCtx.moveTo(a.x, a.y);
        staticCtx.quadraticCurveTo(edge.control.x, edge.control.y, b.x, b.y);
        staticCtx.stroke();
      });
      nodes.forEach((node) => {
        const nodeGroup = effectiveGroup(node);
        const nodeSeverity = Number((node.meta && node.meta.severity) || 0);
        const counter = node.meta && node.meta.counters ? Object.keys(node.meta.counters).reduce((sum, key) => {
          const value = node.meta.counters[key];
          return sum + (typeof value === "number" && value > 0 ? value : 0);
        }, 0) : 0;
        const act = nodeActivity(node.id);   // 真實活躍度 → 節點光暈隨負載增強
        const halo = staticCtx.createRadialGradient(node.x, node.y, 0, node.x, node.y, node.r * (7 + act * 3));
        halo.addColorStop(0, color(nodeGroup, (node.kind === "primary" ? .24 : .14) + nodeSeverity * .025 + act * .22));
        halo.addColorStop(1, color(nodeGroup, 0));
        staticCtx.fillStyle = halo;
        staticCtx.beginPath();
        staticCtx.arc(node.x, node.y, node.r * 7, 0, Math.PI * 2);
        staticCtx.fill();
        staticCtx.fillStyle = color(nodeGroup, node.kind === "primary" ? .78 : .55);
        staticCtx.beginPath();
        staticCtx.arc(node.x, node.y, node.r, 0, Math.PI * 2);
        staticCtx.fill();
        if (nodeSeverity || counter) {
          staticCtx.fillStyle = color(nodeSeverity >= 4 ? "danger" : "governance", .92);
          staticCtx.beginPath();
          staticCtx.arc(node.x + node.r * .82, node.y - node.r * .82, node.kind === "primary" ? 3.2 : 2.4, 0, Math.PI * 2);
          staticCtx.fill();
        }
      });
      staticCtx.restore();
    };
    const resize = () => {
      const box = canvas.getBoundingClientRect();
      dpr = Math.min(window.devicePixelRatio || 1, 2);
      width = Math.max(320, box.width || canvas.clientWidth || 320);
      height = Math.max(360, box.height || canvas.clientHeight || 360);
      canvas.width = Math.max(1, Math.floor(width * dpr));
      canvas.height = Math.max(1, Math.floor(height * dpr));
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      staticCanvas.width = canvas.width;
      staticCanvas.height = canvas.height;
      staticCtx.setTransform(dpr, 0, 0, dpr, 0, 0);
      pointer.x = pointer.tx = width * .5;
      pointer.y = pointer.ty = height * .5;
      buildTopology();
      renderStaticLayer();
    };
    const findNearestNode = (x, y) => {
      let nearest = -1;
      let nearestDistance = 54;
      nodes.forEach((node, index) => {
        const distance = Math.hypot(node.x - x, node.y - y);
        const hit = node.kind === "primary" ? 58 : 36;
        if (distance < Math.min(nearestDistance, hit)) {
          nearest = index;
          nearestDistance = distance;
        }
      });
      return nearest;
    };
    const drawPackets = (time) => {
      ctx.save();
      ctx.globalCompositeOperation = "lighter";
      ctx.lineCap = "round";
      const speedScale = reduceMotion.matches ? 0 : 1;
      packets.forEach((packet) => {
        const edge = edges[packet.edge];
        if (!edge) return;
        packet.progress = (packet.progress + packet.speed * speedScale * 16) % 1;
        const head = sampleEdge(edge, packet.progress);
        const tail = sampleEdge(edge, Math.max(0, packet.progress - .06));
        const a = nodes[edge.a];
        const b = nodes[edge.b];
        const alpha = .36 + Math.sin(time * .003 + packet.phase) * .1 + dangerBoost * .18;
        const gradient = ctx.createLinearGradient(tail.x, tail.y, head.x, head.y);
        gradient.addColorStop(0, color(effectiveGroup(a), 0));
        gradient.addColorStop(1, color(dangerBoost > .55 ? "danger" : effectiveGroup(b), alpha));
        ctx.strokeStyle = gradient;
        ctx.lineWidth = packet.size;
        ctx.beginPath();
        ctx.moveTo(tail.x, tail.y);
        ctx.lineTo(head.x, head.y);
        ctx.stroke();
        ctx.fillStyle = dangerBoost > .55 ? "rgba(255, 245, 245, .78)" : "rgba(230, 255, 250, .62)";
        ctx.beginPath();
        ctx.arc(head.x, head.y, packet.size * .75, 0, Math.PI * 2);
        ctx.fill();
      });
      ctx.restore();
    };
    const drawInteractiveLinks = (time) => {
      const activeNodes = [selectedNode, hoverNode].filter((node, index, list) => node >= 0 && list.indexOf(node) === index);
      if (!activeNodes.length) return;
      ctx.save();
      ctx.globalCompositeOperation = "lighter";
      ctx.lineCap = "round";
      activeNodes.forEach((nodeIndex) => {
        const node = nodes[nodeIndex];
        const isHover = nodeIndex === hoverNode;
        (nodeEdgeMap[nodeIndex] || []).forEach((edgeIndex) => {
          const edge = edges[edgeIndex];
          const a = nodes[edge.a];
          const b = nodes[edge.b];
          const gradient = ctx.createLinearGradient(a.x, a.y, b.x, b.y);
          gradient.addColorStop(0, color(effectiveGroup(a), 0));
          gradient.addColorStop(.35, color(effectiveGroup(a), isHover ? .28 : .17));
          gradient.addColorStop(.72, color(effectiveGroup(b), isHover ? .24 : .14));
          gradient.addColorStop(1, color(effectiveGroup(b), 0));
          ctx.strokeStyle = gradient;
          ctx.lineWidth = isHover ? 2 : 1.25;
          ctx.beginPath();
          ctx.moveTo(a.x, a.y);
          ctx.quadraticCurveTo(edge.control.x, edge.control.y, b.x, b.y);
          ctx.stroke();
        });
        const pulse = .65 + Math.sin(time * .004 + node.phase) * .35;
        ctx.strokeStyle = color(effectiveGroup(node), isHover ? .62 : .36);
        ctx.lineWidth = isHover ? 1.35 : 1;
        ctx.beginPath();
        ctx.arc(node.x, node.y, node.r * (2.4 + pulse * .8), 0, Math.PI * 2);
        ctx.stroke();
        ctx.fillStyle = color(effectiveGroup(node), isHover ? .92 : .68);
        ctx.beginPath();
        ctx.arc(node.x, node.y, node.r + 2.2 + pulse, 0, Math.PI * 2);
        ctx.fill();
      });
      ctx.restore();
    };
    const emitBurstsFromNode = (nodeIndex) => {
      (nodeEdgeMap[nodeIndex] || []).forEach((edgeIndex) => {
        const edge = edges[edgeIndex];
        bursts.push({ edge: edgeIndex, fromA: edge.a === nodeIndex, progress: 0, speed: .014 + Math.random() * .012, alpha: .72, group: nodes[nodeIndex].group });
      });
    };
    // 實時信息流:真正活躍的節點(最近有事件/高負載)週期性向外脈衝 —— 你能看到事件在圖上流動
    const emitActivityPulses = () => {
      if (reduceMotion.matches) return;
      nodes.forEach((node, i) => {
        const act = nodeActivity(node.id);
        if (act > .25 && Math.random() < act) emitBurstsFromNode(i);
      });
    };
    const drawBursts = () => {
      ctx.save();
      ctx.globalCompositeOperation = "lighter";
      ctx.lineCap = "round";
      for (let i = bursts.length - 1; i >= 0; i -= 1) {
        const burst = bursts[i];
        const edge = edges[burst.edge];
        if (!edge) {
          bursts.splice(i, 1);
          continue;
        }
        burst.progress += burst.speed;
        burst.alpha *= .985;
        const headT = burst.fromA ? burst.progress : 1 - burst.progress;
        const tailT = burst.fromA ? Math.max(0, burst.progress - .11) : Math.min(1, 1 - burst.progress + .11);
        const head = sampleEdge(edge, headT);
        const tail = sampleEdge(edge, tailT);
        ctx.strokeStyle = color(burst.group, burst.alpha * .72);
        ctx.lineWidth = 2.2;
        ctx.beginPath();
        ctx.moveTo(tail.x, tail.y);
        ctx.lineTo(head.x, head.y);
        ctx.stroke();
        ctx.fillStyle = "rgba(245,255,252,.88)";
        ctx.beginPath();
        ctx.arc(head.x, head.y, 2.6, 0, Math.PI * 2);
        ctx.fill();
        if (burst.progress >= 1 || burst.alpha < .08) bursts.splice(i, 1);
      }
      ctx.restore();
    };
    const addPulse = (x, y) => pulses.push({ x, y, r: 8, a: .32 });
    const drawPulses = () => {
      ctx.save();
      ctx.globalCompositeOperation = "lighter";
      for (let i = pulses.length - 1; i >= 0; i -= 1) {
        const pulse = pulses[i];
        pulse.r += 8;
        pulse.a *= .955;
        ctx.strokeStyle = `rgba(157,255,240,${pulse.a})`;
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.arc(pulse.x, pulse.y, pulse.r, 0, Math.PI * 2);
        ctx.stroke();
        if (pulse.a < .012) pulses.splice(i, 1);
      }
      ctx.restore();
    };
    const drawFocus = () => {
      if (!pointer.active) return;
      ctx.save();
      ctx.globalCompositeOperation = "lighter";
      const radius = Math.min(width, height) * .15;
      const focus = ctx.createRadialGradient(pointer.x, pointer.y, 0, pointer.x, pointer.y, radius);
      focus.addColorStop(0, "rgba(157,255,240,.075)");
      focus.addColorStop(1, "rgba(157,255,240,0)");
      ctx.fillStyle = focus;
      ctx.beginPath();
      ctx.arc(pointer.x, pointer.y, radius, 0, Math.PI * 2);
      ctx.fill();
      ctx.restore();
    };
    const render = (time) => {
      pointer.x = lerp(pointer.x, pointer.tx, .12);
      pointer.y = lerp(pointer.y, pointer.ty, .12);
      ctx.drawImage(staticCanvas, 0, 0, width, height);
      drawInteractiveLinks(time);
      drawPackets(time);
      drawBursts();
      drawFocus();
      drawPulses();
      raf = requestAnimationFrame(render);
    };
    const setPointer = (event) => {
      const rect = canvas.getBoundingClientRect();
      pointer.tx = event.clientX - rect.left;
      pointer.ty = event.clientY - rect.top;
      pointer.active = true;
      hoverNode = findNearestNode(pointer.tx, pointer.ty);
    };
    const pointerLeave = () => {
      pointer.active = false;
      hoverNode = -1;
      pointer.tx = width * .5;
      pointer.ty = height * .5;
    };
    const pointerDown = (event) => {
      setPointer(event);
      if (hoverNode >= 0) {
        selectedNode = hoverNode;
        emitBurstsFromNode(selectedNode);
        addPulse(nodes[selectedNode].x, nodes[selectedNode].y);
        if (selectRef.current) selectRef.current(nodes[selectedNode].id);
      } else {
        addPulse(pointer.x, pointer.y);
      }
    };
    resize();
    emitActivityPulses();
    const activityTimer = setInterval(emitActivityPulses, 2600);
    const observer = new ResizeObserver(resize);
    observer.observe(canvas);
    canvas.addEventListener("pointermove", setPointer);
    canvas.addEventListener("pointerenter", setPointer);
    canvas.addEventListener("pointerleave", pointerLeave);
    canvas.addEventListener("pointerdown", pointerDown);
    raf = requestAnimationFrame(render);
    return () => {
      cancelAnimationFrame(raf);
      clearInterval(activityTimer);
      observer.disconnect();
      canvas.removeEventListener("pointermove", setPointer);
      canvas.removeEventListener("pointerenter", setPointer);
      canvas.removeEventListener("pointerleave", pointerLeave);
      canvas.removeEventListener("pointerdown", pointerDown);
    };
  }, [state, severity, openRisk, selectedNodeId, topologyNodes]);

  return <canvas ref={ref} style={{ width: "100%", height, display: "block", borderRadius: 12, cursor: "crosshair", touchAction: "none" }}/>;
};

const ShieldMetric = ({ icon, label, value, sub, tone = "blue" }) => {
  const color = tone === "red" ? "#EF4444" : tone === "yellow" ? "#F59E0B" : tone === "green" ? "#10B981" : "#2563EB";
  return (
    <div className="card" style={{ padding: 16, minHeight: 118 }}>
      <div className="row gap-10" style={{ alignItems: "center", justifyContent: "space-between" }}>
        <div style={{ fontSize: 12, color: "var(--ink-3)", fontWeight: 800 }}>{label}</div>
        <span style={{ width: 32, height: 32, display: "grid", placeItems: "center", borderRadius: 8, color, background: `${color}18` }}>
          <Icon name={icon} size={17}/>
        </span>
      </div>
      <div style={{ marginTop: 12, fontSize: 28, fontWeight: 900, color: "var(--ink)", lineHeight: 1 }}>{value}</div>
      <div className="muted" style={{ marginTop: 8, fontSize: 12 }}>{sub || "—"}</div>
    </div>
  );
};

const ShieldStatePill = ({ state }) => {
  const meta = shieldStateMeta(state);
  return (
    <span className="row gap-6" style={{
      alignItems: "center", width: "fit-content", border: `1px solid ${meta.color}44`,
      background: meta.soft, color: meta.color, borderRadius: 8, padding: "5px 9px", fontSize: 12, fontWeight: 900,
    }}>
      <span style={{ width: 7, height: 7, borderRadius: "50%", background: meta.color, boxShadow: `0 0 12px ${meta.color}` }}/>
      {meta.label}
    </span>
  );
};

const ShieldSignal = ({ icon, label, value, sub, tone = "blue" }) => (
  <div className={`shield-signal shield-signal-${tone}`}>
    <div className="shield-signal-head">
      <span><Icon name={icon} size={16}/></span>
      <b>{label}</b>
    </div>
    <strong>{value}</strong>
    <small>{sub || "—"}</small>
  </div>
);

const ShieldPanelTitle = ({ icon, title, right }) => (
  <div className="shield-panel-title">
    <div>
      <span><Icon name={icon} size={15}/></span>
      <b>{title}</b>
    </div>
    {right}
  </div>
);

const shieldParseJson = (value) => {
  if (typeof value !== "string") return value && typeof value === "object" ? value : null;
  try { return JSON.parse(value); } catch (_) { return null; }
};

const shieldTimelineSummary = (item) => {
  const kind = String((item && item.kind) || "");
  const content = String((item && item.content) || "");
  const parsed = shieldParseJson(content);
  if (kind === "diagnose" && /未配置|不可用|not configured|api key/i.test(content)) {
    return "智能引擎未配置，已记录本地观测占位，等待接入共用密钥。";
  }
  if (kind === "trigger" && parsed) {
    const alphas = parsed.alphas || {};
    const active = Object.keys(alphas).filter((key) => Number(alphas[key]) > 0)
      .map((key) => `${key} ${Number(alphas[key]).toFixed(2)}`).join(" · ");
    return `${parsed.type || "trigger"} 触发 · ${active || "无显著脉冲"}`;
  }
  if (kind === "detect" && parsed) {
    const inputs = parsed.inputs || {};
    const top = Object.keys(inputs).filter((key) => Number(inputs[key]) > 0)
      .map((key) => `${key}:${Number(inputs[key]).toFixed(2)}`).slice(0, 3).join(" · ");
    return `${parsed.state || "状态异常"} · ${top || "信号已采集"}`;
  }
  if (kind.indexOf("repair_") === 0 && parsed) {
    return `${parsed.action || "repair"} · ${parsed.ok === false ? "未完成" : "已记录"} · ${parsed.reason || parsed.level || ""}`;
  }
  return shieldCompact(content, 190);
};

const shieldRiskSummary = (risk) => {
  const args = shieldParseJson(risk && risk.args_json);
  if (!args) return shieldCompact(risk && risk.args_json, 120);
  if (args.sql) return `SQL 写操作 · ${String(args.sql).replace(/\s+/g, " ").slice(0, 110)}`;
  if (args.code) return `脚本执行请求 · ${String(args.code).length} 字符 · 已进入覆核队列`;
  if (args.id != null) return `对象 #${args.id} · 等待管理员覆核`;
  return shieldCompact(args, 120);
};

const ShieldStreamItem = ({ item }) => (
  <div className={`shield-stream-item shield-stream-${String(item.kind || "").replace(/[^a-z0-9_-]/gi, "-")}`}>
    <div className="shield-stream-dot"/>
    <div>
      <div className="shield-stream-meta">
        <b>{item.kind || "event"}</b>
        <span>{shieldTime(item.ts)}</span>
      </div>
      <p>{shieldTimelineSummary(item)}</p>
    </div>
  </div>
);

const ShieldIncidentCard = ({ inc }) => (
  <div className="shield-incident-card">
    <div className="shield-incident-top">
      <b>INC-{inc.id}</b>
      <ShieldStatePill state={inc.state}/>
    </div>
    <div className="shield-incident-title">{inc.title || inc.signature || "—"}</div>
    <div className="shield-incident-meta">
      <span>{shieldTime(inc.opened_at)}</span>
      <span>{inc.closed_at ? shieldTime(inc.closed_at) : "進行中"}</span>
    </div>
  </div>
);

const ShieldRiskCard = ({ risk }) => (
  <div className="shield-risk-card">
    <div className="shield-risk-top">
      <b>{risk.command || "unknown"}</b>
      <span className={risk.status === "open" ? "badge badge-warn" : "badge badge-ok"}>{risk.status}</span>
    </div>
    <div className="shield-risk-meta">{shieldTime(risk.created_at)} · {risk.actor_name || "AI"}</div>
    <p>{shieldRiskSummary(risk)}</p>
  </div>
);

const ShieldNodeInspector = ({ node, timeline, risks, onAction }) => {
  if (!node) {
    return (
      <div className="shield-node-inspector">
        <ShieldPanelTitle icon="scan" title="拓撲節點" right={<span className="shield-chip">等待選擇</span>}/>
        <div className="shield-empty">點擊拓撲節點查看後端資源、事件與安全動作。</div>
      </div>
    );
  }
  const counters = Object.entries(node.counters || {}).filter(([, value]) => value !== "" && value != null);
  return (
    <div className="shield-node-inspector">
      <ShieldPanelTitle icon="scan" title={node.label || node.id} right={<span className="shield-chip">{node.state || "unknown"}</span>}/>
      <p className="shield-node-summary">{node.summary || "此節點已接入 SHIELD 後端拓撲。"}</p>
      <div className="shield-node-facts">
        <span><b>{node.severity || 0}</b><small>Severity</small></span>
        <span><b>{timeline.length}</b><small>Events</small></span>
        <span><b>{risks.length}</b><small>Risks</small></span>
      </div>
      {!!counters.length && (
        <div className="shield-node-counters">
          {counters.slice(0, 5).map(([key, value]) => (
            <span key={key}><b>{key}</b>{String(value)}</span>
          ))}
        </div>
      )}
      <div className="shield-node-actions">
        {(node.actions || []).map((action) => (
          <button key={action.id} type="button" onClick={() => onAction && onAction(action)}>
            <Icon name={action.kind === "client-refresh" ? "refresh" : action.kind === "navigate-settings" ? "gear" : "arrow"} size={14}/>
            {action.label || action.id}
          </button>
        ))}
      </div>
      <div className="shield-node-related">
        <b>關聯事件</b>
        {timeline.length ? timeline.slice(0, 3).map((item, idx) => (
          <p key={idx}>{item.kind} · {shieldTimelineSummary(item)}</p>
        )) : <p>暫無此節點事件。</p>}
      </div>
      <div className="shield-node-related">
        <b>關聯風險</b>
        {risks.length ? risks.slice(0, 2).map((risk) => (
          <p key={risk.id}>{risk.command || "risk"} · {shieldRiskSummary(risk)}</p>
        )) : <p>暫無此節點風險。</p>}
      </div>
    </div>
  );
};

const SHIELD_AUTO_KIND = {
  detect: { tone: "warn", label: "偵測" },
  trigger: { tone: "warn", label: "觸發" },
  diagnose: { tone: "ai", label: "診斷" },
  pulse: { tone: "ai", label: "脈衝" },
  transition: { tone: "muted", label: "狀態轉移" },
  resolve: { tone: "ok", label: "解除" },
  repair_plan: { tone: "warn", label: "修復計劃" },
  repair_execute: { tone: "ok", label: "修復執行" },
  repair_verify: { tone: "ok", label: "修復復檢" },
  repair_failed: { tone: "err", label: "修復失敗" },
  repair_resolved: { tone: "ok", label: "修復完成" },
};

const shieldGuardianTone = (line) => {
  const s = String(line || "");
  if (/INTEGRITY VIOLATION|HEALTH FAIL|WATCHDOG/.test(s)) return "err";
  if (/RESTORED|RECOVER/.test(s)) return "ok";
  return "muted";
};

// 自主巡檢:把後端時間線(消防員自主動作)+ 守護日誌合成為終端可讀的活動流
const shieldAutoFeed = (timeline, guardianTail) => {
  const items = [];
  (timeline || []).forEach((it) => {
    const kind = String(it.kind || "");
    const meta = SHIELD_AUTO_KIND[kind] || (kind.indexOf("repair_") === 0 ? { tone: "ok", label: "修復" } : { tone: "muted", label: kind || "事件" });
    items.push({ tone: meta.tone, label: meta.label, ts: it.ts, text: shieldTimelineSummary(it) });
  });
  (guardianTail || []).slice(-4).forEach((line) => {
    const m = String(line).match(/^(\S+)\s+(.*)$/);
    items.push({ tone: shieldGuardianTone(line), label: "守護", ts: m ? m[1] : "", text: m ? m[2] : String(line) });
  });
  return items.slice(0, 6);
};

const ShieldTerminal = ({ status, timeline, guardianTail, engineReady, onAfterRun }) => {
  const [lines, setLines] = useStateShield([
    { id: "boot", kind: "sys", text: "SHIELD 超級終端就緒 — 自然語言指揮駐場安全 AI;點「代理」讓將軍拆解目標、派遣只讀 Agent 大軍取證綜合(例:徹查潛伏威脅並給出根因)。" },
  ]);
  const [input, setInput] = useStateShield("");
  const [busy, setBusy] = useStateShield(false);
  const [apJobs, setApJobs] = useStateShield([]);
  const [autoPilot, setAutoPilot] = useStateShield(true);
  const [frozen, setFrozen] = useStateShield(false);
  const convRef = useRefShield(null);
  const seqRef = useRefShield(0);
  const scrollRef = useRefShield(null);
  const autoRunRef = useRefShield(null);
  const seenCampRef = useRefShield(null);

  const autoFeed = shieldAutoFeed(timeline, guardianTail);

  useEffectShield(() => {
    const el = scrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [lines]);

  const push = (kind, text, tone) => {
    seqRef.current += 1;
    setLines((prev) => [...prev.slice(-200), { id: `l${seqRef.current}`, kind, text, tone }]);
  };

  // 每分鐘自檢:駐場 AI 主動拉取只讀健康快照(/api/shield/digest),把結果回顯成終端一行。
  // 純只讀、無模型開銷;異常時變黃/紅,健康時綠色一行帶過。
  useEffectShield(() => {
    let alive = true;
    const tick = () => {
      shieldRequest("/api/shield/digest")
        .then((res) => shieldReadJson(res, "自檢失敗"))
        .then((d) => {
          if (!alive) return;
          const inc = (d.open_incidents || []).length;
          const risk = Number(d.open_ai_risk_events || 0);
          const sev = Number(d.severity || 0);
          const eng = !!(d.ai_engine || {}).connected;
          const ffOk = !!d.firefighter_available;
          const guardAlert = (d.guardian_tail || []).some((l) => /INTEGRITY VIOLATION|HEALTH FAIL|WATCHDOG/.test(String(l)));
          const tone = (inc || sev >= 3 || guardAlert) ? "err" : (sev || risk || !eng || !ffOk) ? "warn" : "ok";
          const hms = new Date().toLocaleTimeString("zh-CN", { hour12: false });
          const text = `自檢 ${hms} · ${d.state || "?"} · 嚴重度${sev} · 事件${inc} · 風險${risk} · 引擎${eng ? "在線" : "未接入"} · 守護${ffOk ? "在線" : "離線"}${guardAlert ? " · ⚠守護告警" : ""}`;
          push("selfcheck", text, tone);
        })
        .catch((e) => { if (alive) push("selfcheck", `自檢失敗:${e.message || e}`, "err"); });
    };
    tick();
    const timer = setInterval(tick, 60000);
    return () => { alive = false; clearInterval(timer); };
  }, []);

  // 自主升級任務:消防員把 L1 窮盡的事件入隊;這裡輪詢列出,供一鍵自主診斷(只讀)。
  useEffectShield(() => {
    let alive = true;
    const fetchJobs = () => {
      shieldRequest("/api/shield/autopilot/jobs?limit=12")
        .then((res) => shieldReadJson(res, ""))
        .then((d) => { if (alive) setApJobs((d && d.rows) || []); })
        .catch(() => {});
    };
    fetchJobs();
    const timer = setInterval(fetchJobs, 30000);
    return () => { alive = false; clearInterval(timer); };
  }, []);

  const runAutopilotDiagnose = (job) => {
    if (!job || busy) return;
    setBusy(true);
    push("user", `🛰 自主診斷升級事件 INC-${job.incident_id}(${job.reason || "L1 窮盡"})`);
    shieldStream("/api/shield/autopilot/diagnose/stream", { job_id: job.id }, (ev) => {
      if (ev.event === "step_start") {
        const args = ev.args && Object.keys(ev.args).length ? " " + JSON.stringify(ev.args).slice(0, 160) : "";
        push("cmd", `${ev.command || ev.tool_name}${args}`);
      } else if (ev.event === "step") {
        if (ev.ok) push("result", `← ${ev.status || "ok"}${ev.preview ? " · " + String(ev.preview).slice(0, 120) : ""}`);
        else push("error", `✗ ${ev.command || ev.tool_name} · ${ev.preview || ev.status || "失敗"}`);
      } else if (ev.event === "final") {
        if (ev.message) push(ev.ok === false ? "error" : "final", ev.message);
      } else if (ev.event === "error") {
        push("error", `診斷錯誤:${ev.error || "流式中斷"}`);
      }
    }).catch((e) => push("error", `診斷錯誤:${e.message || e}`))
      .finally(() => { setBusy(false); if (onAfterRun) onAfterRun(); });
  };

  const apPending = apJobs.filter((j) => !j.diagnosed_at);

  // 自主運行:偵測到升級事件(L1 窮盡)→ 駐場 AI 自動在終端開跑取證,無需點按鈕。
  // 單發保護:每個 job 一個會話;診斷後後端記錄 diagnosed_at,下輪輪詢即移出待辦。
  useEffectShield(() => {
    if (!autoPilot || busy || !engineReady) return;
    if (!autoRunRef.current) autoRunRef.current = { ids: {}, count: 0 };
    if (autoRunRef.current.count >= 5) return;   // 本會話自動跑上限(防積壓事件成本失控);更多可手動或刷新重置
    const job = apPending.find((j) => !autoRunRef.current.ids[j.id]);
    if (job) {
      autoRunRef.current.ids[job.id] = true;
      autoRunRef.current.count += 1;
      push("sys", `🛰 偵測到升級事件 INC-${job.incident_id}(${job.reason || "L1 窮盡"}),駐場 AI 自動診斷中…`);
      runAutopilotDiagnose(job);
    }
  }, [apJobs, busy, engineReady, autoPilot]);

  const runDiagnoseNow = () => {
    if (busy) return;
    setBusy(true);
    push("user", "🩺 立即診斷(當前態勢)");
    shieldRequest("/api/shield/diagnose/now")
      .then((res) => shieldReadJson(res, "診斷失敗"))
      .then((d) => {
        if (!d || d.ok === false || d.error) { push("error", `診斷失敗:${(d && d.error) || "未知錯誤"}`); return; }
        push("final", `【判讀】${d.diagnosis || "(模型未返回)"}`);
        push("result", `建議動作:${d.recommended_action || "none"} · 嚴重度 ${d.severity ?? "?"}/5 · 信心 ${d.confidence ?? "?"}`);
        if (d.report_delta) push("sys", String(d.report_delta).slice(0, 600));
      })
      .catch((e) => push("error", `診斷失敗:${e.message || e}`))
      .finally(() => setBusy(false));
  };

  // 🎖 開戰役(SHIELD Commander Phase 0,只讀):將軍把指令拆成 objectives → 派遣只讀偵察
  // Agent 大軍 → 各 brief 向上綜合 → 去品牌化指揮報告。全程零寫,直播在本終端。
  const runCampaign = (text) => {
    if (busy) return;
    const directive = (text || "").trim();
    setBusy(true);
    push("user", `代理 ▸ ${directive || "全面安全態勢核查"}`);
    if (directive && directive === input.trim()) setInput("");
    shieldStream("/api/shield/campaign/stream", { directive }, (ev) => {
      if (ev.event === "campaign_start") {
        push("sys", `戰役 #${ev.campaign_id} 啟動 · 將軍接管,開始指揮 Agent 大軍`);
      } else if (ev.event === "phase") {
        push("sys", `▶ ${ev.label || ev.phase}${ev.note ? " · " + ev.note : ""}`, "warn");
      } else if (ev.event === "objectives") {
        const obs = ev.objectives || [];
        push("sys", `將軍拆解 ${obs.length} 個作戰目標:`);
        obs.forEach((o, i) => push("cmd", `${i + 1}. [${o.role || "recon"}] ${o.title || ""}`));
      } else if (ev.event === "lieutenant_start") {
        push("cmd", `▷ 派遣 [${ev.role}] → ${ev.objective}`);
      } else if (ev.event === "lieutenant_brief") {
        push("result", `↳ [${ev.role}] ${String(ev.brief || "").slice(0, 700)}`);
      } else if (ev.event === "act_decide") {
        push("sys", ev.action === "none"
          ? `⚖ 決策:無需 L1 動作 · ${ev.reason || ""}`
          : `⚖ 決策:建議執行 ${ev.action}${ev.confidence != null ? ` · 信心 ${ev.confidence}` : ""} · ${ev.reason || ""}`, "warn");
      } else if (ev.event === "act_verify") {
        push(ev.approve ? "result" : "error", `🔎 獨立驗證 ${ev.action}:${ev.approve ? "通過" : "否決 → 升級人工"} · ${ev.reason || ""}`);
      } else if (ev.event === "act_exec") {
        if (ev.skipped) push("sys", `⚙ ${ev.action} 未執行(閘門未滿足:${ev.skipped})`);
        else push(ev.ok ? "result" : "error", `⚙ 執行 ${ev.action} · ${ev.applied ? "已套用" : "dry-run"} · ${ev.ok ? "成功" : "失敗"}`);
      } else if (ev.event === "act_health") {
        push(ev.recovered ? "final" : "error", `🩺 復檢 ${ev.action}:${ev.recovered ? "已恢復健康 ✓" : "未恢復 → 已升級人工"}`);
      } else if (ev.event === "report") {
        push("final", `【指揮報告】\n${ev.report_md || ""}`);
      } else if (ev.event === "final") {
        if (ev.ok === false) { if (ev.message) push("error", ev.message); }
        else {
          const a = ev.act;
          const actNote = a && a.acted ? ` · 執行 ${a.decided}(${a.recovered ? "已恢復" : "升級人工"})`
            : a && a.decided && a.decided !== "none" ? ` · 建議 ${a.decided}` : "";
          push("sys", `戰役 #${ev.campaign_id} 結束 · ${ev.agents || 0} 個 Agent · ${ev.objectives || 0} 目標 · ${ev.tokens || 0} tokens${actNote}`);
        }
      } else if (ev.event === "error") {
        push("error", `戰役錯誤:${ev.error || "流式中斷"}`);
      }
    }).catch((e) => push("error", `戰役錯誤:${e.message || e}`))
      .finally(() => { setBusy(false); if (onAfterRun) onAfterRun(); });
  };

  // 🛑 總凍結 kill-switch:凍結後運行中的戰役在階段邊界即停,自治點火暫停(讀寫皆停)。
  const toggleFreeze = () => {
    const next = !frozen;
    setFrozen(next);
    shieldRequest("/api/shield/freeze", {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ freeze: next }),
    })
      .then((res) => shieldReadJson(res, "凍結切換失敗"))
      .then((d) => {
        setFrozen(!!(d && d.frozen));
        push("sys", next
          ? "🛑 已凍結 SHIELD Commander(運行中戰役將在階段邊界停止,自治點火暫停)"
          : "▶ 已解凍 SHIELD Commander(恢復自治)", next ? "err" : "ok");
      })
      .catch((e) => push("error", `凍結切換失敗:${e.message || e}`));
  };

  // 查看某場戰役:把各波 brief + 指揮報告呈現到終端(供自治戰役自動回放,或手動查看)。
  const viewCampaign = (id, opts) => {
    shieldRequest(`/api/shield/campaign?id=${id}`)
      .then((res) => shieldReadJson(res, "讀取戰役失敗"))
      .then((d) => {
        if (!d || d.ok === false) { push("error", `讀取戰役失敗:${(d && d.error) || "?"}`); return; }
        const c = d.campaign || {};
        if (!opts || !opts.silent) push("user", `🎖 查看戰役 #${id}:${c.directive || c.signature || ""}`);
        (d.waves || []).forEach((w) => push("result", `↳ [${w.role || w.kind}] ${String(w.brief || "").slice(0, 600)}`));
        if (c.report_md) push("final", `【指揮報告】\n${c.report_md}`);
      })
      .catch((e) => push("error", `讀取戰役失敗:${e.message || e}`));
  };

  // 自治戰役回放:輪詢戰役記錄;新完成的「自治」戰役(消防員點火,trigger_kind=incident)
  // 自動把將軍指揮報告呈現到終端 —— 即使沒人盯著瀏覽器,事後打開也能看到大軍幹了什麼。
  useEffectShield(() => {
    let alive = true;
    const poll = () => {
      shieldRequest("/api/shield/campaigns?limit=6")
        .then((res) => shieldReadJson(res, ""))
        .then((d) => {
          if (!alive) return;
          setFrozen(!!(d && d.frozen));
          const rows = (d && d.rows) || [];
          if (!seenCampRef.current) { seenCampRef.current = new Set(rows.map((r) => r.id)); return; }
          rows.slice().reverse().forEach((r) => {
            if (seenCampRef.current.has(r.id)) return;
            seenCampRef.current.add(r.id);
            if (r.trigger_kind === "incident" && r.status === "done") {
              push("sys", `🎖 自治戰役 #${r.id} 完成(消防員點火 · ${r.signature || "事件"})— 將軍報告:`);
              viewCampaign(r.id, { silent: true });
            }
          });
        })
        .catch(() => {});
    };
    poll();
    const t = setInterval(poll, 30000);
    return () => { alive = false; clearInterval(t); };
  }, []);

  const runKeyCheck = () => {
    push("sys", "引擎密鑰自檢中…");
    shieldRequest("/api/shield/keycheck")
      .then((res) => shieldReadJson(res, "自檢失敗"))
      .then((d) => {
        push("sys", `當前租戶庫=${d.current_tenant_db} · 當前租戶有key=${d.current_tenant_has_key} · firewatch在warehouse組=${d.firewatch_in_warehouse_group} · tenants目錄權限=${d.tenants_dir_mode || "?"}`);
        (d.scan || []).forEach((s) => {
          const rows = s.deepseek_active_rows;
          push(rows ? "result" : "sys",
            `  ${s.db} · key=${rows === undefined ? (s.query_err ? "無表" : "?") : rows} · ${s.mode || "?"} ${s.owner || ""}:${s.group || ""}${s.open_err ? " · 打不開:" + s.open_err : ""}`);
        });
      })
      .catch((e) => push("error", `引擎自檢失敗:${e.message || e}`));
    shieldRequest("/api/shield/enginetest")
      .then((res) => shieldReadJson(res, "引擎深測失敗"))
      .then((d) => {
        if (d.error) { push("error", `引擎深測:${d.error}`); return; }
        push("sys", `引擎深測 · 端點=${d.endpoint || "?"} · 模型=${d.model || "?"}`);
        const s = d.simple || {}, t = d.with_tools || {};
        push(s.ok ? "result" : "error", `  簡單請求 ${s.status || "?"} ${s.ok ? "OK" : "失敗:" + String(s.body || "").slice(0, 220)}`);
        push(t.ok ? "result" : "error", `  函數調用(tools) ${t.status || "?"} ${t.ok ? "OK" : "失敗:" + String(t.body || "").slice(0, 320)}`);
      })
      .catch((e) => push("error", `引擎深測失敗:${e.message || e}`));
  };

  const runInstruction = (text) => {
    const instruction = (text || "").trim();
    if (!instruction || busy) return;
    push("user", instruction);
    setInput("");
    setBusy(true);
    shieldStream("/api/shield/terminal/stream", { text: instruction, conversation_id: convRef.current, channel: "shield" }, (ev) => {
      if (ev.event === "run_start") {
        convRef.current = ev.conversation_id || convRef.current;
      } else if (ev.event === "step_start") {
        const args = ev.args && Object.keys(ev.args).length ? " " + JSON.stringify(ev.args) : "";
        push("cmd", `${ev.command || ev.tool_name}${args}`);
      } else if (ev.event === "step") {
        if (ev.ok) {
          push("result", `← ${ev.status || "ok"}${typeof ev.duration_ms === "number" ? ` · ${ev.duration_ms}ms` : ""}`);
        } else {
          push("error", `✗ ${ev.command || ev.tool_name} · ${ev.error || ev.status || "失敗"}`);
        }
      } else if (ev.event === "final") {
        if (ev.message) push("final", ev.message);
      } else if (ev.event === "error") {
        push("error", `終端錯誤:${ev.error || "流式中斷"}`);
      }
    }).catch((e) => push("error", `終端錯誤:${e.message || e}`))
      .finally(() => { setBusy(false); if (onAfterRun) onAfterRun(); });
  };

  const onKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      runInstruction(input);
    }
  };

  return (
    <div className="shield-panel shield-terminal-panel">
      <ShieldPanelTitle icon="cpu" title="SHIELD AI 終端" right={
        <span className="shield-term-head-actions">
          <button type="button" className={`shield-term-autotoggle ${autoPilot ? "on" : ""}`} onClick={() => setAutoPilot((v) => !v)} title="自主模式:偵測到升級事件時 AI 自動在終端開跑取證診斷">
            {autoPilot ? "自主 ●" : "自主 ○"}
          </button>
          <button type="button" className={`shield-term-freeze ${frozen ? "on" : ""}`} onClick={toggleFreeze} title="總凍結 kill-switch:凍結後運行中的戰役在階段邊界即停、自治點火暫停(讀寫皆停)">
            {frozen ? "🛑 已凍結" : "凍結"}
          </button>
          <button type="button" className="shield-term-campaign" disabled={busy || !engineReady || frozen} onClick={() => runCampaign(input)} title="派遣 Agent:將軍拆解目標 → 派遣只讀 Agent 大軍偵察 → 綜合指揮報告(有輸入則作為指令)">代理</button>
          <button type="button" className="shield-term-diagnose" disabled={busy || !engineReady} onClick={runDiagnoseNow} title="以當前態勢即時診斷一次(走秘書同鏈路,證明可用)">立即診斷</button>
          <button type="button" className="shield-term-keycheck" onClick={runKeyCheck} title="引擎密鑰自檢(定位未配置根因)">引擎自檢</button>
          <span className={`shield-term-live ${busy ? "is-busy" : ""}`}>
            <span/>{busy ? "AI 執行中" : "LIVE"}
          </span>
        </span>
      }/>
      {!!apPending.length && (
        <div className="shield-term-escalation">
          <span className="shield-term-esc-tag">🛰 自主升級</span>
          <span className="shield-term-esc-text">
            {apPending.length} 個事件確定性 L1 已窮盡 · 最新 INC-{apPending[0].incident_id}（{apPending[0].reason || "需 AI 診斷"}）
          </span>
          <button type="button" disabled={busy || !engineReady} onClick={() => runAutopilotDiagnose(apPending[0])}>
            <Icon name="sparkle" size={13}/>{busy ? "診斷中…" : "AI 自主診斷"}
          </button>
        </div>
      )}
      <div className="shield-term-autostrip">
        {autoFeed.length ? autoFeed.map((a, i) => (
          <div key={i} className={`shield-term-auto shield-term-auto-${a.tone}`}>
            <b>{a.label}</b>
            <span>{a.text}</span>
          </div>
        )) : <div className="shield-term-auto shield-term-auto-muted"><b>自主巡檢</b><span>暫無自主動作,消防員守護在線。</span></div>}
      </div>
      <div className="shield-term-scroll" ref={scrollRef}>
        {lines.map((l) => (
          <div key={l.id} className={`shield-term-line shield-term-${l.kind}${l.tone ? ` shield-term-tone-${l.tone}` : ""}`}>
            {l.kind === "user" ? <span className="shield-term-prompt">你 ›</span>
              : l.kind === "cmd" ? <span className="shield-term-glyph">🤖</span>
              : l.kind === "result" ? <span className="shield-term-glyph">↳</span>
              : l.kind === "error" ? <span className="shield-term-glyph">✗</span>
              : l.kind === "final" ? <span className="shield-term-glyph">✦</span>
              : l.kind === "selfcheck" ? <span className="shield-term-glyph">🩺</span>
              : <span className="shield-term-glyph">·</span>}
            <span className="shield-term-text">{l.text}</span>
          </div>
        ))}
        {busy && <div className="shield-term-line shield-term-cmd shield-term-typing"><span className="shield-term-glyph">🤖</span><span className="shield-term-text">安全中樞 AI 思考中…</span></div>}
      </div>
      <div className="shield-term-input">
        <span>›</span>
        <input
          type="text"
          value={input}
          disabled={busy || !engineReady}
          placeholder={engineReady ? "自然語言指揮 SHIELD AI…（Enter 執行）" : "智能引擎未接入，請先在上方重新驗證引擎"}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={onKeyDown}
        />
        <button type="button" disabled={busy || !engineReady || !input.trim()} onClick={() => runInstruction(input)}>
          <Icon name="zap" size={14}/>{busy ? "執行中" : "執行"}
        </button>
      </div>
    </div>
  );
};

const ShieldSpark = ({ data, color = "#14B8A6", height = 48 }) => {
  const vals = (data || []).map((d) => Number(d[1]) || 0);
  if (!vals.length) return <div className="shield-spark-empty">無數據</div>;
  const max = Math.max(...vals, 1), min = Math.min(...vals, 0), W = 260, H = height, n = vals.length;
  const pts = vals.map((v, i) => {
    const x = n === 1 ? W : (i / (n - 1)) * W;
    const y = H - ((v - min) / (max - min || 1)) * (H - 4) - 2;
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  }).join(" ");
  return (
    <svg className="shield-spark" viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none">
      <polyline points={`0,${H} ${pts} ${W},${H}`} fill={color} fillOpacity="0.1" stroke="none"/>
      <polyline points={pts} fill="none" stroke={color} strokeWidth="1.6" vectorEffect="non-scaling-stroke"/>
    </svg>
  );
};

const ShieldBars = ({ data, color = "#3B82F6" }) => {
  const rows = data || [];
  if (!rows.length) return <div className="shield-bars-empty">無數據</div>;
  const max = Math.max(...rows.map((r) => Number(r[1]) || 0), 1);
  return (
    <div className="shield-bars">
      {rows.map(([label, val], i) => (
        <div className="shield-bar-row" key={i}>
          <span className="shield-bar-label" title={String(label)}>{String(label)}</span>
          <span className="shield-bar-track"><span className="shield-bar-fill" style={{ width: `${(Number(val) / max) * 100}%`, background: color }}/></span>
          <b>{val}</b>
        </div>
      ))}
    </div>
  );
};

const ShieldStats = () => {
  const [data, setData] = useStateShield(null);
  const [win, setWin] = useStateShield(180);
  const [loading, setLoading] = useStateShield(true);
  useEffectShield(() => {
    let alive = true;
    setLoading(true);
    shieldRequest(`/api/shield/stats?window=${win}`)
      .then((res) => shieldReadJson(res, "統計載入失敗"))
      .then((d) => { if (alive) setData(d); })
      .catch(() => {})
      .finally(() => { if (alive) setLoading(false); });
    return () => { alive = false; };
  }, [win]);

  if (loading && !data) return <div className="shield-empty">平臺統計載入中…</div>;
  const a = (data && data.access) || {}, c = (data && data.calls) || {}, u = (data && data.usage) || {}, s = (data && data.security) || {};
  const num = (v) => (typeof v === "number" ? v.toLocaleString() : (v || 0));

  return (
    <div className="shield-stats">
      <div className="shield-stats-head">
        <span>時間視窗</span>
        {[[60, "1 時"], [180, "3 時"], [720, "12 時"], [1440, "1 天"], [10080, "7 天"]].map(([w, l]) => (
          <button key={w} type="button" className={`shield-stats-win ${win === w ? "on" : ""}`} onClick={() => setWin(w)}>{l}</button>
        ))}
      </div>
      <div className="shield-stats-cards">
        <div className="shield-stat-card"><span>總請求(訪問)</span><b>{num(a.total_req)}</b><small>峰值 {num(a.peak_req)}/拍</small></div>
        <div className="shield-stat-card"><span>AI 運行(調用)</span><b>{num(c.ai_runs)}</b><small>{num(c.tool_calls)} 次工具調用</small></div>
        <div className="shield-stat-card"><span>Token 消耗</span><b>{num(c.ai_tokens)}</b><small>消防員 {num(c.ff_llm_tokens)}</small></div>
        <div className="shield-stat-card"><span>活躍用戶(使用)</span><b>{num(u.active_users)}</b><small>{num(u.active_tenants)}/{num(u.tenant_count)} 租戶活躍</small></div>
        <div className="shield-stat-card"><span>安全事件</span><b>{num(s.incidents)}</b><small>攻擊態勢 {num(s.under_attack)}</small></div>
      </div>
      <div className="shield-stats-grid">
        <div className="shield-stat-chart"><h4>訪問流量(req/拍)</h4><ShieldSpark data={a.req_series} color="#14B8A6"/></div>
        <div className="shield-stat-chart"><h4>AI 運行(每小時)</h4><ShieldSpark data={c.runs_series} color="#8457E7"/></div>
        <div className="shield-stat-chart"><h4>5xx 服務錯誤</h4><ShieldSpark data={a.err5xx_series} color="#EF4444"/></div>
        <div className="shield-stat-chart"><h4>登入失敗(安全)</h4><ShieldSpark data={s.login_series} color="#F59E0B"/></div>
        <div className="shield-stat-chart"><h4>Top 工具調用</h4><ShieldBars data={c.top_tools} color="#3B82F6"/></div>
        <div className="shield-stat-chart"><h4>AI 運行狀態 / 引擎</h4><ShieldBars data={(c.by_status || []).concat(u.by_engine || [])} color="#10B981"/></div>
      </div>
    </div>
  );
};

const PageShield = () => {
  const [status, setStatus] = useStateShield(null);
  const [incidents, setIncidents] = useStateShield([]);
  const [loading, setLoading] = useStateShield(true);
  const [error, setError] = useStateShield("");
  const [lastLoaded, setLastLoaded] = useStateShield("");
  const [selectedNodeId, setSelectedNodeId] = useStateShield("");
  const [engineBusy, setEngineBusy] = useStateShield(false);
  const [panelDiag, setPanelDiag] = useStateShield(null);
  const [panelDiagBusy, setPanelDiagBusy] = useStateShield(false);
  const [activeTab, setActiveTab] = useStateShield("intel");

  const load = (silent = false) => {
    if (!silent) setLoading(true);
    setError("");
    return Promise.all([
      shieldRequest("/api/shield/status").then((res) => shieldReadJson(res, "安全狀態載入失敗")),
      shieldRequest("/api/shield/incidents?limit=40").then((res) => shieldReadJson(res, "事件列表載入失敗")),
    ]).then(([st, inc]) => {
      setStatus(st);
      setIncidents(inc.rows || []);
      setLastLoaded(new Date().toLocaleTimeString("zh-CN", { hour12: false }));
    }).catch((e) => setError(e.message || String(e)))
      .finally(() => setLoading(false));
  };

  useEffectShield(() => {
    load(false);
    const timer = setInterval(() => load(true), 15000);
    return () => clearInterval(timer);
  }, []);

  const stateMeta = shieldStateMeta(status && status.state);
  const topology = (status && status.topology) || {};
  const topologyNodes = topology.nodes || [];
  const openIncidents = status && status.open_incidents ? status.open_incidents.length : 0;
  const risks = (status && status.recent_ai_risk_events) || [];
  const openRisks = Number((status && status.open_ai_risk_events) || 0);
  const timeline = (status && status.recent_timeline) || [];
  const guardianTail = (status && status.guardian_tail) || [];
  const severity = Number((status && status.severity) || 0);
  const repairEvents = timeline.filter((item) => String(item.kind || "").indexOf("repair_") === 0);
  const latestRepair = repairEvents[0];
  // 只取「成功」的診斷;失敗條目(調用/委派失敗、未配置、HTTP 4xx/5xx、tool_calls 不符等)
  // 不在面板呈現 —— 鏈路已修,殘留的舊失敗條目不該一直掛在智能判讀上。
  const isFailedDiag = (item) => /調用失敗|调用失败|委派失敗|委派失败|推理通道|未配置|不可用|not configured|api key|HTTP [45]|insufficient tool/i
    .test(String((item && item.content) || ""));
  const diagnosticEvents = timeline.filter((item) => String(item.kind || "") === "diagnose" && !isFailedDiag(item));
  const latestDiagnostic = diagnosticEvents[0];
  const aiEngine = (status && status.ai_engine) || {};
  const engineConfigured = !!aiEngine.configured;
  const engineConnected = !!aiEngine.connected;
  const deepseekUnavailable = !engineConfigured;
  const healthScore = status ? Math.max(0, Math.min(100, Math.round(
    100 - severity * 18 - openIncidents * 12 - (status.firefighter_available ? 0 : 18)
  ))) : 0;
  const postureText = !status ? "同步中" : stateMeta.label;
  const deepseekMode = !engineConfigured ? "智能引擎未配置"
    : engineConnected ? "共用密鑰已接入"
    : "待重新驗證";
  const repairMode = status && status.firefighter_available ? "L1 白名單自動修復" : "等待消防員資料";
  const guardianMode = guardianTail.length ? "Guardian 記錄在線" : "Guardian 等待回傳";
  const governanceMode = openRisks >= 100 ? "治理隊列高壓" : openRisks ? "待覆核" : "清空";
  const selectedNode = topologyNodes.find((node) => node.id === selectedNodeId) || topologyNodes.find((node) => node.id === topology.hot_node_id) || topologyNodes[0] || null;
  const selectedFilters = (selectedNode && selectedNode.filters) || {};
  const selectedTimeline = selectedFilters.timeline_kinds && selectedFilters.timeline_kinds.length
    ? timeline.filter((item) => selectedFilters.timeline_kinds.indexOf(String(item.kind || "")) >= 0)
    : timeline;
  const selectedRisks = selectedFilters.risk_commands && selectedFilters.risk_commands.length
    ? risks.filter((risk) => selectedFilters.risk_commands.indexOf(String(risk.command || "")) >= 0)
    : (selectedNode && selectedNode.id === "governance" ? risks : []);
  const riskTone = useMemoShield(() => {
    if ((status && status.state) === "healthy" && !openIncidents) return "green";
    if (openIncidents) return "red";
    return "yellow";
  }, [status, openIncidents]);

  useEffectShield(() => {
    if (!topologyNodes.length) return;
    const ids = topologyNodes.map((node) => node.id);
    if (!selectedNodeId || ids.indexOf(selectedNodeId) < 0) {
      setSelectedNodeId(topology.hot_node_id || ids[0]);
    }
  }, [topology && topology.generated_at, topologyNodes.length]);

  const runPanelDiagnose = () => {
    if (panelDiagBusy) return;
    setPanelDiagBusy(true);
    setPanelDiag(null);
    shieldRequest("/api/shield/diagnose/now")
      .then((res) => shieldReadJson(res, "診斷失敗"))
      .then((d) => setPanelDiag((!d || d.ok === false || d.error) ? { error: (d && d.error) || "診斷失敗" } : d))
      .catch((e) => setPanelDiag({ error: e.message || String(e) }))
      .finally(() => setPanelDiagBusy(false));
  };

  const revalidateEngine = () => {
    setEngineBusy(true);
    setError("");
    shieldRequest("/api/integrations/deepseek/validate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ persist: true }),
    }).then((res) => shieldReadJson(res, "智能引擎重新驗證失敗"))
      .then(() => load(true))
      .catch((e) => setError(e.message || String(e)))
      .finally(() => setEngineBusy(false));
  };

  const handleTopologyAction = (action) => {
    if (!action) return;
    if (action.kind === "client-refresh") {
      load(false);
      return;
    }
    if (action.kind === "revalidate-ai") {
      revalidateEngine();
      return;
    }
    if (action.kind === "navigate-settings") {
      const nav = document.querySelector('[data-nav-id="settings"]');
      if (nav) nav.click();
      return;
    }
    if (action.id === "review-risks") setSelectedNodeId("governance");
    if (action.id === "show-events") setSelectedNodeId("event");
    if (action.id === "show-repairs") setSelectedNodeId("l1");
  };

  const tabs = [
    { id: "intel", label: "智能判讀", icon: "sparkle" },
    { id: "stats", label: "平臺統計", icon: "activity" },
    { id: "stream", label: "事件流", icon: "activity", count: timeline.length },
    { id: "governance", label: "治理隊列", icon: "alert", count: openRisks },
    { id: "incidents", label: "消防員事件", icon: "flame", count: incidents.length },
  ];

  return (
    <div className="shield-page shield-page-v2 shield-page-v3">
      {error && <div className="shield-error"><Icon name="alert" size={16}/>{error}</div>}

      {/* 健康狀態條 */}
      <header className="shield-statusbar">
        <div className="shield-sb-brand">
          <span><Icon name="shield" size={18}/></span>
          <div><b>SHIELD</b><small>AI 安全中樞</small></div>
        </div>
        <div className="shield-sb-metrics">
          <div className={`shield-sb-cell shield-sb-${riskTone}`}>
            <span>綜合健康</span><b>{healthScore}%</b><small>嚴重度 {severity}/5</small>
          </div>
          <div className={`shield-sb-cell ${openIncidents ? "shield-sb-red" : "shield-sb-green"}`}>
            <span>消防員事件</span><b>{openIncidents}</b><small>{status && status.firefighter_available ? "在線" : "未就緒"}</small>
          </div>
          <div className={`shield-sb-cell ${openRisks ? "shield-sb-yellow" : "shield-sb-green"}`}>
            <span>治理隊列</span><b>{openRisks}</b><small>{governanceMode}</small>
          </div>
          <div className="shield-sb-cell shield-sb-blue">
            <span>數據流</span><b>{Math.round((topology.flow_rate || 0) * 100)}%</b><small>{Math.round((topology.live_metrics || {}).req_rate || 0)} req/拍</small>
          </div>
          <div className={`shield-sb-cell ${engineConnected ? "shield-sb-green" : "shield-sb-yellow"}`}>
            <span>智能引擎</span><b>{!engineConfigured ? "未配置" : engineConnected ? "在線" : "待驗證"}</b><small>{aiEngine.node || "—"}</small>
          </div>
          <div className="shield-sb-cell">
            <span>守護</span><b>{guardianTail.length ? "在線" : "等待"}</b><small>{guardianTail.length ? `${guardianTail.length} 行` : "—"}</small>
          </div>
        </div>
        <div className="shield-sb-actions">
          {status && <ShieldStatePill state={status.state}/>}
          <div className="shield-refresh"><span>刷新</span><b>{lastLoaded || "—"}</b></div>
          <button className="btn btn-sm" disabled={loading} onClick={() => load(false)} title="刷新安全中樞">
            <Icon name="refresh" size={15}/>刷新
          </button>
        </div>
      </header>

      {/* 雙核:實時拓撲 + AI 終端 */}
      <section className="shield-dualcore">
        <div className="shield-core shield-topology-stage">
          <div className="shield-stage-head">
            <div><span>LIVE TOPOLOGY</span><b>平台實時數據鏈路</b></div>
            <div className="shield-score-ring" style={{ borderColor: `${stateMeta.color}66`, color: stateMeta.color }}>
              <strong>{healthScore}</strong><span>score</span>
            </div>
          </div>
          <ShieldTopologyCanvas
            status={status || { state: "offline" }}
            height={520}
            topology={topology}
            selectedNodeId={selectedNode && selectedNode.id}
            onSelectNode={setSelectedNodeId}
          />
          <div className="shield-stage-strip">
            <span title="真實平台數據流:nginx 請求速率 + 事件密度">
              <Icon name="activity" size={13}/>數據流 {Math.round((topology.flow_rate || 0) * 100)}% · {Math.round((topology.live_metrics || {}).req_rate || 0)} req/拍
            </span>
            <span><Icon name="zap" size={13}/>L1 {latestRepair ? "有修復記錄" : "監控中"}</span>
            <span><Icon name="eye" size={13}/>Guardian {guardianTail.length ? "在線" : "等待"}</span>
          </div>
        </div>

        <ShieldTerminal
          status={status}
          timeline={timeline}
          guardianTail={guardianTail}
          engineReady={engineConfigured}
          onAfterRun={() => load(true)}
        />
      </section>

      {/* 標籤頁:次要面板 */}
      <section className="shield-tabsec">
        <nav className="shield-tabs">
          {tabs.map((t) => (
            <button key={t.id} type="button" className={`shield-tab ${activeTab === t.id ? "is-active" : ""}`} onClick={() => setActiveTab(t.id)}>
              <Icon name={t.icon} size={14}/>{t.label}{typeof t.count === "number" ? <em>{t.count}</em> : null}
            </button>
          ))}
        </nav>

        {activeTab === "intel" && (
          <div className="shield-tab-body shield-intel-grid">
            <ShieldNodeInspector node={selectedNode} timeline={selectedTimeline} risks={selectedRisks} onAction={handleTopologyAction}/>
            <div className="shield-intel-card shield-intel-primary">
              <ShieldPanelTitle icon="sparkle" title="智能判讀" right={<span className="shield-chip">{deepseekMode}</span>}/>
              <div className="shield-intel-big">{postureText}</div>
              <div className="shield-engine-line">
                <span>共用密鑰</span><b>{aiEngine.masked_key || "未配置"}</b>
                <span>節點</span><b>{aiEngine.node || "—"}</b>
                <span>最近驗證</span><b>{aiEngine.checked_at ? shieldTime(aiEngine.checked_at) : "—"}</b>
              </div>
              {panelDiag ? (
                panelDiag.error ? (
                  <p className="shield-diag-fresh shield-diag-err">即時診斷失敗:{panelDiag.error}</p>
                ) : (
                  <p className="shield-diag-fresh">
                    <b>【判讀】</b>{panelDiag.diagnosis || "(模型未返回)"}
                    <small>建議動作:{panelDiag.recommended_action || "none"} · 嚴重度 {panelDiag.severity ?? "?"}/5 · 信心 {panelDiag.confidence ?? "?"}</small>
                  </p>
                )
              ) : (
                <p>{latestDiagnostic ? shieldTimelineSummary(latestDiagnostic)
                  : (postureText === "健康" ? "系統健康,目前無需診斷。有異常時自動診斷,或點「立即診斷」即時驗讀。"
                    : "消防員會在異常觸發後使用只讀工具取證,再由智能引擎生成診斷與修復建議。")}</p>
              )}
              <div className="shield-intel-actions">
                <button className="shield-engine-revalidate shield-diag-now" type="button" disabled={panelDiagBusy || !engineConfigured} onClick={runPanelDiagnose}>
                  <Icon name="sparkle" size={13}/>{panelDiagBusy ? "診斷中…" : "立即診斷"}
                </button>
                <button className="shield-engine-revalidate" type="button" disabled={engineBusy || !engineConfigured} onClick={revalidateEngine}>
                  <Icon name="refresh" size={13}/>{engineBusy ? "驗證中…" : "重新驗證引擎"}
                </button>
              </div>
            </div>
            <div className="shield-intel-card">
              <ShieldPanelTitle icon="zap" title="自動修復" right={<span className="shield-chip shield-chip-hot">{repairMode}</span>}/>
              <div className="shield-repair-state">
                <strong>{latestRepair ? latestRepair.kind : "standby"}</strong>
                <span>{latestRepair ? shieldTime(latestRepair.ts) : "等待低風險觸發"}</span>
              </div>
              <p>{latestRepair ? shieldCompact(latestRepair.content, 220) : "只允許 L1 白名單命令,不接受任意 shell。"}</p>
            </div>
          </div>
        )}

        {activeTab === "stats" && (
          <div className="shield-tab-body">
            <ShieldStats/>
          </div>
        )}

        {activeTab === "stream" && (
          <div className="shield-tab-body">
            <div className="shield-stream shield-stream-tall">
              {timeline.length ? timeline.slice(0, 24).map((item, idx) => <ShieldStreamItem key={idx} item={item}/>) : (
                <div className="shield-empty">尚無消防員時間線。</div>
              )}
            </div>
          </div>
        )}

        {activeTab === "governance" && (
          <div className="shield-tab-body">
            <div className="shield-risk-list shield-risk-grid">
              {risks.length ? risks.slice(0, 12).map((r) => <ShieldRiskCard key={r.id} risk={r}/>) : (
                <div className="shield-empty">沒有近期 AI 高風險操作。</div>
              )}
            </div>
          </div>
        )}

        {activeTab === "incidents" && (
          <div className="shield-tab-body">
            <div className="shield-incident-list">
              {incidents.length ? incidents.slice(0, 8).map((inc) => <ShieldIncidentCard key={inc.id} inc={inc}/>) : (
                <div className="shield-empty">目前沒有消防員事件。</div>
              )}
            </div>
          </div>
        )}
      </section>
    </div>
  );
};

window.PageShield = PageShield;
