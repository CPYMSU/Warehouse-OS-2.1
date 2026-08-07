/* Bonfire Civilization · browser-side PNG postcard renderer. */
(() => {
  const DOMAIN = {
    judgement: { signal: "#D62B20", accent: "#F3CE1D", ink: "#211A17", pale: "#F7E8D8" },
    technology: { signal: "#1656A3", accent: "#64D1D4", ink: "#092840", pale: "#DDEDF2" },
    organization: { signal: "#17694E", accent: "#F1C928", ink: "#102B22", pale: "#DCEBE1" },
    time: { signal: "#B45418", accent: "#F1CF75", ink: "#3A2416", pale: "#F4E8D8" },
    ethics: { signal: "#6C3D8E", accent: "#F0A4C2", ink: "#28172E", pale: "#EDE1F0" },
  };
  const textOf = (value, locale) => {
    if (typeof value === "string") return value;
    if (!value || typeof value !== "object") return "";
    return locale === "en" ? (value.en || value.zh || "") : (value.zh || value.en || "");
  };
  const contentOf = (post, locale) => {
    const locales = post && post.content && post.content.locales || {};
    return (locale === "en" ? (locales.en || locales.zh) : (locales.zh || locales.en)) || {
      title: textOf(post && post.title, locale),
      short: textOf(post && post.short, locale),
      quote: textOf(post && post.short, locale),
    };
  };
  const tokens = value => String(value || "").match(/[\u3400-\u9fff\uf900-\ufaff]|[^\u3400-\u9fff\uf900-\ufaff\s]+\s*|\s+/g) || [];
  const wrap = (context, value, width) => {
    const lines = [];
    let line = "";
    tokens(value).forEach(token => {
      const next = line + token;
      if (line && context.measureText(next).width > width) {
        lines.push(line.trim());
        line = token.trimStart();
      } else line = next;
    });
    if (line.trim()) lines.push(line.trim());
    return lines;
  };
  const titleLayout = (context, title) => {
    for (let size = 106; size >= 52; size -= 3) {
      context.font = `900 ${size}px "Helvetica Neue", "PingFang SC", "Noto Sans CJK SC", sans-serif`;
      const lines = wrap(context, title, 1010);
      if (lines.length <= 5) return { size, lines };
    }
    context.font = '900 52px "Helvetica Neue", "PingFang SC", sans-serif';
    return { size: 52, lines: wrap(context, title, 1010).slice(0, 6) };
  };
  const draw = (post, publicUrl, locale = "zh") => {
    const canvas = document.createElement("canvas");
    canvas.width = 1600;
    canvas.height = 1000;
    const context = canvas.getContext("2d");
    const palette = DOMAIN[post && post.domain] || DOMAIN.judgement;
    const content = contentOf(post, locale);
    const title = String(content.title || "CIVILIZATION");
    const short = String(content.short || content.quote || "");
    context.fillStyle = palette.pale;
    context.fillRect(0, 0, canvas.width, canvas.height);
    context.strokeStyle = palette.signal + "28";
    context.lineWidth = 1;
    for (let x = 0; x <= 1200; x += 100) {
      context.beginPath(); context.moveTo(x, 0); context.lineTo(x, 1000); context.stroke();
    }
    for (let y = 0; y <= 1000; y += 80) {
      context.beginPath(); context.moveTo(0, y); context.lineTo(1200, y); context.stroke();
    }
    context.fillStyle = palette.ink;
    context.fillRect(1200, 0, 400, 1000);
    context.fillStyle = palette.signal;
    context.fillRect(1030, 86, 245, 220);
    context.fillStyle = palette.accent;
    context.globalAlpha = .88;
    context.fillRect(930, 225, 205, 198);
    context.globalAlpha = 1;
    context.fillStyle = palette.ink;
    context.font = '800 18px "SFMono-Regular", Menlo, monospace';
    context.fillText("BONFIRE PLATFORM", 70, 68);
    context.font = '700 15px "SFMono-Regular", Menlo, monospace';
    context.fillText(`CIVILIZATION · ${String(post && post.domain || "JUDGEMENT").toUpperCase()}`, 70, 100);
    const layout = titleLayout(context, title);
    context.fillStyle = palette.ink;
    context.font = `900 ${layout.size}px "Helvetica Neue", "PingFang SC", "Noto Sans CJK SC", sans-serif`;
    layout.lines.forEach((line, index) => context.fillText(line, 70, 220 + index * layout.size * .96));
    context.fillStyle = palette.signal;
    context.fillRect(70, 765, 1035, 8);
    context.fillStyle = palette.ink;
    context.font = '500 30px "Helvetica Neue", "PingFang SC", sans-serif';
    wrap(context, short, 1000).slice(0, 3).forEach((line, index) => context.fillText(line, 70, 825 + index * 42));
    context.fillStyle = "#F7F3E9";
    context.font = '800 15px "SFMono-Regular", Menlo, monospace';
    context.fillText("ONE QUESTION / MANY LENSES", 1250, 70);
    context.fillStyle = palette.accent;
    context.font = '900 92px "SFMono-Regular", Menlo, monospace';
    context.fillText(String(post && post.published_revision || 0).padStart(2, "0"), 1245, 180);
    context.fillStyle = "#F7F3E9";
    context.font = '700 18px "Helvetica Neue", "PingFang SC", sans-serif';
    const side = wrap(context, String(content.quote || short), 290).slice(0, 8);
    side.forEach((line, index) => context.fillText(line, 1245, 300 + index * 31));
    context.fillStyle = palette.accent;
    context.font = '700 13px "SFMono-Regular", Menlo, monospace';
    wrap(context, publicUrl, 290).slice(0, 4).forEach((line, index) => context.fillText(line, 1245, 820 + index * 22));
    context.fillStyle = "#F7F3E9";
    context.font = '700 13px "SFMono-Regular", Menlo, monospace';
    context.fillText(String(post && post.date || "BONFIRE"), 1245, 950);
    context.fillStyle = palette.accent;
    context.fillRect(1510, 925, 28, 28);
    return canvas;
  };
  const download = (post, publicUrl, locale = "zh") => {
    const canvas = draw(post, publicUrl, locale);
    const title = String(contentOf(post, locale).title || "civilization")
      .replace(/[\\/:*?"<>|\s]+/g, "-").slice(0, 36) || "civilization";
    const save = url => {
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `${title}-bonfire-postcard.png`;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
    };
    if (canvas.toBlob) canvas.toBlob(blob => {
      if (!blob) return;
      const url = URL.createObjectURL(blob);
      save(url);
      window.setTimeout(() => URL.revokeObjectURL(url), 1000);
    }, "image/png");
    else save(canvas.toDataURL("image/png"));
  };
  window.CivilizationPostcard = { draw, download };
})();
