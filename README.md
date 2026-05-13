# Shiller《金融市場》— 給世界級金融家的核心知識站（v0.1）

把 Robert Shiller 在 Yale 開的 ECON 252（2011 春）23 講，做成一個可分享的靜態網站：

- **首頁**：使用指南 + 三條學習路徑（入門／工具／制度）+ 四個應用場景
- **逐字稿頁**：YouTube 嵌入 + 中英對照逐字稿（中英並排／上下交錯／僅中／僅英 四模式）
- **Wiki**：121 個 Shiller 核心名詞，**每條附從原始逐字稿擷取的真實 Shiller 段落引用**（不編造、可點連結驗證）
- **心智圖**：markmap 互動式知識點地圖

純靜態 HTML/CSS/JS、無 build step、可離線使用、可 zip 分享、可上 GitHub Pages。

---

## 本機開啟

```bash
cd "6. Tool/shiller-financial-markets"
python3 -m http.server 8000
# 開 http://localhost:8000
```

> **不要直接 file:// 打開 index.html** — 瀏覽器會封鎖 fetch 讀取 markdown，畫面會空白。一定要透過 http server。

---

## 公開分享：3 種方案

### A. GitHub Pages（推薦長期）
1. 在 GitHub 開一個 repo（如 `shiller-financial-markets-zh`）
2. 把本資料夾內容 push 到 main：
   ```bash
   cd "6. Tool/shiller-financial-markets"
   git init && git add . && git commit -m "init"
   git remote add origin https://github.com/<你>/<repo>.git
   git push -u origin main
   ```
3. Repo Settings → Pages → Source 選 `main / root` → 等 1 分鐘
4. 拿到網址 `https://<你>.github.io/<repo>/`

### B. Cloudflare Pages / Netlify Drop（5 分鐘）
- Netlify：去 https://app.netlify.com/drop 把整個資料夾拖上去 → 拿到 `xxx.netlify.app` 網址
- Cloudflare Pages：登入後 → Create → Upload assets → 拖整個資料夾上去 → 自動部署

### C. 壓 zip 寄人
```bash
cd "6. Tool"
zip -r shiller-financial-markets.zip shiller-financial-markets
```
對方解壓後**仍需用本機 http server 開啟**（同上）。如果你想對方直接雙擊就能看，請改用方案 A 或 B。

---

## 檔案結構

```
shiller-financial-markets/
├── index.html              # 首頁（使用說明 + 學習路徑）
├── lecture.html            # 逐字稿頁
├── wiki.html               # 名詞 Wiki
├── mindmap.html            # 心智圖
├── assets/
│   ├── css/styles.css
│   └── js/
│       ├── common.js       # 共用頂欄、側邊欄、資料載入
│       ├── home.js
│       ├── lecture.js      # 逐字稿解析 + 渲染
│       ├── wiki.js
│       └── mindmap.js
├── data/
│   ├── lectures.json       # 23 講 metadata + 章節索引 + YT id（v0.1 已完整）
│   ├── glossary.json       # 18 個核心詞條（v0.1 留薄）
│   └── mindmap.md          # markmap 大綱（v0.1 全課程骨架）
└── transcripts/            # L01.md ~ L23.md（從 1. Information/Interview/Robert Shiller 複製）
```

---

## v0.1 範圍（這版做了什麼）

- ✅ 4 頁框架、側邊欄導覽、頂欄路由、頁面間跳轉
- ✅ 23 講逐字稿全部載入，中英自動分段（用 CJK 偵測）
- ✅ YouTube 全部 23 個影片 id 已從 OYC 自動抓取並寫入 `data/lectures.json`
- ✅ 4 種顯示模式（並排 / 交錯 / 僅中 / 僅英）切換並記憶選擇
- ✅ 首頁三條學習路徑、四個應用場景、五步使用指南
- ✅ Wiki：121 個核心名詞、5 分類過濾、即時搜尋、每條附真實 Shiller 段落引用與可點出處
- ✅ 心智圖：全課程骨架（六大主題、約 80 個節點）

## v1.0+ 後續可擴充

- Wiki 詞條擴充到 150+（再深入專業細項）
- 心智圖加入「每節要點」層
- 全文搜尋（已預留 UI，下一輪接 MiniSearch）
- 影片時間戳 ↔ 逐字稿段落雙向跳轉
- 個人筆記／重點標記（localStorage）

---

## 更新逐字稿來源

每次原始 `.md` 在 `1. Information/Interview/Robert Shiller/` 變動後，重新同步：

```bash
cd "6. Tool/shiller-financial-markets/transcripts"
rm L*.md
for f in "../../../1. Information/Interview/Robert Shiller/"*.md; do
  base=$(basename "$f")
  num=$(echo "$base" | grep -oE 'L[0-9]+|Lecture[0-9]+' | head -1 | sed -E 's/L|Lecture//g')
  [ -n "$num" ] && cp "$f" "$(printf "L%02d.md" "$num")"
done
```

如果改了標題或章節，重跑 `lectures.json` 產生器（見 `/tmp/build_lectures.py`）。

---

## 來源與授權

教材來源：[Open Yale Courses ECON 252 (2011)](https://oyc.yale.edu/economics/econ-252-11)，按 CC BY-NC-SA 釋出。
中文翻譯／整理為個人作業，供教學參考。
本網站本身為靜態整理，無商業用途。
