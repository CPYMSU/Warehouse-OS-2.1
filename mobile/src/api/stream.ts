// NDJSON 流式 — RN 的 fetch 不支持讀 ReadableStream,改用 XMLHttpRequest 監聽 progress,
// 對 responseText 增量按 \n 切分逐行 JSON。用於 AI 秘書 /api/agent/run/stream。
import { API_BASE } from "./client";

export type StreamEvent = Record<string, any>;

type Handlers = {
  token: string;
  slug: string;
  onEvent: (e: StreamEvent) => void;
  onError?: (msg: string) => void;
  onDone?: () => void;
};

export function streamNDJSON(path: string, body: any, h: Handlers): () => void {
  const xhr = new XMLHttpRequest();
  let seen = 0;
  xhr.open("POST", API_BASE + path);
  xhr.setRequestHeader("Content-Type", "application/json");
  xhr.setRequestHeader("Accept", "application/x-ndjson");
  if (h.token) xhr.setRequestHeader("Authorization", `Bearer ${h.token}`);
  if (h.slug) xhr.setRequestHeader("X-Tenant-Slug", h.slug);

  const flush = () => {
    const text = xhr.responseText || "";
    const chunk = text.slice(seen);
    const lastNl = chunk.lastIndexOf("\n");
    if (lastNl === -1) return;
    const ready = chunk.slice(0, lastNl);
    seen += lastNl + 1;
    for (const line of ready.split("\n")) {
      const s = line.trim();
      if (!s) continue;
      try { h.onEvent(JSON.parse(s)); } catch (_) { /* 忽略半行 */ }
    }
  };

  xhr.onprogress = flush;
  xhr.onreadystatechange = () => {
    if (xhr.readyState === 4) {
      flush();
      if (xhr.status >= 200 && xhr.status < 300) h.onDone && h.onDone();
      else h.onError && h.onError(`HTTP ${xhr.status}`);
    }
  };
  xhr.onerror = () => h.onError && h.onError("網絡錯誤");
  xhr.send(JSON.stringify(body || {}));

  return () => { try { xhr.abort(); } catch (_) {} };
}
