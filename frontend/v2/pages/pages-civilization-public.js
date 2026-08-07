(() => {
  const root = document.getElementById("civilization-public");
  const shareKey = decodeURIComponent(location.pathname.split("/").filter(Boolean).pop() || "");
  const locale = /^en\b/i.test(navigator.language || "") ? "en" : "zh";
  const PALETTES = {
    judgement:["#D62B20","#F3CE1D","#211A17","#F7E8D8"], technology:["#1656A3","#64D1D4","#092840","#DDEDF2"],
    organization:["#17694E","#F1C928","#102B22","#DCEBE1"], time:["#B45418","#F1CF75","#3A2416","#F4E8D8"], ethics:["#6C3D8E","#F0A4C2","#28172E","#EDE1F0"],
  };
  const el = (tag, className, text) => { const node = document.createElement(tag); if (className) node.className = className; if (text != null) node.textContent = text; return node; };
  const localContent = post => {
    const locales = post && post.content && post.content.locales || {};
    return (locale === "en" ? (locales.en || locales.zh) : (locales.zh || locales.en)) || {};
  };
  const paragraphs = value => {
    const source = String(value || "").trim();
    if (!source) return [];
    const explicit = source.split(/\n\s*\n/).map(item => item.trim()).filter(Boolean);
    if (explicit.length > 1) return explicit;
    const sentences = source.match(/[^。！？.!?]+[。！？.!?]?/g) || [source];
    const result = [];
    for (let index = 0; index < sentences.length; index += 2) result.push(sentences.slice(index,index+2).join("").trim());
    return result.filter(Boolean);
  };
  const sectionsOf = content => {
    if (Array.isArray(content.sections) && content.sections.length) return content.sections;
    const source = String(content.thesis || "").trim();
    const stages = source.split(/(?=(?:20|30|40|50|60)岁)/).map(item => item.trim()).filter(Boolean);
    if (stages.length > 1) return stages.map((part,index) => { const age=part.match(/^(20|30|40|50|60)岁/); const stop=part.search(/[。！？.!?]/); return { marker:age?age[1]:String(index).padStart(2,"0"), kicker:age?"LIFE / NETWORK":"PROPOSITION", heading:stop>=0?part.slice(0,stop+1):(content.short||content.title), paragraphs:paragraphs(stop>=0?part.slice(stop+1):part) }; });
    return [{ marker:"00", kicker:"PROPOSITION / 核心判断", heading:content.short||content.title, paragraphs:paragraphs(source) }];
  };
  const button = (text, action, primary=false) => { const node=el("button",primary?"is-primary":"",text); node.type="button"; node.addEventListener("click",action); return node; };
  const render = post => {
    const content = localContent(post);
    const palette = PALETTES[post.domain] || PALETTES.judgement;
    const shell = el("div","cp-shell");
    shell.style.setProperty("--signal",palette[0]); shell.style.setProperty("--accent",palette[1]); shell.style.setProperty("--domain-ink",palette[2]); shell.style.setProperty("--domain-pale",palette[3]);
    const topbar=el("header","cp-topbar"), brand=el("div","cp-brand"), actions=el("div","cp-actions");
    brand.append(el("i"),el("span","","BONFIRE PLATFORM · CIVILIZATION"));
    const publicUrl=location.origin+post.public_path;
    actions.append(button(locale==="en"?"COPY LINK":"复制链接",async()=>{ await navigator.clipboard.writeText(publicUrl); }),button(locale==="en"?"PNG POSTCARD":"PNG 明信片",()=>window.CivilizationPostcard.download(post,publicUrl,locale),true));
    if (navigator.share) actions.append(button(locale==="en"?"SHARE":"系统分享",()=>navigator.share({title:String(content.title||"Civilization"),text:String(content.short||""),url:publicUrl}).catch(()=>{})));
    topbar.append(brand,actions);
    const poster=el("article","cp-poster"), main=el("div","cp-poster-main"), kicker=el("div","cp-kicker"), side=el("aside","cp-side");
    kicker.append(el("span","",String(content.eyebrow||"CIVILIZATION · QUESTION")),el("span","",String(content.category_label||post.domain).toUpperCase()));
    main.append(kicker,el("h1","cp-title",content.title||"CIVILIZATION"),el("p","cp-short",content.short||""));
    side.append(el("strong","cp-side-no",String(post.published_revision||0).padStart(2,"0")),el("h2","",content.title||""),el("p","",content.quote||content.short||""),el("footer","",`${post.date}\nSWISS B / PUBLIC EDITION`));
    poster.append(main,side);
    const body=el("section","cp-body");
    sectionsOf(content).forEach((section,index)=>{ const row=el("section","cp-section"), marker=el("div","cp-section-index"), copy=el("div","cp-copy"); marker.append(el("strong","",section.marker||String(index).padStart(2,"0")),el("small","",section.kicker||"SECTION / THOUGHT")); copy.append(el("span","",section.kicker||`SECTION ${index+1}`),el("h2","",section.heading||"")); (Array.isArray(section.paragraphs)?section.paragraphs:paragraphs(section.paragraphs)).forEach(value=>copy.append(el("p","",value))); row.append(marker,copy); body.append(row); });
    const footer=el("footer","cp-foot"); footer.append(el("span","",content.footer_right||"INFORMATION BEFORE DECORATION"),el("span","",post.date));
    shell.append(topbar,poster,body,footer); root.replaceChildren(shell);
  };
  fetch(`/api/public/civilization/${encodeURIComponent(shareKey)}`,{credentials:"omit",headers:{Accept:"application/json"}}).then(async response=>{ if(!response.ok) throw new Error(response.status===404?"NOT FOUND":"UNAVAILABLE"); return response.json(); }).then(render).catch(error=>{ root.replaceChildren(el("div","civilization-public-error",`${error.message}\nBONFIRE / CIVILIZATION`)); });
})();
