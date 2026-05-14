/* analytics.js — Cloudflare Web Analytics loader
 *
 * 設定步驟：
 * 1. 去 https://dash.cloudflare.com → 免費註冊
 * 2. 左側 Analytics & Logs → Web Analytics → Add a site
 * 3. 填網址：jackjack861114.github.io/shiller-financial-markets
 * 4. CF 會給一段 script 標籤，找裡面的 data-cf-beacon='{"token":"XXXX..."}'
 * 5. 把 XXXX 那串 token 貼下面的 CF_BEACON_TOKEN
 * 6. git add . && git commit -m "Enable analytics" && git push
 * 7. 1-2 分鐘後同事造訪會被計入；回 CF dashboard 看儀表板
 *
 * 預設不會在 localhost / 127.0.0.1 觸發，所以本機開發不會污染統計。
 */

const CF_BEACON_TOKEN = "732f4bd9bdfa465986d3d57fafdab9d0";

(function () {
  if (
    !CF_BEACON_TOKEN ||
    CF_BEACON_TOKEN === "PASTE_YOUR_TOKEN_HERE" ||
    location.hostname === "localhost" ||
    location.hostname === "127.0.0.1" ||
    location.protocol === "file:"
  ) {
    return;
  }
  const s = document.createElement("script");
  s.defer = true;
  s.src = "https://static.cloudflareinsights.com/beacon.min.js";
  s.setAttribute("data-cf-beacon", JSON.stringify({ token: CF_BEACON_TOKEN }));
  document.head.appendChild(s);
})();
