#!/usr/bin/env python3
"""Export the explicitly selected loopback reading site, without its source tree.

Output is private runtime data, never a committed frontend asset. HTML editions
embed their local images/styles/scripts and relay internal navigation to the
authenticated parent reader. Original source files remain untouched.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import html
import json
import mimetypes
import re
from collections import deque
from datetime import UTC, datetime
from html.parser import HTMLParser
from pathlib import Path, PurePosixPath
from urllib.parse import unquote, urldefrag, urljoin, urlsplit
from urllib.request import urlopen

GROUPS = [
    {"id": "mk73", "code": "MK73", "title": "博士論文", "subtitle": "外部條件與中俄相互貿易", "description": "從研究問題、選擇集與理論模型，讀到各章的證據與邊界。"},
    {"id": "mk77", "code": "MK77", "title": "期刊研究", "subtitle": "油價下跌時誰受損", "description": "從價格與數量開始，逐步推導中俄貿易的負擔反轉條件。"},
    {"id": "learn", "code": "METHODS", "title": "方法學習", "subtitle": "同一問題，不同模型", "description": "比較計量模型、均衡模型與 DSGE 的問題、假設與回答。"},
]
DOCUMENTS = [
    ("mk73", "papers/mk73-dissertation.pdf", "MK73 博士論文", "博士論文全文 · PDF", "paper"),
    ("mk73", "papers/mk73-autoreferat.pdf", "MK73 自述摘要", "論文的問題、貢獻與結論 · PDF", "paper"),
    ("mk77", "papers/mk77-manuscript.pdf", "MK77 期刊稿", "油價下跌時誰受損：中俄貿易的負擔反轉 · PDF", "paper"),
    ("mk77", "mk77/derive.html", "一步一步推導負擔反轉", "從價格 × 數量出發，用九個步驟推導兩個方向的銷售變化。", "interactive"),
    ("mk77", "mk77/index.html", "五張圖讀懂核心機制", "油的需求、收入傳導、兩條線的比較、原油緩衝與恩格爾曲線。", "interactive"),
    ("mk73", "mk73/index.html", "論文總覽", "題目、定理、證據與各章的閱讀地圖。", "page"),
    ("mk73", "mk73/story.html", "論文講的故事", "排除轉移貿易而不創造貿易：從問題走向解釋。", "page"),
    ("mk73", "mk73/narrator.html", "聽懂排除轉移理論", "用講述的順序理解研究的核心論證。", "interactive"),
    ("mk73", "mk73/model_b.html", "模型 B：選項被移走的市場", "從一個供需均衡開始，分層推導進口市場的改變。", "interactive"),
    ("mk73", "mk73/laws.html", "六條規律的小模型", "把六個定理放回能逐項檢查的小模型。", "interactive"),
    ("mk73", "mk73/skeleton.html", "有效選擇集：論文骨架", "把問題、機制與可觀察的結果連起來。", "page"),
    ("mk73", "mk73/manifest.html", "修訂段落清單", "從 v29 到選擇集修訂的逐段記錄。", "page"),
    ("learn", "learn/models.html", "三種模型，三種回答", "計量模型、均衡模型、DSGE：各自能回答什麼。", "interactive"),
]
ALLOWED_ROOTS = {"mk73", "mk77", "learn", "papers"}
ALLOWED_SUFFIXES = {".html", ".pdf", ".js", ".css", ".png", ".jpg", ".jpeg", ".svg", ".gif", ".webp", ".woff", ".woff2", ".json"}
SANDBOX_COMPAT = """<script>
// Reading pages keep their own step state; opaque sandbox documents cannot
// write the parent application's URL history.
if (location.protocol === 'about:') {
  ['replaceState', 'pushState'].forEach(function(name) {
    var original = history[name].bind(history);
    history[name] = function() {
      try { return original.apply(history, arguments); }
      catch (error) { if (error.name !== 'SecurityError') throw error; }
    };
  });
}
</script>"""
BRIDGE = """<script>
document.addEventListener('click', function(event) {
  var link = event.target.closest('a[data-showcase-path]');
  if (!link) return;
  event.preventDefault();
  parent.postMessage({type:'bonfire-research-navigate', path:link.dataset.showcasePath}, '*');
});
window.addEventListener('message', function(event) {
  if (event.source !== parent || !event.data || event.data.type !== 'bonfire-research-anchor') return;
  var target = document.getElementById(event.data.anchor);
  if (target) target.scrollIntoView();
});
</script>"""


class Edition:
    def __init__(self, source: str):
        parsed = urlsplit(source)
        if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
            raise ValueError("The import source must be an explicitly selected loopback HTTP server")
        self.source = source.rstrip("/") + "/"
        self.pending = deque(["index.html"] + [row[1] for row in DOCUMENTS])
        self.originals: dict[str, bytes] = {}
        self.results: dict[str, bytes] = {}

    def resolve(self, value: str, current: str) -> tuple[str, str] | None:
        if not value or value.startswith(("#", "data:", "mailto:", "javascript:")):
            return None
        target, fragment = urldefrag(urljoin(urljoin(self.source, current), html.unescape(value)))
        parsed = urlsplit(target)
        if parsed.netloc != urlsplit(self.source).netloc or parsed.scheme != "http":
            return None
        path = unquote(parsed.path).lstrip("/") or "index.html"
        parts = PurePosixPath(path).parts
        if ".." in parts or "\\" in path:
            raise ValueError(f"Unsafe local reference: {path}")
        if path != "index.html" and (parts[0] not in ALLOWED_ROOTS or PurePosixPath(path).suffix.lower() not in ALLOWED_SUFFIXES):
            raise ValueError(f"Reference outside the selected research site: {path}")
        return path, fragment

    def fetch(self, path: str) -> bytes:
        if path not in self.originals:
            url = self.source if path == "index.html" else urljoin(self.source, path)
            with urlopen(url, timeout=30) as response:
                if urlsplit(response.url).netloc != urlsplit(self.source).netloc:
                    raise ValueError("A local import redirected outside its source")
                body = response.read(40 * 1024 * 1024 + 1)
            if len(body) > 40 * 1024 * 1024:
                raise ValueError(f"Research file exceeds the import limit: {path}")
            self.originals[path] = body
        return self.originals[path]

    def asset(self, path: str) -> str:
        body = self.fetch(path)
        if path.endswith(".css"):
            text = body.decode("utf-8")
            def css_url(match):
                ref = match.group(1).strip(" \"'")
                resolved = self.resolve(ref, path)
                return "url(" + self.asset(resolved[0]) + ")" if resolved else match.group(0)
            body = re.sub(r"url\(([^)]+)\)", css_url, text).encode("utf-8")
        media = mimetypes.guess_type(path)[0] or "application/octet-stream"
        return "data:" + media + ";base64," + base64.b64encode(body).decode("ascii")

    def build(self, output: Path):
        while self.pending:
            path = self.pending.popleft()
            if path in self.results:
                continue
            body = self.fetch(path)
            if path.endswith(".html"):
                parser = Page(self, path)
                parser.feed(body.decode("utf-8"))
                text = "".join(parser.output)
                for old, new in [
                    ("本頁只在本機，不發佈。", "研究工作稿 · Bonfire 研究展示。"),
                    ("這一頁每次打開都重新列出，新的頁面和新版論文會自己出現。", "此處收錄本次同步的研究頁面與論文。"),
                    ("只在本機", "研究工作稿"),
                    ("127.0.0.1:8000", "BONFIRE RESEARCH"),
                ]:
                    text = text.replace(old, new)
                text = re.sub(r"(<head\b[^>]*>)", lambda match: match.group(1) + SANDBOX_COMPAT, text, count=1, flags=re.I)
                body = text.replace("</body>", BRIDGE + "</body>").encode("utf-8")
            self.results[path] = body
        content = output / "content"
        files = {}
        for path, body in self.results.items():
            destination = content / path
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(body)
            files[path] = {"bytes": len(body), "sha256": hashlib.sha256(body).hexdigest(), "source_sha256": hashlib.sha256(self.originals[path]).hexdigest()}
        documents = [{"id": path, "group": group, "path": path, "title": title, "description": description, "kind": kind, "bytes": files[path]["bytes"]} for group, path, title, description, kind in DOCUMENTS]
        catalog = {"available": True, "title": "MK 研究展示", "edition": datetime.now(UTC).isoformat(timespec="seconds"), "edition_date": datetime.now().astimezone().date().isoformat(), "groups": GROUPS, "documents": documents, "files": files}
        (output / "catalog.json").write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"documents": len(documents), "files": len(files), "bytes": sum(item["bytes"] for item in files.values()), "output": str(output)}, ensure_ascii=False))


class Page(HTMLParser):
    def __init__(self, edition: Edition, path: str):
        super().__init__(convert_charrefs=False)
        self.edition, self.path, self.output = edition, path, []

    def handle_starttag(self, tag, attrs):
        original = self.get_starttag_text()
        additions = ""
        for key, value in attrs:
            if key not in {"src", "href", "poster"} or value is None:
                continue
            resolved = self.edition.resolve(value, self.path)
            if not resolved:
                continue
            path, fragment = resolved
            if tag == "a" and key == "href":
                self.edition.pending.append(path)
                target = path + ("#" + fragment if fragment else "")
                replacement = "#research-page"
                additions = ' data-showcase-path="' + html.escape(target, quote=True) + '"'
            else:
                replacement = self.edition.asset(path)
            pattern = r"(\b" + key + r"\s*=\s*)([\"'])(.*?)\2"
            original = re.sub(pattern, lambda match: match.group(1) + match.group(2) + html.escape(replacement, quote=True) + match.group(2), original, count=1, flags=re.I | re.S)
        self.output.append(re.sub(r"(/?>)$", lambda match: additions + match.group(1), original))

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag): self.output.append("</" + tag + ">")
    def handle_data(self, data): self.output.append(data)
    def handle_entityref(self, name): self.output.append("&" + name + ";")
    def handle_charref(self, name): self.output.append("&#" + name + ";")
    def handle_comment(self, data): self.output.append("<!--" + data + "-->")
    def handle_decl(self, decl): self.output.append("<!" + decl + ">")


if __name__ == "__main__":
    arguments = argparse.ArgumentParser(description=__doc__)
    arguments.add_argument("--source", default="http://127.0.0.1:8000/")
    arguments.add_argument("--output", type=Path, default=Path("backend/var/research-showcase-export"))
    options = arguments.parse_args()
    Edition(options.source).build(options.output)
