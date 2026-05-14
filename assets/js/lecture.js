/* lecture.js — parse bilingual transcript and render with YT embed */

const CJK_RE = /[㐀-鿿豈-﫿　-〿＀-￯]/;

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
    // speaker label?
    const speakerMatch = text.match(/^\*\*(.+?)[：:]?\*\*[：:]?\s*$/);
    if (speakerMatch) {
      current.segments.push({ type: "speaker", label: speakerMatch[1].trim() });
      return;
    }
    // strip leading "> " quoting if any
    const cleaned = text.replace(/^>\s?/gm, "");
    const cjk = isCJK(cleaned);
    current.segments.push({ type: cjk ? "zh" : "en", text: cleaned });
  }

  for (let line of lines) {
    if (line.startsWith("# ") && !line.startsWith("## ")) continue; // top H1
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
    if (/^#{1,4}\s/.test(line)) continue; // skip other headings
    if (line.trim() === "") {
      flushParagraph();
    } else {
      buffer.push(line);
    }
  }
  flushParagraph();
  if (current) chapters.push(current);

  // pair EN+ZH segments inside each chapter
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
        // orphan EN or ZH → still render
        out.push({ type: "pair", en: s.type === "en" ? s.text : "", zh: s.type === "zh" ? s.text : "" });
        i++;
      }
    }
    c.segments = out;
  }

  return chapters;
}

function renderLecture(lec, chapters) {
  const main = document.getElementById("main");
  main.innerHTML = "";

  // header
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

  // broker callout
  main.appendChild(el("div", { class: "broker-callout" },
    el("div", { class: "label" }, "對世界級金融家的價值"),
    el("div", { html: lec.value }),
  ));

  // video
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

  // view mode bar
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
  bar.appendChild(el("span", { class: "link" },
    el("a", { href: lec.oyc_url, target: "_blank", rel: "noopener" }, "Open Yale 原始頁面 ↗")
  ));
  main.appendChild(bar);

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
  for (const b of document.querySelectorAll(".viewmode-bar button")) {
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
