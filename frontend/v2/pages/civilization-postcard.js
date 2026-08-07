/* Bonfire Civilization · browser-side mobile long-poster PNG renderer. */
(() => {
  const DOMAIN = {
    judgement: { signal: "#D62B20", accent: "#F3CE1D", ink: "#211A17", pale: "#F7E8D8" },
    technology: { signal: "#1656A3", accent: "#64D1D4", ink: "#092840", pale: "#DDEDF2" },
    organization: { signal: "#17694E", accent: "#F1C928", ink: "#102B22", pale: "#DCEBE1" },
    time: { signal: "#B45418", accent: "#F1CF75", ink: "#3A2416", pale: "#F4E8D8" },
    ethics: { signal: "#6C3D8E", accent: "#F0A4C2", ink: "#28172E", pale: "#EDE1F0" },
  };
  const WIDTH = 1080;
  const MAX_HEIGHT = 14000;
  const MARGIN = 58;
  const CONTENT_WIDTH = WIDTH - MARGIN * 2;
  const SANS = '"Helvetica Neue", "PingFang SC", "Noto Sans CJK SC", sans-serif';
  const MONO = '"SFMono-Regular", Menlo, monospace';

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
      thesis: textOf(post && post.thesis, locale),
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
  const paragraphs = value => {
    const source = String(value || "").trim();
    if (!source) return [];
    const explicit = source.split(/\n\s*\n/).map(part => part.trim()).filter(Boolean);
    if (explicit.length > 1) return explicit;
    const sentences = source.match(/[^。！？.!?]+[。！？.!?]?/g) || [source];
    const result = [];
    for (let index = 0; index < sentences.length; index += 2) {
      result.push(sentences.slice(index, index + 2).join("").trim());
    }
    return result.filter(Boolean);
  };
  const sectionsOf = content => {
    if (Array.isArray(content.sections) && content.sections.length) return content.sections;
    return [{
      marker: "00",
      kicker: content.category_label || "PROPOSITION / 核心判断",
      heading: "",
      paragraphs: paragraphs(content.thesis || content.quote || content.short),
    }];
  };
  const setFont = (context, weight, size, family = SANS) => {
    context.font = `${weight} ${size}px ${family}`;
  };
  const titleLayout = (context, title) => {
    for (let size = 92; size >= 58; size -= 2) {
      setFont(context, 900, size);
      const lines = wrap(context, title, CONTENT_WIDTH);
      if (lines.length <= 4) return { size, lines };
    }
    setFont(context, 900, 58);
    return { size: 58, lines: wrap(context, title, CONTENT_WIDTH).slice(0, 5) };
  };
  const normalizeSectionParagraphs = section => Array.isArray(section && section.paragraphs)
    ? section.paragraphs.map(value => String(value || "").trim()).filter(Boolean)
    : paragraphs(section && section.paragraphs);

  const makePlan = (context, post, locale, bodySize) => {
    const content = contentOf(post, locale);
    const title = String(content.title || "CIVILIZATION");
    const titlePlan = titleLayout(context, title);
    const titleLineHeight = Math.round(titlePlan.size * 1.03);
    let y = 610;
    const titleY = y;
    y += titlePlan.lines.length * titleLineHeight + 54;
    const items = [];
    const sections = sectionsOf(content);
    sections.forEach((section, sectionIndex) => {
      const kicker = String(section && section.kicker || `SECTION ${sectionIndex + 1}`).trim();
      const heading = String(section && section.heading || "").trim();
      const sectionParagraphs = normalizeSectionParagraphs(section);
      if (sectionIndex > 0 || heading) {
        y += sectionIndex ? 58 : 0;
        items.push({ type: "rule", y });
        y += 44;
        if (kicker) {
          items.push({ type: "kicker", y, text: kicker.toUpperCase() });
          y += 42;
        }
      }
      if (heading) {
        setFont(context, 850, 52);
        const lines = wrap(context, heading, CONTENT_WIDTH);
        items.push({ type: "heading", y, lines });
        y += lines.length * 61 + 32;
      }
      sectionParagraphs.forEach((paragraph, paragraphIndex) => {
        setFont(context, 450, bodySize);
        const lines = wrap(context, paragraph, CONTENT_WIDTH);
        items.push({ type: "paragraph", y, lines, size: bodySize });
        y += lines.length * Math.round(bodySize * 1.68);
        y += paragraphIndex === sectionParagraphs.length - 1 ? 10 : 28;
      });
    });
    const footerY = y + 68;
    return {
      content,
      title,
      titlePlan,
      titleY,
      titleLineHeight,
      items,
      footerY,
      height: Math.ceil(footerY + 210),
    };
  };

  const fitPlan = (context, post, locale) => {
    const sizes = [38, 35, 32, 29, 26, 23];
    let plan;
    for (const size of sizes) {
      plan = makePlan(context, post, locale, size);
      if (plan.height <= MAX_HEIGHT) return { ...plan, clipped: false };
    }
    return { ...plan, height: MAX_HEIGHT, clipped: true };
  };
  const strokeCircle = (context, x, y, radius, color, width) => {
    context.beginPath();
    context.arc(x, y, radius, 0, Math.PI * 2);
    context.strokeStyle = color;
    context.lineWidth = width;
    context.stroke();
  };
  const drawHero = (context, post, locale, palette, plan) => {
    const date = String(post && post.date || new Date().toISOString().slice(0, 10));
    const month = date.slice(0, 7).replace("-", "—");
    const domain = String(post && post.domain || "judgement").toUpperCase();
    const number = String(post && (post.no || post.published_revision) || 1).padStart(2, "0");
    context.fillStyle = palette.ink;
    context.fillRect(0, 0, WIDTH, plan.height);

    context.globalAlpha = .72;
    context.fillStyle = palette.signal;
    context.beginPath();
    context.arc(960, 450, 390, 0, Math.PI * 2);
    context.fill();
    context.fillStyle = palette.ink;
    context.beginPath();
    context.arc(960, 450, 270, 0, Math.PI * 2);
    context.fill();
    context.globalAlpha = 1;

    strokeCircle(context, 960, 270, 168, palette.pale + "B8", 2);
    strokeCircle(context, 960, 270, 116, palette.signal, 2);
    strokeCircle(context, 960, 270, 58, palette.accent, 3);
    context.fillStyle = palette.accent;
    context.beginPath(); context.arc(960, 270, 17, 0, Math.PI * 2); context.fill();
    context.strokeStyle = palette.signal;
    context.lineWidth = 4;
    context.beginPath(); context.moveTo(960, 270); context.lineTo(980, 395); context.stroke();

    context.fillStyle = palette.pale;
    setFont(context, 800, 21, MONO);
    context.fillText(`${domain} / ${month}`, MARGIN, 78);
    context.textAlign = "right";
    context.fillText(locale === "en" ? "PUBLIC EDITION" : "公开分享", WIDTH - MARGIN, 78);
    context.textAlign = "left";

    context.fillStyle = palette.accent;
    setFont(context, 900, 250);
    context.fillText(number, MARGIN, 430);
    context.fillStyle = palette.pale;
    setFont(context, 800, 24);
    context.fillText(locale === "en" ? "CURRENT QUESTION" : "当前问题", MARGIN, 474);

    context.fillStyle = palette.pale;
    setFont(context, 900, plan.titlePlan.size);
    plan.titlePlan.lines.forEach((line, index) => {
      context.fillText(line, MARGIN, plan.titleY + index * plan.titleLineHeight);
    });
  };
  const drawBody = (context, palette, plan, publicUrl, locale, post) => {
    context.fillStyle = palette.pale;
    plan.items.forEach(item => {
      if (item.y > plan.height - 190) return;
      if (item.type === "rule") {
        context.globalAlpha = .55;
        context.fillStyle = palette.pale;
        context.fillRect(MARGIN, item.y, CONTENT_WIDTH, 2);
        context.globalAlpha = 1;
      } else if (item.type === "kicker") {
        context.fillStyle = palette.accent;
        setFont(context, 850, 19, MONO);
        context.fillText(item.text, MARGIN, item.y);
      } else if (item.type === "heading") {
        context.fillStyle = palette.pale;
        setFont(context, 850, 52);
        item.lines.forEach((line, index) => context.fillText(line, MARGIN, item.y + index * 61));
      } else if (item.type === "paragraph") {
        context.fillStyle = palette.pale;
        context.globalAlpha = .94;
        setFont(context, 450, item.size);
        const lineHeight = Math.round(item.size * 1.68);
        item.lines.forEach((line, index) => {
          const baseline = item.y + index * lineHeight;
          if (baseline <= plan.height - 205) context.fillText(line, MARGIN, baseline);
        });
        context.globalAlpha = 1;
      }
    });

    const footerY = Math.min(plan.footerY, plan.height - 142);
    context.fillStyle = palette.pale;
    context.globalAlpha = .58;
    context.fillRect(MARGIN, footerY, CONTENT_WIDTH, 2);
    context.globalAlpha = 1;
    context.fillStyle = palette.accent;
    setFont(context, 800, 18, MONO);
    context.fillText("BONFIRE PLATFORM / CIVILIZATION", MARGIN, footerY + 48);
    context.textAlign = "right";
    context.fillText(String(post && post.date || "BONFIRE"), WIDTH - MARGIN, footerY + 48);
    context.textAlign = "left";
    if (publicUrl) {
      context.fillStyle = palette.pale;
      context.globalAlpha = .72;
      setFont(context, 650, 17, MONO);
      wrap(context, publicUrl, CONTENT_WIDTH).slice(0, 2).forEach((line, index) => {
        context.fillText(line, MARGIN, footerY + 88 + index * 27);
      });
      context.globalAlpha = 1;
    } else {
      context.fillStyle = palette.pale;
      context.globalAlpha = .72;
      setFont(context, 650, 17, MONO);
      context.fillText(locale === "en" ? "PRIVATE BROWSER EXPORT" : "浏览器本地导出", MARGIN, footerY + 88);
      context.globalAlpha = 1;
    }
    if (plan.clipped) {
      context.fillStyle = palette.accent;
      setFont(context, 700, 17, MONO);
      context.fillText(locale === "en" ? "OPEN THE PUBLIC PAGE TO CONTINUE READING" : "内容较长，请打开公开网页继续阅读", MARGIN, plan.height - 38);
    }
  };

  const drawLong = (post, publicUrl, locale = "zh") => {
    const canvas = document.createElement("canvas");
    canvas.width = WIDTH;
    canvas.height = 200;
    let context = canvas.getContext("2d");
    const plan = fitPlan(context, post, locale);
    canvas.height = plan.height;
    context = canvas.getContext("2d");
    const palette = DOMAIN[post && post.domain] || DOMAIN.judgement;
    drawHero(context, post, locale, palette, plan);
    drawBody(context, palette, plan, publicUrl, locale, post);
    return canvas;
  };
  const filename = (post, locale) => {
    const title = String(contentOf(post, locale).title || "civilization")
      .replace(/[\\/:*?"<>|\s]+/g, "-").slice(0, 36) || "civilization";
    return `${title}-bonfire-long-poster.png`;
  };
  const downloadLong = (post, publicUrl, locale = "zh") => {
    const canvas = drawLong(post, publicUrl, locale);
    const save = url => {
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = filename(post, locale);
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
  window.CivilizationPostcard = {
    draw: drawLong,
    drawLong,
    download: downloadLong,
    downloadLong,
  };
})();
