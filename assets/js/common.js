/* common.js — shared topbar + sidebar + data loader */

const DATA_URL = "data/lectures.json";
let LECTURES_CACHE = null;

async function loadLectures() {
  if (LECTURES_CACHE) return LECTURES_CACHE;
  const resp = await fetch(DATA_URL);
  LECTURES_CACHE = await resp.json();
  return LECTURES_CACHE;
}

function el(tag, attrs = {}, ...children) {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === "class") e.className = v;
    else if (k === "html") e.innerHTML = v;
    else if (k.startsWith("on") && typeof v === "function") e.addEventListener(k.slice(2), v);
    else e.setAttribute(k, v);
  }
  for (const c of children) {
    if (c == null) continue;
    e.appendChild(typeof c === "string" ? document.createTextNode(c) : c);
  }
  return e;
}

function buildTopbar(activeTab) {
  const tabs = [
    { id: "home", label: "首頁", href: "index.html" },
    { id: "lecture", label: "逐字稿", href: "lecture.html" },
    { id: "wiki", label: "Wiki", href: "wiki.html" },
    { id: "mindmap", label: "心智圖", href: "mindmap.html" },
  ];
  const bar = el("div", { class: "topbar" },
    el("a", { class: "brand", href: "index.html" },
      "Shiller《金融市場》",
      el("span", { class: "small" }, "Yale ECON 252 · 2011")
    ),
    el("nav", { class: "navtabs" },
      ...tabs.map(t => {
        const a = el("a", { href: t.href }, t.label);
        if (t.id === activeTab) a.classList.add("active");
        return a;
      })
    ),
    el("form", { class: "searchbox", onsubmit: (e) => { e.preventDefault(); doSearch(); } },
      el("input", { type: "search", placeholder: "搜尋名詞 / 內容 / 課次…", id: "topSearchInput" })
    ),
  );
  return bar;
}

function buildSidebar(lectures, activeId) {
  const ul = el("ul");
  for (const lec of lectures) {
    const a = el("a", { href: `lecture.html?id=${lec.id}` },
      el("span", { class: "num" }, `L${lec.num}`),
      el("span", { class: "ttl" }, lec.title_zh),
      el("span", { class: "track-dot" })
    );
    const li = el("li", { class: `track-${lec.track}` }, a);
    if (lec.id === activeId) a.classList.add("active");
    ul.appendChild(li);
  }
  return el("aside", { class: "sidebar" },
    el("h3", {}, "23 講清單"),
    ul,
    el("h3", { style: "margin-top:20px" }, "圖例"),
    el("div", { class: "muted", style: "font-size:0.82rem;padding:0 8px" },
      el("div", {}, "● 入門線（導論與行為）"),
      el("div", {}, "● 工具線（量化與定價）"),
      el("div", {}, "● 制度線（市場機構）"),
    ),
  );
}

function buildFooter() {
  return el("footer", { class: "footer" },
    "教材來源：",
    el("a", { href: "https://oyc.yale.edu/economics/econ-252-11", target: "_blank", rel: "noopener" }, "Open Yale Courses · ECON 252 (2011)"),
    "．Robert J. Shiller．中英對照逐字稿整理。本網站供教學分享使用。"
  );
}

function doSearch() {
  const q = document.getElementById("topSearchInput").value.trim();
  if (!q) return;
  location.href = `wiki.html?q=${encodeURIComponent(q)}`;
}

function getParam(k) {
  return new URLSearchParams(location.search).get(k);
}
