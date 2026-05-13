/* home.js — index page */

const TRACKS = {
  intro:  { name: "入門線", desc: "建立金融的世界觀、風險直覺與心理學底子。剛入行的金融人從這條線開始。", color: "#2a6f97" },
  tools:  { name: "工具線", desc: "投組分散、有效市場、CAPM、期貨選擇權——客戶問「為什麼」時的硬底子。", color: "#386641" },
  institutions: { name: "制度線", desc: "從銀行、保險、央行到交易所——理解你工作的世界是怎麼運轉的。", color: "#8b3a2b" },
};

async function initHomePage() {
  document.body.prepend(buildTopbar("home"));

  const data = await loadLectures();
  document.querySelector(".layout").prepend(buildSidebar(data.lectures, null));

  // render tracks
  const grid = document.getElementById("trackGrid");
  for (const [trackId, t] of Object.entries(TRACKS)) {
    const lecturesInTrack = data.lectures.filter(l => l.track === trackId);
    const list = el("ol");
    for (const lec of lecturesInTrack) {
      list.appendChild(el("li", {},
        el("a", { href: `lecture.html?id=${lec.id}` }, `L${lec.num}｜${lec.title_zh}`)
      ));
    }
    const card = el("div", { class: `track-card ${trackId}` },
      el("h3", {}, t.name + ` · ${lecturesInTrack.length} 講`),
      el("div", { class: "why" }, t.desc),
      list
    );
    grid.appendChild(card);
  }

  document.body.appendChild(buildFooter());
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initHomePage);
} else {
  initHomePage();
}
