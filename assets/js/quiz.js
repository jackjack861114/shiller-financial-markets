/* quiz.js — Robert Shiller Financial Markets Knowledge Quiz */

const QUIZ_DATA_URL = "data/quiz.json";
const LS_KEY = "shiller_leaderboard_v1";

let QUIZ = null;         // full data from quiz.json
let state = {
  role: null,           // selected role object
  playerName: "",
  questions: [],        // shuffled questions for this session
  current: 0,           // current question index
  score: 0,             // points earned
  answered: false,      // has user answered current q
};

// ── helpers ──────────────────────────────────────────────────────────

function show(id) {
  document.querySelectorAll(".quiz-screen").forEach(el => el.classList.remove("active"));
  document.getElementById(id).classList.add("active");
}

function scoreToPoints(correct) { return correct ? 5 : 0; }
function totalPossible() { return state.questions.length * 12.5; }

function shuffle(arr) {
  const a = [...arr];
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

function getLectureNum(id) { return parseInt(id.replace("L", ""), 10); }

// ── leaderboard (localStorage) ───────────────────────────────────────

function loadLB() {
  try { return JSON.parse(localStorage.getItem(LS_KEY) || "[]"); }
  catch { return []; }
}

function saveLB(entries) {
  localStorage.setItem(LS_KEY, JSON.stringify(entries));
}

function addToLB(entry) {
  const lb = loadLB();
  lb.push(entry);
  lb.sort((a, b) => b.score - a.score || a.ts - b.ts);
  saveLB(lb.slice(0, 100)); // cap at 100 entries
}

function exportScore(entry) {
  const raw = JSON.stringify(entry);
  return btoa(unescape(encodeURIComponent(raw)));
}

function importScore(code) {
  try {
    const raw = decodeURIComponent(escape(atob(code.trim())));
    const entry = JSON.parse(raw);
    if (!entry.name || typeof entry.score !== "number" || !entry.role) throw new Error("invalid");
    return entry;
  } catch {
    return null;
  }
}

// ── render leaderboard ───────────────────────────────────────────────

function renderLeaderboard() {
  const lb = loadLB();
  const wrap = document.getElementById("leaderboard");
  if (!wrap) return;

  if (!lb.length) {
    wrap.innerHTML = '<div class="lb-empty">還沒有記錄。完成測驗後，你的分數會出現在這裡。</div>';
    return;
  }

  const medals = ["🥇", "🥈", "🥉"];
  const rows = lb.map((e, i) => {
    const roleObj = QUIZ ? QUIZ.roles.find(r => r.id === e.role) : null;
    const roleName = roleObj ? roleObj.name_zh : e.role;
    const roleIcon = roleObj ? roleObj.icon : "👤";
    const medal = i < 3 ? medals[i] : `${i + 1}`;
    const dateStr = e.ts ? new Date(e.ts).toLocaleDateString("zh-TW") : "";
    const pct = Math.round((e.score / 100) * 100);
    return `
      <div class="lb-row ${i === 0 ? "lb-top" : ""}">
        <span class="lb-rank">${medal}</span>
        <span class="lb-name">${escHtml(e.name)}</span>
        <span class="lb-role">${roleIcon} ${escHtml(roleName)}</span>
        <span class="lb-score">${e.score.toFixed(1)} 分</span>
        <span class="lb-bar-wrap"><span class="lb-bar" style="width:${pct}%"></span></span>
        <span class="lb-date">${dateStr}</span>
      </div>`;
  }).join("");

  wrap.innerHTML = `<div class="lb-header">
    <span>名次</span><span>姓名</span><span>角色</span><span>分數</span><span></span><span>日期</span>
  </div>${rows}`;
}

function escHtml(s) {
  return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

// ── screen 1: role grid ───────────────────────────────────────────────

function renderRoleGrid() {
  const grid = document.getElementById("roleGrid");
  if (!grid || !QUIZ) return;

  grid.innerHTML = QUIZ.roles.map(role => `
    <button class="role-card" data-role="${role.id}" style="--role-color:${role.color}">
      <span class="role-icon">${role.icon}</span>
      <span class="role-name">${role.name_zh}</span>
      <span class="role-name-en">${role.name_en}</span>
      <span class="role-desc">${role.desc_zh}</span>
      <span class="role-lectures">${role.lectures.join(" · ")}</span>
    </button>`).join("");

  grid.querySelectorAll(".role-card").forEach(btn => {
    btn.addEventListener("click", () => selectRole(btn.dataset.role));
  });
}

function selectRole(roleId) {
  state.role = QUIZ.roles.find(r => r.id === roleId);
  if (!state.role) return;

  // update display badge
  const disp = document.getElementById("selectedRoleDisplay");
  if (disp) {
    disp.style.setProperty("--role-color", state.role.color);
    disp.innerHTML = `<span>${state.role.icon}</span><span>${state.role.name_zh}</span>`;
  }

  // clear name input
  const nameInput = document.getElementById("nameInput");
  if (nameInput) nameInput.value = "";

  show("screenName");
  if (nameInput) setTimeout(() => nameInput.focus(), 100);
}

// ── screen 2: name form ───────────────────────────────────────────────

document.addEventListener("DOMContentLoaded", () => {
  const nameForm = document.getElementById("nameForm");
  if (nameForm) {
    nameForm.addEventListener("submit", e => {
      e.preventDefault();
      const val = document.getElementById("nameInput").value.trim();
      if (!val) { document.getElementById("nameInput").focus(); return; }
      state.playerName = val;
      startQuiz();
    });
  }

  const backBtn = document.getElementById("backToRoles");
  if (backBtn) backBtn.addEventListener("click", () => show("screenRole"));

  const nextBtn = document.getElementById("nextBtn");
  if (nextBtn) nextBtn.addEventListener("click", nextQuestion);

  const retryBtn = document.getElementById("retryBtn");
  if (retryBtn) retryBtn.addEventListener("click", () => {
    state.questions = shuffle(QUIZ.questions[state.role.id]);
    state.current = 0; state.score = 0; state.answered = false;
    startQuiz();
  });

  const changeRoleBtn = document.getElementById("changeRoleBtn");
  if (changeRoleBtn) changeRoleBtn.addEventListener("click", () => show("screenRole"));

  const exportBtn = document.getElementById("exportBtn");
  if (exportBtn) exportBtn.addEventListener("click", handleExport);

  const importBtn = document.getElementById("importBtn");
  if (importBtn) importBtn.addEventListener("click", handleImport);

  const clearLBBtn = document.getElementById("clearLBBtn");
  if (clearLBBtn) clearLBBtn.addEventListener("click", () => {
    if (confirm("確定要清空整個排行榜嗎？")) { saveLB([]); renderLeaderboard(); }
  });
});

// ── screen 3: quiz ────────────────────────────────────────────────────

function startQuiz() {
  const questions = QUIZ.questions[state.role.id];
  state.questions = shuffle(questions);
  state.current = 0;
  state.score = 0;
  state.answered = false;

  // fill identity header
  const roleBadge = document.getElementById("qRoleBadge");
  if (roleBadge) {
    roleBadge.textContent = `${state.role.icon} ${state.role.name_zh}`;
    roleBadge.style.setProperty("--role-color", state.role.color);
  }
  const pName = document.getElementById("qPlayerName");
  if (pName) pName.textContent = state.playerName;

  show("screenQuiz");
  renderQuestion();
}

function renderQuestion() {
  const q = state.questions[state.current];
  const total = state.questions.length;

  // progress
  document.getElementById("qProgress").textContent = `第 ${state.current + 1} 題 / 共 ${total} 題`;
  document.getElementById("qProgressFill").style.width = `${(state.current / total) * 100}%`;
  document.getElementById("qScore").textContent = `${state.score.toFixed(1)} 分`;

  // meta
  const lectureNum = getLectureNum(q.lecture_id);
  document.getElementById("qMeta").innerHTML =
    `<span class="q-lecture-tag">L${lectureNum.toString().padStart(2, "0")}</span>`;

  // question text
  document.getElementById("qText").textContent = q.text;

  // choices
  const choicesEl = document.getElementById("qChoices");
  const letters = ["A", "B", "C", "D"];
  choicesEl.innerHTML = q.choices.map((c, i) =>
    `<button class="choice-btn" data-idx="${i}">
      <span class="choice-letter">${letters[i]}</span>
      <span class="choice-text">${escHtml(c)}</span>
    </button>`
  ).join("");

  choicesEl.querySelectorAll(".choice-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      if (state.answered) return;
      answerQuestion(parseInt(btn.dataset.idx, 10));
    });
  });

  // hide feedback
  document.getElementById("feedbackPanel").style.display = "none";
  state.answered = false;

  // scroll to top of quiz card
  document.getElementById("questionCard").scrollIntoView({ behavior: "smooth", block: "nearest" });
}

function answerQuestion(idx) {
  if (state.answered) return;
  state.answered = true;

  const q = state.questions[state.current];
  const isCorrect = idx === q.correct;
  if (isCorrect) state.score += scoreToPoints(true);

  // mark choices
  const btns = document.querySelectorAll(".choice-btn");
  btns.forEach((btn, i) => {
    btn.disabled = true;
    if (i === q.correct) btn.classList.add("correct");
    else if (i === idx && !isCorrect) btn.classList.add("wrong");
  });

  // update score display
  document.getElementById("qScore").textContent = `${state.score.toFixed(1)} 分`;

  // show feedback
  const panel = document.getElementById("feedbackPanel");
  panel.style.display = "block";

  document.getElementById("feedbackVerdict").innerHTML = isCorrect
    ? `<span class="verdict-correct">✓ 正確！</span>`
    : `<span class="verdict-wrong">✗ 答錯了</span><span class="verdict-correct-label"> 正確答案：${["A","B","C","D"][q.correct]}</span>`;

  document.getElementById("feedbackExplanation").textContent = q.explanation;
  document.getElementById("feedbackQuote").textContent = `"${q.shiller_quote}"`;

  const lectureNum = getLectureNum(q.lecture_id);
  const lectureLabel = `L${lectureNum.toString().padStart(2, "0")}`;
  document.getElementById("feedbackLinks").innerHTML = `
    <a class="feedback-link" href="https://www.youtube.com/watch?v=${q.youtube_id}" target="_blank" rel="noopener">
      ▶ 觀看 YouTube 影片（${lectureLabel}）
    </a>
    <a class="feedback-link" href="${q.oyc_url}" target="_blank" rel="noopener">
      🎓 Open Yale Courses 原始頁面
    </a>
    <a class="feedback-link" href="lecture.html?id=${q.lecture_id}" target="_blank" rel="noopener">
      📄 查看完整逐字稿
    </a>`;

  // change next button text on last question
  const nextBtn = document.getElementById("nextBtn");
  if (nextBtn) {
    nextBtn.textContent = state.current + 1 >= state.questions.length ? "查看結果 →" : "下一題 →";
  }

  panel.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

function nextQuestion() {
  state.current++;
  if (state.current >= state.questions.length) {
    finishQuiz();
  } else {
    renderQuestion();
  }
}

// ── screen 4: results ─────────────────────────────────────────────────

function finishQuiz() {
  const score = parseFloat(state.score.toFixed(1));
  const pct = Math.round((score / 100) * 100);

  // store result
  const entry = {
    name: state.playerName,
    role: state.role.id,
    score,
    ts: Date.now(),
  };
  addToLB(entry);

  // render results
  const roleBadge = document.getElementById("resultRoleBadge");
  if (roleBadge) {
    roleBadge.style.setProperty("--role-color", state.role.color);
    roleBadge.innerHTML = `<span>${state.role.icon}</span><span>${state.role.name_zh}</span>`;
  }

  document.getElementById("resultScore").innerHTML =
    `<span class="result-num">${score}</span><span class="result-denom"> / 100 分</span>`;

  document.getElementById("resultPlayerName").textContent = `${state.playerName} · ${state.role.name_zh}`;

  let msg = "", emoji = "";
  if (pct >= 90) { msg = "Shiller 本人也會對你滿意！"; emoji = "🏆"; }
  else if (pct >= 75) { msg = "紮實的金融知識基礎，繼續精進！"; emoji = "🎯"; }
  else if (pct >= 50) { msg = "不錯的開始，多看幾次原文會更強。"; emoji = "📚"; }
  else { msg = "繼續加油！Shiller 的原文值得細讀。"; emoji = "💪"; }

  document.getElementById("resultMsg").innerHTML = `${emoji} ${msg}`;

  renderLeaderboard();
  show("screenResults");
  window.scrollTo({ top: 0, behavior: "smooth" });
}

// ── export / import ───────────────────────────────────────────────────

function handleExport() {
  const lb = loadLB();
  const entry = lb.find(e =>
    e.name === state.playerName &&
    e.role === (state.role ? state.role.id : "") &&
    e.score === parseFloat(state.score.toFixed(1))
  ) || lb[0];

  if (!entry) { alert("請先完成測驗再匯出！"); return; }
  const code = exportScore(entry);

  navigator.clipboard.writeText(code).then(() => {
    alert(`分數碼已複製到剪貼簿！\n\n請貼給同事，讓他們匯入到排行榜。\n\n分數碼：\n${code}`);
  }).catch(() => {
    prompt("複製以下分數碼，貼給同事：", code);
  });
}

function handleImport() {
  const code = document.getElementById("importInput").value.trim();
  const msgEl = document.getElementById("importMsg");
  if (!code) { msgEl.textContent = "請貼入分數碼"; msgEl.className = "import-msg error"; return; }

  const entry = importScore(code);
  if (!entry) {
    msgEl.textContent = "無效的分數碼，請確認是否完整複製";
    msgEl.className = "import-msg error";
    return;
  }

  addToLB(entry);
  document.getElementById("importInput").value = "";
  renderLeaderboard();

  const roleObj = QUIZ ? QUIZ.roles.find(r => r.id === entry.role) : null;
  const roleName = roleObj ? roleObj.name_zh : entry.role;
  msgEl.textContent = `✓ 已匯入 ${entry.name}（${roleName}）的分數：${entry.score} 分`;
  msgEl.className = "import-msg success";
}

// ── init ──────────────────────────────────────────────────────────────

async function initQuiz() {
  const data = await loadLectures();
  const resp = await fetch(QUIZ_DATA_URL);
  QUIZ = await resp.json();

  // build sidebar & topbar
  document.body.prepend(buildTopbar("quiz"));
  document.querySelector(".layout").prepend(buildSidebar(data.lectures, null));
  document.body.appendChild(buildFooter());

  renderRoleGrid();
  show("screenRole");
}

initQuiz().catch(console.error);
