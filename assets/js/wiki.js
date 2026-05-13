/* wiki.js — glossary view with category filter + search */

async function loadGlossary() {
  const resp = await fetch("data/glossary.json");
  return resp.json();
}

function renderWiki(gloss, filterCat = "all", query = "") {
  const list = document.getElementById("wikiList");
  list.innerHTML = "";
  const q = query.trim().toLowerCase();
  let count = 0;

  for (const t of gloss.terms) {
    if (filterCat !== "all" && t.category !== filterCat) continue;
    if (q) {
      const hay = (t.term_en + " " + t.term_zh + " " + (t.def_en||"") + " " + (t.def_zh||"") + " " + (t.shiller_quote||"")).toLowerCase();
      if (!hay.includes(q)) continue;
    }
    count++;
    const card = el("div", { class: "wiki-card" },
      el("div", { class: "term" },
        el("span", {}, t.term_zh),
        el("span", { class: "en" }, t.term_en)
      ),
      el("div", {},
        el("span", { class: "cat-pill" }, gloss.categories[t.category] || t.category),
      ),
      el("div", { class: "def-zh" }, t.def_zh),
      el("div", { class: "def-en" }, t.def_en),
      t.shiller_quote ? el("blockquote", { class: "quote" },
        `「${t.shiller_quote}」`,
        t.quote_source ? el("div", { class: "quote-src" },
          "— 引自 ",
          el("a", { href: `lecture.html?id=${t.quote_source}` }, t.quote_source)
        ) : null
      ) : null,
      el("div", { class: "sources" },
        el("span", { class: "muted" }, "相關課次："),
        ...t.sources.map(s => el("a", { href: `lecture.html?id=${s}` }, s))
      )
    );
    list.appendChild(card);
  }

  document.getElementById("wikiCount").textContent = `${count} 個詞條`;
}

async function initWikiPage() {
  document.body.prepend(buildTopbar("wiki"));
  const data = await loadLectures();
  const layout = document.querySelector(".layout");
  layout.prepend(buildSidebar(data.lectures, null));

  const gloss = await loadGlossary();
  document.title = "金融名詞 Wiki — Shiller《金融市場》";

  // filters
  const filterBar = document.getElementById("wikiFilters");
  let active = "all";
  let query = getParam("q") || "";
  if (query) document.getElementById("wikiSearch").value = query;

  const cats = [["all", "全部"], ...Object.entries(gloss.categories)];
  for (const [id, label] of cats) {
    const b = el("button", { onclick: () => {
      active = id;
      for (const x of filterBar.querySelectorAll("button")) x.classList.remove("active");
      b.classList.add("active");
      renderWiki(gloss, active, document.getElementById("wikiSearch").value);
    }}, label);
    if (id === "all") b.classList.add("active");
    filterBar.appendChild(b);
  }

  document.getElementById("wikiSearch").addEventListener("input", (e) => {
    renderWiki(gloss, active, e.target.value);
  });

  renderWiki(gloss, active, query);

  document.body.appendChild(buildFooter());
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initWikiPage);
} else {
  initWikiPage();
}
