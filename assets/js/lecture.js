/* lecture.js — parse bilingual transcript and render with YT embed */

const CJK_RE = /[㐀-鿿豈-﫿　-〿＀-￯]/;

// Cached for export
let CURRENT_MD = "";
let CURRENT_LEC = null;
let CURRENT_CHAPTERS = [];

function stripFrontmatter(md) {
  if (md.startsWith("---")) {
    const end = md.indexOf("\n---", 3);
    if (end > 0) return md.slice(end + 4).replace(/^\s*\n/, "");
  }
  return md;
}

function isCJK(s) { return CJK_RE.test(s); }

function parseTranscript(md) {
  md = stripFrontmatter(md);
  const lines = md.split("\n");
  const chapters = [];
  let current = null;
  let buffer = [];

  function flushParagraph() {
    if (!buffer.length) return;
    const text = buffer.join("\n").trim();
    buffer = [];
    if (!text) return;
    if (!current) return;
    const speakerMatch = text.match(/^\*\*(.+?)[：:]?\*\*[：:]?\s*$/);
    if (speakerMatch) {
      current.segments.push({ type: "speaker", label: speakerMatch[1].trim() });
      return;
    }
    const cleaned = text.replace(/^>\s?/gm, "");
    const cjk = isCJK(cleaned);
    current.segments.push({ type: cjk ? "zh" : "en", text: cleaned });
  }

  for (let line of lines) {
    if (line.startsWith("# ") && !line.startsWith("## ")) continue;
    const ch = line.match(/^## Chapter (\d+)\.\s+(.+?)(?:\s*\[[\d:]+\])?\s*$/);
    if (ch) {
      flushParagraph();
      if (current) chapters.push(current);
      const titleParts = ch[2].split(/[｜|]/, 2);
      current = {
        n: parseInt(ch[1]),
        title_en: (titleParts[0] || "").trim(),
        title_zh: ((titleParts[1] || "").trim()).replace(/^第[一二三四五六七八九十0-9]+\s*章[:：]\s*/, ""),
        segments: [],
      };
      continue;
    }
    if (/^#{1,4}\s/.test(line)) continue;
    if (line.trim() === "") {
      flushParagraph();
    } else {
      buffer.push(line);
    }
  }
  flushParagraph();
  if (current) chapters.push(current);

  for (const c of chapters) {
    const out = [];
    const segs = c.segments;
    let i = 0;
    while (i < segs.length) {
      const s = segs[i];
      if (s.type === "speaker") { out.push(s); i++; continue; }
      if (s.type === "en" && i + 1 < segs.length && segs[i+1].type === "zh") {
        out.push({ type: "pair", en: s.text, zh: segs[i+1].text });
        i += 2;
      } else {
        out.push({ type: "pair", en: s.type === "en" ? s.text : "", zh: s.type === "zh" ? s.text : "" });
        i++;
      }
    }
    c.segments = out;
  }

  return chapters;
}

// ===================== Export utilities =====================

function safeFileName(s) {
  return s.replace(/[<>:"/\\|?*\x00-\x1f]/g, "").slice(0, 80).trim();
}

function downloadBlob(content, mime, filename) {
  const blob = new Blob([content], { type: mime + ";charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url; a.download = filename;
  document.body.appendChild(a); a.click();
  setTimeout(() => { URL.revokeObjectURL(url); a.remove(); }, 0);
}

function showToast(msg, timeout = 2400) {
  let t = document.getElementById("toast");
  if (!t) {
    t = document.createElement("div");
    t.id = "toast";
    t.className = "toast";
    document.body.appendChild(t);
  }
  t.textContent = msg;
  t.classList.add("show");
  clearTimeout(t._timer);
  t._timer = setTimeout(() => t.classList.remove("show"), timeout);
}

function lectureFileBase(lec) {
  return safeFileName(`Shiller_ECON252_${lec.id}_${lec.title_zh}`);
}

function exportMd() {
  const filename = lectureFileBase(CURRENT_LEC) + ".md";
  downloadBlob(CURRENT_MD, "text/markdown", filename);
  showToast("已下載 " + filename);
}

function exportTxt() {
  const lec = CURRENT_LEC;
  const lines = [];
  lines.push(`${lec.title_zh}（L${lec.num}）`);
  lines.push(lec.title_en);
  lines.push(`Yale ECON 252 (2011) Lecture ${lec.num} — Robert J. Shiller`);
  lines.push(`Open Yale Courses: ${lec.oyc_url}`);
  if (lec.youtube_id) lines.push(`YouTube: https://youtu.be/${lec.youtube_id}`);
  lines.push("");
  lines.push("=".repeat(60));
  lines.push("");

  for (const c of CURRENT_CHAPTERS) {
    lines.push("");
    lines.push(`[Chapter ${c.n}] ${c.title_en}`);
    lines.push(`[第 ${c.n} 章] ${c.title_zh}`);
    lines.push("-".repeat(50));
    lines.push("");
    for (const seg of c.segments) {
      if (seg.type === "speaker") {
        lines.push(`【${seg.label}】`);
        lines.push("");
      } else {
        if (seg.en) { lines.push(seg.en); lines.push(""); }
        if (seg.zh) { lines.push(seg.zh); lines.push(""); }
      }
    }
  }
  const filename = lectureFileBase(lec) + ".txt";
  downloadBlob(lines.join("\n"), "text/plain", filename);
  showToast("已下載 " + filename);
}

function escapeHtml(s) {
  return s.replace(/[&<>]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" })[c]);
}

function buildPrintableHtml(lec, chapters) {
  let body = "";
  for (const c of chapters) {
    body += `<section class="ch"><h2>Ch ${c.n}. ${escapeHtml(c.title_en)}</h2>`;
    body += `<div class="ch-zh">第 ${c.n} 章：${escapeHtml(c.title_zh)}</div>`;
    for (const seg of c.segments) {
      if (seg.type === "speaker") {
        body += `<div class="speaker">${escapeHtml(seg.label)}</div>`;
      } else {
        body += `<div class="pair">`;
        if (seg.en) body += `<p class="en">${escapeHtml(seg.en)}</p>`;
        if (seg.zh) body += `<p class="zh">${escapeHtml(seg.zh)}</p>`;
        body += `</div>`;
      }
    }
    body += `</section>`;
  }
  return `<!DOCTYPE html>
<html lang="zh-Hant"><head>
<meta charset="UTF-8">
<title>${escapeHtml(lec.title_zh)} — Shiller ECON 252 L${lec.num}</title>
<style>
  body { font-family: "Noto Serif TC","Source Han Serif TC","PingFang TC","Songti TC", Georgia, serif;
         max-width: 760px; margin: 24px auto; padding: 0 28px; line-height: 1.75; color: #1f1d1a; }
  h1 { font-size: 1.5rem; margin: 0 0 6px; }
  .meta { color: #666; font-size: 0.88rem; margin-bottom: 24px; padding-bottom: 14px; border-bottom: 1px solid #ddd; }
  .meta a { color: #8b3a2b; }
  h2 { font-size: 1.1rem; color: #8b3a2b; margin: 26px 0 4px; padding-top: 12px; border-top: 1px solid #eee; page-break-after: avoid; }
  .ch-zh { color: #555; font-size: 0.95rem; margin-bottom: 14px; }
  .speaker { font-weight: 600; color: #8b3a2b; margin: 14px 0 6px; font-size: 0.95rem; }
  .pair { margin: 0 0 14px; page-break-inside: avoid; }
  p.en { font-family: Georgia, serif; color: #444; margin: 0 0 4px; font-size: 0.94rem; }
  p.zh { color: #111; margin: 0; }
  @media print {
    body { margin: 0; padding: 0 24px; max-width: 100%; }
    .ch { page-break-inside: auto; }
    h2 { page-break-after: avoid; }
    .pair { page-break-inside: avoid; }
    .no-print { display: none; }
  }
  .print-btn { position: fixed; top: 12px; right: 16px;
    background: #8b3a2b; color: #fff; border: 0; padding: 10px 18px;
    border-radius: 6px; font-size: 0.95rem; cursor: pointer; box-shadow: 0 2px 8px rgba(0,0,0,0.2); }
</style></head>
<body>
<button class="print-btn no-print" onclick="window.print()">🖨 列印 / 存成 PDF</button>
<h1>L${lec.num}｜${escapeHtml(lec.title_zh)}</h1>
<div class="meta">${escapeHtml(lec.title_en)}<br>
Yale ECON 252 (2011) · Robert J. Shiller · 日期 ${escapeHtml(lec.date || "—")}<br>
原始: <a href="${lec.oyc_url}">${lec.oyc_url}</a>${lec.youtube_id ? ` · YouTube: <a href="https://youtu.be/${lec.youtube_id}">https://youtu.be/${lec.youtube_id}</a>` : ""}</div>
${body}
<script>setTimeout(()=>window.print(), 350);</script>
</body></html>`;
}

function exportPdf() {
  const html = buildPrintableHtml(CURRENT_LEC, CURRENT_CHAPTERS);
  const w = window.open("", "_blank");
  if (!w) {
    showToast("瀏覽器封鎖了視窗開啟，請允許彈出後再試");
    return;
  }
  w.document.open();
  w.document.write(html);
  w.document.close();
  w.focus();
  showToast("列印視窗已開啟，在對話框選『另存為 PDF』");
}

async function copyMd() {
  try {
    await navigator.clipboard.writeText(CURRENT_MD);
    showToast("✓ 已複製到剪貼簿——可直接貼進 Claude / ChatGPT 對話");
  } catch (e) {
    showToast("複製失敗，請改用「MD」下載");
  }
}

// ===================== Render =====================

function renderLecture(lec, chapters) {
  const main = document.getElementById("main");
  main.innerHTML = "";

  main.appendChild(el("div", { class: "lecture-header" },
    el("div", { class: "titles" },
      el("h1", {}, `L${lec.num}｜${lec.title_zh}`),
      el("div", { class: "en" }, lec.title_en),
    ),
    el("div", { class: "meta" },
      el("span", {}, "日期 " + (lec.date || "—")),
      lec.guest ? el("span", { class: "tag" }, "嘉賓 " + lec.guest) : null,
      el("span", { class: "tag" }, "Track: " + ({intro:"入門", tools:"工具", institutions:"制度"}[lec.track] || lec.track)),
    ),
  ));

  main.appendChild(el("div", { class: "broker-callout" },
    el("div", { class: "label" }, "對世界級金融家的價值"),
    el("div", { html: lec.value }),
  ));

  if (lec.youtube_id) {
    main.appendChild(el("div", { class: "video-wrap" },
      el("iframe", {
        src: `https://www.youtube.com/embed/${lec.youtube_id}`,
        title: lec.title_zh,
        allow: "accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture",
        allowfullscreen: "",
      })
    ));
  } else {
    main.appendChild(el("div", { class: "video-wrap" },
      el("div", { class: "video-fallback" },
        el("div", {}, "尚未綁定 YouTube 影片"),
        el("a", { href: lec.oyc_url, target: "_blank", rel: "noopener", style: "color:#fff" }, "→ 前往 Open Yale Courses 觀看")
      )
    ));
  }

  // ----- view-mode + export bar -----
  const modes = [
    { id: "side", label: "中英並排" },
    { id: "stack", label: "上下交錯" },
    { id: "zh", label: "僅中文" },
    { id: "en", label: "僅英文" },
  ];
  const bar = el("div", { class: "viewmode-bar" });
  bar.appendChild(el("span", { class: "muted" }, "顯示模式："));
  const group = el("div", { class: "group" });
  for (const m of modes) {
    const b = el("button", { onclick: () => setMode(m.id) }, m.label);
    b.dataset.mode = m.id;
    group.appendChild(b);
  }
  bar.appendChild(group);

  // export group
  const exportGroup = el("div", { class: "export-group" },
    el("span", { class: "muted exp-label" }, "匯出："),
    el("button", { class: "exp-btn", onclick: copyMd, title: "複製為 Markdown 到剪貼簿（適合貼進 Claude / ChatGPT）" },
      "📋 複製"),
    el("button", { class: "exp-btn", onclick: exportMd, title: "下載 .md 檔（含中英對照、結構化，最適合餵 AI）" },
      "MD"),
    el("button", { class: "exp-btn", onclick: exportTxt, title: "下載 .txt 純文字檔（最通用格式）" },
      "TXT"),
    el("button", { class: "exp-btn", onclick: exportPdf, title: "在新分頁開啟列印版面，選『另存為 PDF』" },
      "PDF"),
  );
  bar.appendChild(exportGroup);

  bar.appendChild(el("span", { class: "link" },
    el("a", { href: lec.oyc_url, target: "_blank", rel: "noopener" }, "Open Yale 原始頁面 ↗")
  ));
  main.appendChild(bar);

  // hint about AI usage (small, below bar)
  main.appendChild(el("div", { class: "ai-hint" },
    "💡 ",
    el("b", {}, "餵給 AI 學習"),
    "：點「📋 複製」或「MD」拿到完整逐字稿，貼進 Claude / ChatGPT 後可請 AI 摘要、提問、考你重點概念。"
  ));

  // chapters
  for (const c of chapters) {
    const det = el("details", { class: "chapter" });
    if (c.n <= 2) det.setAttribute("open", "");
    det.appendChild(el("summary", {},
      el("span", { class: "chnum" }, `Ch ${c.n}`),
      el("span", { class: "ch-title" }, c.title_zh || c.title_en),
      el("span", { class: "ch-en" }, c.title_en),
    ));
    const body = el("div", { class: "ch-body" });
    for (const seg of c.segments) {
      if (seg.type === "speaker") {
        body.appendChild(el("div", { class: "speaker" }, seg.label));
      } else {
        body.appendChild(el("div", { class: "pair" },
          el("div", { class: "en" }, seg.en),
          el("div", { class: "zh" }, seg.zh),
        ));
      }
    }
    det.appendChild(body);
    main.appendChild(det);
  }

  setMode(localStorage.getItem("viewmode") || "side");
}

function setMode(m) {
  document.body.classList.remove("mode-side", "mode-stack", "mode-zh", "mode-en");
  document.body.classList.add("mode-" + m);
  for (const b of document.querySelectorAll(".viewmode-bar .group button")) {
    b.classList.toggle("active", b.dataset.mode === m);
  }
  localStorage.setItem("viewmode", m);
}

async function initLecturePage() {
  const data = await loadLectures();
  let id = getParam("id");
  if (!id) id = "L01";
  const lec = data.lectures.find(l => l.id === id) || data.lectures[0];

  document.body.prepend(buildTopbar("lecture"));
  const layout = document.querySelector(".layout");
  layout.prepend(buildSidebar(data.lectures, lec.id));
  document.title = `L${lec.num}｜${lec.title_zh} — Shiller《金融市場》`;

  try {
    const resp = await fetch(lec.file);
    if (!resp.ok) throw new Error(resp.status);
    const md = await resp.text();
    const chs = parseTranscript(md);
    CURRENT_MD = md;
    CURRENT_LEC = lec;
    CURRENT_CHAPTERS = chs;
    renderLecture(lec, chs);
  } catch (e) {
    document.getElementById("main").innerHTML = `<div class="broker-callout">無法載入逐字稿（${lec.file}）：${e.message}<br>若以 file:// 直接開啟，瀏覽器會封鎖 fetch；請在資料夾執行 <code>python3 -m http.server</code> 並用 http://localhost:8000 開啟。</div>`;
  }

  document.body.appendChild(buildFooter());
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initLecturePage);
} else {
  initLecturePage();
}
