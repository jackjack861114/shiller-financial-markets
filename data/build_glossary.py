#!/usr/bin/env python3
"""Build glossary.json from curated term specs + real Shiller quotes
extracted from transcripts.

Rules:
- def_en / def_zh: hand-written reference definitions (not attributed to Shiller).
- shiller_quote: must be a verbatim paragraph from the listed lectures' English
  body (Shiller's speech, or in guest lectures attributed clearly). If none
  found, leave null and let the renderer hide that field.
- sources: lecture IDs where the term is taught/used.
"""
from __future__ import annotations
import json, re
from pathlib import Path

ROOT = Path("/Users/jack/Desktop/DATABASE/6. Tool/shiller-financial-markets")
TR = ROOT / "transcripts"

CJK = re.compile(r"[぀-ヿ㐀-鿿豈-﫿＀-￯]")

def is_cjk(s: str) -> bool:
    return bool(CJK.search(s))

def strip_frontmatter(text: str) -> str:
    if text.startswith("---"):
        idx = text.find("\n---", 3)
        if idx > 0:
            return text[idx + 4:].lstrip("\n")
    return text

def load_lecture(lid: str) -> list[tuple[str, str]]:
    """Return list of (kind, text) where kind in {speaker, en, zh, chapter}."""
    raw = (TR / f"{lid}.md").read_text(encoding="utf-8")
    body = strip_frontmatter(raw)
    paragraphs = []
    cur_speaker = "Professor Robert Shiller"
    cur_chapter = None
    blocks = re.split(r"\n\s*\n", body)
    for blk in blocks:
        blk = blk.strip()
        if not blk:
            continue
        if blk.startswith("# "):
            continue
        m = re.match(r"^## Chapter (\d+)\.\s*(.+)$", blk.splitlines()[0])
        if m:
            cur_chapter = (int(m.group(1)), m.group(2).strip())
            continue
        if re.match(r"^#{1,4}\s", blk):
            continue
        m = re.match(r"^\*\*(.+?)[:：]?\*\*[:：]?\s*$", blk)
        if m:
            cur_speaker = m.group(1).split("|")[0].split("｜")[0].strip()
            continue
        # Inline speaker prefix: **Speaker：** body
        m2 = re.match(r"^\*\*(.+?)[:：]?\*\*[:：]?\s+(.+)$", blk, flags=re.DOTALL)
        if m2:
            cur_speaker = m2.group(1).split("|")[0].split("｜")[0].strip()
            blk = m2.group(2).strip()
        # Skip blockquote notes
        if blk.startswith(">"):
            continue
        if not blk:
            continue
        kind = "zh" if is_cjk(blk) else "en"
        paragraphs.append({
            "kind": kind, "text": blk,
            "speaker": cur_speaker,
            "chapter": cur_chapter[0] if cur_chapter else None,
        })
    return paragraphs

LECTURE_CACHE = {}
def get(lid):
    if lid not in LECTURE_CACHE:
        LECTURE_CACHE[lid] = load_lecture(lid)
    return LECTURE_CACHE[lid]

def find_quote(lectures: list[str], patterns: list[str], shiller_only: bool = True, max_len: int = 540) -> tuple[str | None, str | None]:
    """Find best Shiller paragraph mentioning any of patterns.

    Returns (quote, source_lid). Best = shortest paragraph that contains the
    pattern intact (full word match) and is not too long.
    """
    best = None
    best_score = 1e9
    best_lid = None
    for lid in lectures:
        for p in get(lid):
            if p["kind"] != "en":
                continue
            if shiller_only and "Shiller" not in p["speaker"] and "Professor" not in p["speaker"]:
                continue
            text = p["text"]
            tlow = text.lower()
            hit = False
            for pat in patterns:
                if pat.startswith("re:"):
                    if re.search(pat[3:], text, flags=re.IGNORECASE):
                        hit = True; break
                else:
                    if pat.lower() in tlow:
                        hit = True; break
            if not hit:
                continue
            # prefer medium-length paragraphs that contain a complete sentence with the term
            length = len(text)
            # bonus for "is", "means", "called", "I call" (definitional)
            defy = any(re.search(rf"\b{kw}\b", tlow) for kw in ["is called", "we call", "i call", "means", "defined", "definition", "refers to"])
            score = abs(length - 350) - (200 if defy else 0)
            if score < best_score:
                best = text
                best_score = score
                best_lid = lid
    if best and len(best) > max_len:
        # Pick the first sentence(s) up to max_len ending at sentence boundary
        sents = re.split(r"(?<=[.!?])\s+", best)
        out = ""
        for s in sents:
            if len(out) + len(s) > max_len:
                break
            out += s + " "
        best = out.strip() or best[:max_len].rstrip() + "…"
    return best, best_lid

# =========================================================================
# TERM SPECS — 100 entries
# Each entry: en, zh, cat, L (source lectures), search (case-insensitive),
# def_zh, def_en. Quote is auto-extracted.
# =========================================================================

CATEGORIES = {
    "risk": "風險與機率",
    "behavior": "行為財務",
    "markets": "市場與制度",
    "instruments": "金融工具",
    "policy": "監管與政策",
}

TERMS = [
    # ============== RISK (16) ==============
    dict(en="Risk Pooling", zh="風險匯集", cat="risk", L=["L05"],
         search=["risk pooling", "pool the risk"],
         def_zh="保險的根本原理——只要許多保戶的風險彼此獨立，大數法則就會讓總體結果可預測，即使個別事件無法預測。",
         def_en="Insurance's core principle: independent risks across many policyholders allow the law of large numbers to make aggregate outcomes predictable."),
    dict(en="Law of Large Numbers", zh="大數法則", cat="risk", L=["L02","L05"],
         search=["law of large numbers"],
         def_zh="大量獨立同分布隨機事件的平均，會收斂到其期望值。保險與分散投資的數學基礎。",
         def_en="The average of many independent identically distributed random variables converges to its expected value—the math behind insurance and diversification."),
    dict(en="Central Limit Theorem", zh="中央極限定理", cat="risk", L=["L02","L03"],
         search=["central limit theorem"],
         def_zh="許多獨立隨機變數之和（或平均）會趨近常態分配，無論原本分配為何。常被當成「為什麼許多金融現象呈鐘形」的理由。",
         def_en="Sums (or averages) of many independent random variables tend toward a normal distribution—often invoked to justify normality assumptions in finance."),
    dict(en="Expected Value", zh="期望值", cat="risk", L=["L02"],
         search=["expected value", "expectation"],
         def_zh="一個隨機變數的機率加權平均；對連續分配是 ∫x·f(x)dx。所有風險—報酬權衡的起點。",
         def_en="Probability-weighted average of a random variable's possible outcomes; the starting point of all risk-return analysis."),
    dict(en="Variance & Covariance", zh="變異數與共變異數", cat="risk", L=["L02","L04"],
         search=["variance", "covariance"],
         def_zh="變異數衡量單一變數圍繞期望值的散布；共變異數衡量兩變數同向／反向移動的程度。Markowitz 投組理論的兩個關鍵原料。",
         def_en="Variance measures spread of one variable; covariance measures how two variables move together. The two ingredients Markowitz needs to compute optimal portfolios."),
    dict(en="Standard Deviation", zh="標準差", cat="risk", L=["L02"],
         search=["standard deviation"],
         def_zh="變異數的平方根；金融上把它當作「風險」最常用的單一數字。",
         def_en="Square root of variance; the most common one-number summary of 'risk' in finance."),
    dict(en="Independence (statistical)", zh="統計獨立性", cat="risk", L=["L02"],
         search=["independence", "independent risks", "failure of independence"],
         def_zh="兩事件機率相乘不變——彼此不影響。Shiller 強調：金融危機的本質就是「以為獨立、結果不獨立」。",
         def_en="Two events are independent when one gives no information about the other. Shiller stresses: financial crises happen because supposedly independent risks turn out correlated."),
    dict(en="Fat Tails", zh="肥尾分配", cat="risk", L=["L02"],
         search=["fat tail", "fat-tailed", "tails are fat"],
         def_zh="極端事件機率比常態分配預測得高的分配；金融資產報酬普遍是肥尾，意味「不可能發生」的事其實常發生。",
         def_en="Distributions where extreme events are more probable than the normal distribution predicts; financial returns are notoriously fat-tailed."),
    dict(en="Excess Volatility", zh="超額波動", cat="risk", L=["L06","L07"],
         search=["excess volatility", "too volatile", "volatility puzzle", "way more variable"],
         def_zh="Shiller 1981 年標誌性發現：股價波動遠大於其後續股利現值所能解釋；對有效市場假說的最強反駁之一。",
         def_en="Shiller's signature 1981 finding: stock prices fluctuate far more than the present value of subsequent dividends can justify—a key challenge to the efficient markets hypothesis."),
    dict(en="Random Walk", zh="隨機漫步", cat="risk", L=["L07"],
         search=["random walk"],
         def_zh="每期價格變動皆獨立隨機，過去不含未來資訊。被當成「市場有效」的推論，但 Shiller 認為實證上並不成立。",
         def_en="Model in which each price change is an independent random draw—often treated as a consequence of market efficiency, though Shiller disputes its empirical basis."),
    dict(en="Mean Reversion", zh="均值回歸", cat="risk", L=["L07"],
         search=["mean reverting", "mean reversion", "revert to", "reverts to"],
         def_zh="價格／報酬長期會回到歷史平均的傾向，與隨機漫步矛盾。CAPE 比率高時長期報酬偏低，是 Shiller 的典型案例。",
         def_en="Tendency of prices/returns to revert toward long-run averages—contradicting random walk. High CAPE predicting low long-run returns is Shiller's textbook case."),
    dict(en="Sharpe Ratio", zh="Sharpe 比率", cat="risk", L=["L07"],
         search=["sharpe ratio", "sharpe-ratio"],
         def_zh="（報酬 − 無風險利率）÷ 標準差。每承擔一單位風險換到多少報酬；可被賣尾部風險的策略短期粉飾。",
         def_en="(Return − risk-free rate) ÷ standard deviation. Reward per unit of risk; can be gamed by writing tail-risk options that look smooth until they aren't."),
    dict(en="Beta (β)", zh="Beta 係數", cat="risk", L=["L04","L02"],
         search=["beta", "systematic risk", "β"],
         def_zh="個別資產報酬對市場報酬的迴歸係數，衡量「無法分散掉的市場風險」。CAPM 中只有 beta 該被定價。",
         def_en="Regression slope of an asset's return on the market's; measures undiversifiable market risk. In CAPM, only beta should be priced."),
    dict(en="Systematic vs. Idiosyncratic Risk", zh="系統性與特異風險", cat="risk", L=["L02","L04"],
         search=["systematic", "idiosyncratic"],
         def_zh="系統性風險影響所有資產（無法分散）；特異風險只影響單一資產（可分散）。CAPM 假設只有前者得到溢酬。",
         def_en="Systematic risk affects all assets (can't be diversified away); idiosyncratic risk is asset-specific (diversifiable). CAPM says only systematic risk earns a premium."),
    dict(en="Efficient Markets Hypothesis (EMH)", zh="有效市場假說", cat="risk", L=["L07","L11"],
         search=["efficient markets hypothesis", "efficient market hypothesis", "efficient market"],
         def_zh="資產價格已反映所有可得資訊，主動分析無法持續超越市場。Shiller 認為這是「半真理」——適合當基準，當教條會誤事。",
         def_en="The idea that prices fully reflect available information. Shiller treats it as a 'half-truth'—useful benchmark, dangerous dogma."),
    dict(en="Capital Asset Pricing Model (CAPM)", zh="資本資產定價模型", cat="risk", L=["L04"],
         search=["capital asset pricing model", "capm"],
         def_zh="資產預期報酬 = 無風險利率 + β × 市場風險溢酬。建立在「所有人都持有市場組合」的前提上。",
         def_en="E[Ri] = Rf + β(Rm − Rf). The foundational pricing model assuming all investors hold the market portfolio."),
    dict(en="Efficient Portfolio Frontier", zh="有效投組前沿", cat="risk", L=["L04"],
         search=["efficient portfolio frontier", "efficient frontier"],
         def_zh="在每個風險水準下擁有最高預期報酬的投組集合；由 Markowitz 提出。",
         def_en="Set of portfolios offering the highest expected return for each level of risk; introduced by Markowitz."),
    dict(en="Tangency Portfolio", zh="切線投組", cat="risk", L=["L04"],
         search=["tangency portfolio", "tangency"],
         def_zh="從無風險利率畫切線與有效前沿的切點；理論上「人人都該持有」的唯一風險投組，再依風險偏好混入現金。",
         def_en="Point on the efficient frontier tangent to the line from the risk-free rate—the unique risky portfolio everyone should hold, mixed with cash to taste."),
    dict(en="Mutual Fund Theorem", zh="共同基金定理", cat="risk", L=["L04"],
         search=["mutual fund theorem"],
         def_zh="Tobin 證明：在有無風險資產時，所有投資人最佳風險投組相同（即切線投組），差別只在槓桿。",
         def_en="Tobin's result: with a risk-free asset, all investors hold the same risky portfolio (the tangency one); they differ only in leverage."),
    dict(en="Equity Premium Puzzle", zh="股權溢價謎題", cat="risk", L=["L04"],
         search=["equity premium puzzle", "equity premium"],
         def_zh="歷史上股票報酬遠高於債券，幅度大到無法用合理風險趨避偏好解釋。Mehra & Prescott (1985) 提出。",
         def_en="The historical excess return of stocks over bonds is too large to fit reasonable risk-aversion preferences—the puzzle posed by Mehra & Prescott (1985)."),
    dict(en="Head and Shoulders Pattern", zh="頭肩頂型態", cat="risk", L=["L07"],
         search=["head and shoulders"],
         def_zh="技術分析中三峰反轉型態。Shiller 用它示範技術分析的薄弱——人眼會在隨機漫步中看出根本不存在的型態。",
         def_en="Three-peak reversal pattern in technical analysis. Shiller uses it to illustrate how the eye 'sees' patterns in random walks that aren't there."),

    # ============== BEHAVIOR (12) ==============
    dict(en="Prospect Theory", zh="展望理論", cat="behavior", L=["L11"],
         search=["prospect theory"],
         def_zh="Kahneman & Tversky 提出：人以「參考點」評估得失，損失痛感大於同額獲利的快感（損失趨避），且對機率非線性加權。",
         def_en="Kahneman & Tversky: people evaluate gains/losses relative to a reference point, weight losses more than equivalent gains, and weight probabilities nonlinearly."),
    dict(en="Regression Analysis", zh="迴歸分析", cat="risk", L=["L02","L07"],
         search=["regression", "regression line"],
         def_zh="以最小平方法擬合資料的統計工具；用於估計 beta、檢驗市場效率、分解系統性與特異風險。",
         def_en="Least-squares fitting of data; used to estimate beta, test market efficiency, and decompose systematic vs. idiosyncratic risk."),
    dict(en="Regret Theory", zh="後悔理論", cat="behavior", L=["L11"],
         search=["regret theory", "regret"],
         def_zh="人預期事後會後悔某些決策，因此事前傾向迴避——能解釋為何投資人遲遲不認賠賣出。",
         def_en="People anticipate regret over decisions and avoid choices that might lead to it—helps explain reluctance to sell losers."),
    dict(en="Anchoring", zh="錨定", cat="behavior", L=["L11"],
         search=["anchoring", "anchor"],
         def_zh="任意給定的起始數字會不成比例地影響後續判斷；投資人常被買進價、整數價位、近期高低點錨定。",
         def_en="An arbitrary starting value disproportionately influences subsequent judgments; investors anchor on entry prices, round numbers, recent highs/lows."),
    dict(en="Overconfidence", zh="過度自信", cat="behavior", L=["L11"],
         search=["overconfidence"],
         def_zh="人會高估自己的知識、控制力與預測精度。Shiller 稱之為行為財務最穩健的實證發現。",
         def_en="People overestimate their knowledge, control, and forecasting precision. Shiller calls it perhaps the most robust finding in behavioral finance."),
    dict(en="Cognitive Dissonance", zh="認知失調", cat="behavior", L=["L11"],
         search=["cognitive dissonance"],
         def_zh="持有相互矛盾的信念造成心理不適，人會藉由忽略不利資訊、扭曲記憶來消解——導致投資人在套牢時否認事實。",
         def_en="The discomfort of holding contradictory beliefs leads people to ignore disconfirming information—why investors deny their thesis is broken."),
    dict(en="Representativeness Heuristic", zh="代表性捷思", cat="behavior", L=["L11"],
         search=["representativeness"],
         def_zh="以「像不像典型案例」評估機率，忽略基率。Kahneman & Tversky 的關鍵發現；投資人以為「過去三年績效好的基金」未來也好。",
         def_en="Judging probability by resemblance to a stereotype, ignoring base rates; investors mistake recent-winners for long-run winners."),
    dict(en="Social Contagion", zh="社會傳染", cat="behavior", L=["L11"],
         search=["social contagion", "contagion"],
         def_zh="信念、情緒、行為像病毒一樣在社群中擴散；Shiller 認為這是泡沫形成的主要機制。",
         def_en="Beliefs, emotions, and behaviors spread through populations like an epidemic; Shiller sees this as the core mechanism behind bubbles."),
    dict(en="Speculative Bubble", zh="投機性泡沫", cat="behavior", L=["L01","L02","L10"],
         search=["bubble", "speculative bubble"],
         def_zh="Shiller 的工作定義：價格被群眾故事與情緒推升至基本面無法支撐的水準，最終崩跌；可用情緒指標前瞻識別，不只是事後標籤。",
         def_en="Shiller's working definition: prices pushed by narratives and emotion to levels fundamentals can't sustain, ending in collapse—identifiable in real time via sentiment indicators."),
    dict(en="Praise-Worthiness", zh="值得被讚許", cat="behavior", L=["L11"],
         search=["praise-worthiness", "praise worthiness", "praise"],
         def_zh="Adam Smith 提出、Shiller 反覆援引：人深層渴望的不只是被讚許，而是「真的值得被讚許」。Shiller 用以解釋金融從業者的道德動機。",
         def_en="From Adam Smith and a recurring Shiller theme: people want not just to be praised but to be worthy of praise—he uses this to explain moral motivation in finance."),
    dict(en="Moral Judgment in Finance", zh="金融的道德判斷", cat="behavior", L=["L11","L23"],
         search=["moral judgment", "morality of finance"],
         def_zh="Shiller 反覆強調：人渴望「值得被讚許」（worthy of praise），不只是被讚許；金融的道德性是這份渴望的延伸。",
         def_en="Shiller's recurring theme: people want to be worthy of praise, not just praised; financial ethics flows from that desire."),
    dict(en="Manipulation & Deception", zh="操縱與欺騙", cat="behavior", L=["L11","L12"],
         search=["manipulation", "deception", "phishing"],
         def_zh="自由市場給予某些參與者操縱他人偏誤、誘人下單的機會；Shiller & Akerlof《Phishing for Phools》全書主題。",
         def_en="Free markets create opportunities to exploit others' biases—the central theme of Shiller & Akerlof's Phishing for Phools."),

    # ============== MARKETS (22) ==============
    dict(en="Bank Run", zh="銀行擠兌", cat="markets", L=["L13"],
         search=["bank run", "run on the bank"],
         def_zh="自我實現的存戶恐慌——若大家認為銀行付不出錢，搶先提領就是理性的，銀行因此倒閉。存款保險就是為了打斷這個循環。",
         def_en="Self-fulfilling depositor panic: if everyone believes the bank can't pay, withdrawing first is rational—and the bank collapses."),
    dict(en="Adverse Selection", zh="逆選擇", cat="markets", L=["L13","L05"],
         search=["adverse selection"],
         def_zh="資訊不對稱使「壞的標的」更可能成交——保險中體弱的人更想買壽險、銀行借款人裡風險高的更積極申貸。",
         def_en="Information asymmetry that draws the worst types into a market—the sickest buy life insurance, the riskiest borrowers apply hardest."),
    dict(en="Moral Hazard", zh="道德風險", cat="markets", L=["L13","L05"],
         search=["moral hazard"],
         def_zh="有保險／救援機制後，當事人會改變行為（變得不謹慎），因為損失由他人承擔。",
         def_en="Once insured or bailout-protected, an actor takes more risk because someone else bears the downside."),
    dict(en="Liquidity", zh="流動性", cat="markets", L=["L13"],
         search=["liquidity"],
         def_zh="資產轉換為現金的速度與成本；銀行的核心職能是「把長期不流動的貸款，變成短期可隨時提領的存款」。",
         def_en="Speed and cost of converting an asset to cash; banks' core function is transforming illiquid loans into liquid deposits."),
    dict(en="Fractional Reserve Banking", zh="部分準備金銀行制", cat="markets", L=["L13","L18"],
         search=["fractional reserve"],
         def_zh="銀行只保留存款的小部分作為準備金，其餘放貸——使貨幣供給能透過信貸創造放大。",
         def_en="Banks hold only a fraction of deposits as reserves and lend out the rest, multiplying money supply through credit creation."),
    dict(en="Deposit Insurance", zh="存款保險", cat="markets", L=["L13"],
         search=["deposit insurance", "FDIC"],
         def_zh="政府保證存款本金（美國為 FDIC，台灣為中央存保），消除擠兌動機；1933 年 Glass-Steagall 一併創立。",
         def_en="Government guarantee of bank deposits (FDIC in the U.S.) that removes the incentive to run; created alongside Glass-Steagall in 1933."),
    dict(en="Basel Accords", zh="Basel 協定", cat="markets", L=["L13","L18"],
         search=["basel", "basel iii"],
         def_zh="國際銀行監管框架（I/II/III），以風險加權資產為基底訂定資本與流動性要求。",
         def_en="International framework for bank regulation (I/II/III) setting capital and liquidity requirements based on risk-weighted assets."),
    dict(en="Capital Requirement", zh="資本要求", cat="markets", L=["L13","L18"],
         search=["capital requirement", "capital requirements"],
         def_zh="銀行必須以股東權益持有的最低資本比率，作為承擔損失的緩衝；Basel III 上看 8-10%+。",
         def_en="Minimum equity capital a bank must hold as a buffer against losses; Basel III pushes this to 8-10% plus buffers."),
    dict(en="Reserve Requirement", zh="法定準備金", cat="markets", L=["L18"],
         search=["reserve requirement", "required reserves"],
         def_zh="銀行必須在央行帳上保有的存款比率；過去是貨幣政策工具，2020 後美國已調為 0%。",
         def_en="Fraction of deposits banks must hold at the central bank; once a monetary policy tool, set to 0% in the U.S. since 2020."),
    dict(en="Federal Reserve System", zh="美國聯準會體系", cat="markets", L=["L18"],
         search=["federal reserve", "fed "],
         def_zh="美國央行，1913 年成立。雙重使命：物價穩定與最大就業。由理事會、12 家地區聯儲銀行、FOMC 組成。",
         def_en="The U.S. central bank, established 1913. Dual mandate: price stability and maximum employment. Comprises the Board, 12 regional banks, and the FOMC."),
    dict(en="Federal Funds Rate", zh="聯邦資金利率", cat="markets", L=["L18"],
         search=["federal funds rate", "fed funds"],
         def_zh="美國銀行間互相借隔夜準備金的利率，由 FOMC 設定目標區間；最重要的政策利率。",
         def_en="The overnight rate at which U.S. banks lend reserves to each other; the FOMC sets the target range. The key policy rate."),
    dict(en="Discount Window", zh="貼現窗口", cat="markets", L=["L18"],
         search=["discount window", "discount rate"],
         def_zh="銀行直接向央行借款的工具（利率為貼現率，通常高於聯邦資金利率），作為最後貸款人功能。",
         def_en="Facility for banks to borrow directly from the Fed at the discount rate—central bank's lender-of-last-resort function."),
    dict(en="Lender of Last Resort", zh="最後貸款人", cat="markets", L=["L18","L13"],
         search=["lender of last resort"],
         def_zh="Bagehot 原則：危機中央行應對流動性問題機構大量放款（但取良好抵押與懲罰性利率）以制止擠兌。",
         def_en="Bagehot's principle: in a crisis the central bank should lend freely against good collateral at a penalty rate to stop panics."),
    dict(en="Bank of England", zh="英格蘭銀行", cat="markets", L=["L18"],
         search=["bank of england"],
         def_zh="1694 年成立的世界第一家現代中央銀行；Shiller 視之為中央銀行制度的起源。",
         def_en="The world's first modern central bank (1694); Shiller treats it as the origin of central banking."),
    dict(en="National Banking Era", zh="國家銀行時代", cat="markets", L=["L18"],
         search=["national banking era", "national bank"],
         def_zh="美國 1863-1913 年的銀行體系：聯邦核可「國家銀行」發行國幣；終結於 Federal Reserve 創立。",
         def_en="The U.S. banking regime from 1863-1913: federally chartered 'national banks' issued national currency—ended by the founding of the Federal Reserve."),
    dict(en="Central Bank Independence", zh="央行獨立性", cat="markets", L=["L18"],
         search=["independent", "independence"],
         def_zh="央行貨幣決策不受短期政治壓力干預的制度設計；1970 年代後成為全球主流，降低通膨偏誤。",
         def_en="Institutional insulation of monetary policy from short-term political pressure; became the global norm post-1970s, reducing inflation bias."),
    dict(en="Investment Banking", zh="投資銀行業務", cat="markets", L=["L19"],
         search=["investment banking", "investment bank"],
         def_zh="承銷新發行證券、提供併購顧問、自營與機構業務。歷史上與商業銀行分離（Glass-Steagall），1999 年廢除後合流。",
         def_en="Underwriting new securities, advising on M&A, proprietary and institutional trading. Historically separated from commercial banking (Glass-Steagall), reunited after 1999."),
    dict(en="Shadow Banking", zh="影子銀行", cat="markets", L=["L19"],
         search=["shadow bank", "shadow banking"],
         def_zh="行使銀行職能（期限轉換、信用創造）但不受傳統銀行監管的機構與市場：貨幣市場基金、ABCP、回購、MBS 等。",
         def_en="Institutions and markets performing bank-like functions (maturity transformation, credit creation) outside bank regulation: MMFs, ABCP, repo, MBS."),
    dict(en="Repurchase Agreement (Repo)", zh="回購協議", cat="markets", L=["L19","L13"],
         search=["repo market", "repurchase agreement", "repurchase"],
         def_zh="以證券為抵押的短期借款（多半隔夜）；買回協議。Bear Stearns、Lehman 倒閉前都極度依賴 repo 融資。",
         def_en="Short-term collateralized borrowing (often overnight)—seller agrees to repurchase. Bear Stearns and Lehman both leaned heavily on repo before collapse."),
    dict(en="Broker vs. Dealer", zh="經紀商與自營商", cat="markets", L=["L21"],
         search=["broker", "dealer"],
         def_zh="Broker 為客戶代下單收佣金、不持部位；Dealer 以自己帳上部位買賣賺價差。同一公司常兼任兩者。",
         def_en="Broker executes for clients on commission, no position; Dealer trades from its own inventory on the spread. Same firm often does both."),
    dict(en="Market Order / Limit Order / Stop Order", zh="市價單／限價單／停損單", cat="markets", L=["L21"],
         search=["market order", "limit order", "stop order"],
         def_zh="市價單立即以最佳價成交；限價單只在達到指定價或更佳時成交；停損單在價格突破指定點時轉為市價單。",
         def_en="Market = execute now at best price; Limit = execute only at a specified price or better; Stop = becomes a market order when price hits a trigger."),
    dict(en="High-Frequency Trading", zh="高頻交易", cat="markets", L=["L21"],
         search=["high frequency", "high-frequency"],
         def_zh="毫秒級演算法交易，獲利來自做市價差、套利與微結構。Shiller 對其穩定性貢獻持懷疑。",
         def_en="Algorithmic trading on millisecond scales, profiting from market-making spreads, arbitrage, and microstructure. Shiller is skeptical of its stabilizing claims."),
    dict(en="Clearinghouse", zh="清算機構", cat="markets", L=["L21","L15"],
         search=["clearinghouse", "clearing house"],
         def_zh="作為買方對賣方、賣方對買方的中央對手方，每日 mark-to-market 與催繳保證金，消除雙邊對手風險。",
         def_en="Central counterparty that interposes itself between buyer and seller, marks positions to market daily and calls margin—eliminating bilateral counterparty risk."),
    dict(en="Stock Exchange", zh="證券交易所", cat="markets", L=["L21"],
         search=["stock exchange", "exchange"],
         def_zh="集中撮合證券買賣的場所，制定上市與交易規則。從 1602 年阿姆斯特丹開始；今多為公司化、電子化。",
         def_en="Centralized venue for matching securities trades, setting listing and trading rules. From 1602 Amsterdam; now mostly corporatized and electronic."),

    # ============== INSTRUMENTS (32) ==============
    dict(en="Limited Liability Corporation", zh="有限責任公司", cat="instruments", L=["L03","L09"],
         search=["limited liability"],
         def_zh="股東損失上限為其投資額；保護個人財產不被公司債權人追索。Shiller 強調這是現代金融體系的關鍵發明。",
         def_en="Shareholders' losses are capped at their investment; personal assets are shielded from corporate creditors. Shiller calls it a foundational financial invention."),
    dict(en="Common Stock", zh="普通股", cat="instruments", L=["L09"],
         search=["common stock"],
         def_zh="代表公司剩餘求償權的權益證券：在所有債權人與優先股受償後，剩餘現金流／清算價值歸普通股股東。",
         def_en="Residual-claim equity in a corporation: after all creditors and preferred stockholders, what's left belongs to common stockholders."),
    dict(en="Preferred Stock", zh="特別股", cat="instruments", L=["L09"],
         search=["preferred stock"],
         def_zh="介於債券與普通股之間：固定股利、清算優先於普通股，但通常無投票權，且不能像債券到期。",
         def_en="Between bonds and common stock: fixed dividend, priority over common in liquidation, but typically no voting and no maturity."),
    dict(en="Dividend", zh="股利", cat="instruments", L=["L09"],
         search=["dividend"],
         def_zh="公司從稅後盈餘配發給股東的現金或股票；Shiller 在 L7 強調股價長期應由折現股利現值決定，但實證上波動遠超此值。",
         def_en="Cash or stock paid out from after-tax profit to shareholders; Shiller showed in L7 that stock prices fluctuate far more than discounted future dividends justify."),
    dict(en="Stock Buyback", zh="股票回購", cat="instruments", L=["L09"],
         search=["share repurchase", "stock buyback", "buyback", "repurchase"],
         def_zh="公司在公開市場買回自家股票，等同於向股東配發稅務上更有利的現金，並推升 EPS。",
         def_en="Company repurchases its own shares in the market—equivalent to a tax-efficient cash distribution that boosts EPS."),
    dict(en="Subprime Mortgage", zh="次級房貸", cat="instruments", L=["L10","L13"],
         search=["subprime", "subprime mortgage"],
         def_zh="放款給信用記錄不佳借款人的房貸，違約率高於主流市場。2003-07 過度發放是 2008 危機的核心。",
         def_en="Mortgages to borrowers with weak credit histories; the over-extension of subprime in 2003-07 was at the heart of the 2008 crisis."),
    dict(en="IPO (Initial Public Offering)", zh="首次公開發行", cat="instruments", L=["L09","L19"],
         search=["ipo", "initial public offering", "going public"],
         def_zh="私人公司首次向公眾出售股票並上市；投資銀行承銷並設定發行價。",
         def_en="A private company's first public sale of stock, underwritten by investment banks who set the offer price."),
    dict(en="Present Value", zh="現值", cat="instruments", L=["L08"],
         search=["present value", "discount"],
         def_zh="未來現金流按折現率折算到當下的價值：PV = Σ Cₜ/(1+r)^t。金融估值的最基本工具。",
         def_en="Future cash flows discounted back to today at rate r: PV = Σ Cₜ/(1+r)^t. The most fundamental valuation tool."),
    dict(en="Bond", zh="債券", cat="instruments", L=["L08"],
         search=["bond", "bonds"],
         def_zh="發行人承諾在期間內支付票息、到期還本的固定收益契約。價格與利率反向變動。",
         def_en="Fixed-income contract: issuer pays periodic coupons and principal at maturity. Prices move inversely to yields."),
    dict(en="Coupon Rate", zh="票面利率", cat="instruments", L=["L08"],
         search=["coupon rate", "coupon"],
         def_zh="債券每年支付給持有人的利息佔面額的比率；發行時固定，與市場利率無關。",
         def_en="Annual interest paid relative to face value; fixed at issuance, independent of subsequent market rates."),
    dict(en="Yield to Maturity (YTM)", zh="到期殖利率", cat="instruments", L=["L08"],
         search=["yield to maturity", "ytm"],
         def_zh="持有至到期可獲得的內含報酬率，使所有未來現金流的現值等於目前價格的折現率。",
         def_en="The internal rate of return on a bond held to maturity—the discount rate equating present value of future cash flows to current price."),
    dict(en="Term Structure of Interest Rates", zh="利率期限結構", cat="instruments", L=["L08"],
         search=["term structure", "yield curve"],
         def_zh="不同到期日債券殖利率的關係，繪成「殖利率曲線」；正斜率為常態，倒掛常被視為衰退預兆。",
         def_en="The relationship between yields and maturities, drawn as the yield curve; an inverted curve has often preceded recessions."),
    dict(en="Forward Rate", zh="遠期利率", cat="instruments", L=["L08"],
         search=["forward rate"],
         def_zh="從現有利率期限結構推算的未來一段期間之隱含利率：例如「兩年後的一年期利率」。",
         def_en="Future-period interest rate implied by today's yield curve, e.g., the one-year rate two years from now."),
    dict(en="Usury", zh="高利貸", cat="instruments", L=["L08"],
         search=["usury", "usurious"],
         def_zh="放款收取「過高」利息；古代多宗教均禁止有息借貸，現代多以法定上限取代全面禁止。",
         def_en="Charging 'excessive' interest on loans; nearly all ancient religions banned interest outright—modern law uses caps instead of bans."),
    dict(en="Mortgage", zh="不動產抵押貸款", cat="instruments", L=["L10"],
         search=["mortgage"],
         def_zh="以不動產為抵押的長期貸款；現代美國標準是 30 年固定利率、分期攤還，但這在 1930 年代前並不存在。",
         def_en="Long-term loan secured by real estate; the modern U.S. 30-year fixed amortizing mortgage didn't exist before the 1930s."),
    dict(en="Adjustable-Rate Mortgage (ARM)", zh="浮動利率房貸", cat="instruments", L=["L10"],
         search=["adjustable rate", "adjustable-rate", "arm "],
         def_zh="利率隨基準指數定期調整的房貸；多有初期低利率「誘餌期」，2007 危機前在美國被推銷給次級借款人。",
         def_en="Mortgage whose rate resets periodically to an index; often with a low teaser period—heavily marketed to subprime borrowers pre-2007."),
    dict(en="Mortgage-Backed Securities (MBS)", zh="不動產抵押證券", cat="instruments", L=["L10","L13"],
         search=["mortgage-backed", "mortgage backed", "agency mbs", "mortgage securitization"],
         def_zh="把眾多房貸打包後分券賣給投資人；Fannie Mae、Freddie Mac、Ginnie Mae 主導的政府背景 MBS 為大宗，民間 MBS 在 2007 崩盤。",
         def_en="Pools of mortgages sliced and sold as securities; agency MBS (Fannie/Freddie/Ginnie) dominate, while private-label MBS collapsed in 2007."),
    dict(en="Fannie Mae & Freddie Mac", zh="房利美與房地美", cat="instruments", L=["L10"],
         search=["Fannie Mae", "Freddie Mac", "fannie"],
         def_zh="美國兩大政府支持企業（GSE），收購並擔保房貸後打包為 MBS 出售。2008 危機被聯邦接管至今。",
         def_en="Two U.S. government-sponsored enterprises (GSEs) that purchase and guarantee mortgages, packaging them into MBS; placed under federal conservatorship in 2008."),
    dict(en="Hartford Courant 1778 Mortgage Ad", zh="1778 年《Hartford Courant》房貸廣告", cat="instruments", L=["L10"],
         search=["hartford courant", "1778"],
         def_zh="Shiller 在 L10 引用的歷史文物：1778 年康乃狄克報紙的房屋抵押貸款廣告，說明現代不動產金融的長遠根源。",
         def_en="A historical artifact Shiller cites in L10: a 1778 Connecticut newspaper ad for a mortgage loan, illustrating real estate finance's long roots."),
    dict(en="Collateralized Debt Obligation (CDO)", zh="擔保債權憑證", cat="instruments", L=["L10"],
         search=["collateralized debt obligation", "cdo"],
         def_zh="把 MBS／公司債等再打包並切成不同信用層級（tranches）的證券；高層級信評極佳但 2008 大量違約。",
         def_en="Re-pooling of MBS/corporate debt into tranches with different credit ratings; senior tranches were AAA-rated but defaulted en masse in 2008."),
    dict(en="REITs (Real Estate Investment Trusts)", zh="不動產投資信託", cat="instruments", L=["L10"],
         search=["reit", "real estate investment trust"],
         def_zh="1960 年美國立法創立的證券化不動產載體：必須將 90%+ 利潤分派為股利、即可免企業稅，讓散戶能買「房地產股票」。",
         def_en="A securitized real estate vehicle created by 1960 U.S. law: distribute 90%+ of profits as dividends to avoid corporate tax, putting real estate within reach of retail investors."),
    dict(en="Forward Contract", zh="遠期契約", cat="instruments", L=["L15"],
         search=["forward contract"],
         def_zh="雙方私下約定未來某日以今日商定價格買賣資產的客製化契約；無交易所、無保證金。",
         def_en="A bilateral, customized agreement to buy/sell an asset at a future date at a price agreed today—no exchange, no margin."),
    dict(en="Futures Contract", zh="期貨契約", cat="instruments", L=["L15"],
         search=["futures contract", "futures market"],
         def_zh="標準化、在交易所交易的遠期契約：每日 mark-to-market、保證金、清算機構介入。1848 年芝加哥期貨交易所為起點。",
         def_en="An exchange-traded, standardized forward contract with daily mark-to-market, margin, and a clearinghouse—origin: 1848 Chicago Board of Trade."),
    dict(en="Margin", zh="保證金", cat="instruments", L=["L15","L21"],
         search=["margin", "maintenance margin"],
         def_zh="持有衍生品或槓桿部位時必須在帳戶中保留的擔保金額；初始保證金開倉、維持保證金維護倉位。",
         def_en="Collateral that must be posted to hold a derivatives or leveraged position; initial margin to open, maintenance margin to sustain."),
    dict(en="Contango & Backwardation", zh="正價差與逆價差", cat="instruments", L=["L15"],
         search=["contango", "backwardation"],
         def_zh="Contango：期貨價高於現貨（常因儲存成本）；Backwardation：期貨價低於現貨（常因稀缺或便利收益）。",
         def_en="Contango: futures price above spot (often from storage cost). Backwardation: futures below spot (often from scarcity / convenience yield)."),
    dict(en="Call Option", zh="買權", cat="instruments", L=["L17"],
         search=["call option"],
         def_zh="買方有權（但無義務）在到期前以履約價買入標的；買權多頭損失有限、獲利無限。",
         def_en="The right (not obligation) to buy the underlying at the strike price before expiry; limited loss, unlimited upside."),
    dict(en="Put Option", zh="賣權", cat="instruments", L=["L17"],
         search=["put option"],
         def_zh="買方有權（但無義務）在到期前以履約價賣出標的；常被用作避險／保險。",
         def_en="The right (not obligation) to sell the underlying at the strike price before expiry; commonly used as portfolio insurance."),
    dict(en="Put-Call Parity", zh="買賣權平價", cat="instruments", L=["L17"],
         search=["put-call parity", "put call parity"],
         def_zh="C − P = S − PV(K)。無套利條件；以買權＋無風險債券可複製賣權＋標的的組合，反之亦然。",
         def_en="C − P = S − PV(K). The no-arbitrage relation that ties the four instruments together."),
    dict(en="Black-Scholes Formula", zh="Black-Scholes 公式", cat="instruments", L=["L17"],
         search=["black-scholes", "black scholes"],
         def_zh="假設標的價格服從對數常態、可連續避險時的選擇權封閉解定價公式（1973）。革命性，但其假設在危機時崩潰。",
         def_en="Closed-form option pricing formula (1973) assuming lognormal prices and continuous hedging. Revolutionary, but assumptions break in crises."),
    dict(en="Binomial Asset Pricing Model", zh="二項式資產定價模型", cat="instruments", L=["L17"],
         search=["binomial", "binomial model"],
         def_zh="把資產價格演化離散成「上漲／下跌」節點樹的選擇權定價方法；Cox-Ross-Rubinstein (1979)。直覺好、可處理早提權選擇權。",
         def_en="Discrete-time tree of up/down moves for option pricing (Cox-Ross-Rubinstein 1979); intuitive and handles early-exercise options."),
    dict(en="Implied Volatility", zh="隱含波動率", cat="instruments", L=["L17"],
         search=["implied volatility"],
         def_zh="由現行選擇權市價反推 Black-Scholes 的波動率參數；反映市場對未來波動的「預期」。",
         def_en="The volatility implied by current option prices via Black-Scholes—the market's forward-looking volatility estimate."),
    dict(en="VIX Index", zh="VIX 指數", cat="instruments", L=["L17"],
         search=["vix"],
         def_zh="CBOE 編製的 30 天 S&P 500 選擇權隱含波動率指數；俗稱「恐慌指數」。",
         def_en="CBOE's 30-day implied volatility index on S&P 500 options—the 'fear gauge'."),
    dict(en="Swap Contract", zh="交換契約", cat="instruments", L=["L03"],
         search=["swap", "swaps"],
         def_zh="雙方約定在未來一段時間互換現金流（如固定 vs. 浮動利率）；最常見為利率交換。Shiller 視之為 20 世紀重要金融發明之一。",
         def_en="Two parties agree to exchange cash flows over time (e.g., fixed for floating interest); the interest rate swap is the most common. Shiller treats it as a major 20th-century financial invention."),
    dict(en="Securitization", zh="證券化", cat="instruments", L=["L10"],
         search=["securitization", "securitize"],
         def_zh="把貸款（如房貸）打包後將現金流切成分券出售；分散風險也可能隱藏風險，2007-08 危機核心。",
         def_en="Pooling loans and selling tranches of the cash flows as securities; can spread or hide risk—central to the 2007-08 crisis."),
    dict(en="Inflation Indexation", zh="通膨指數化", cat="instruments", L=["L03"],
         search=["indexation", "inflation-indexed", "tips"],
         def_zh="契約金額隨物價指數調整以保持實質購買力；美國 TIPS、英國 ILG 為代表。Shiller 視之為金融的重要發明。",
         def_en="Contractual amounts adjusted to a price index to preserve real value; U.S. TIPS and UK ILGs are flagship examples. Shiller cites this as a key financial invention."),
    dict(en="Hedge Fund", zh="避險基金", cat="instruments", L=["L12","L20"],
         search=["hedge fund"],
         def_zh="僅向合格投資人募集、受監管較鬆、可使用槓桿與賣空、收取績效費（如 2/20）的私募投資基金。",
         def_en="Lightly regulated private funds open only to accredited investors, charging performance fees (e.g., 2/20), allowed to use leverage and short-sell."),
    dict(en="Mutual Fund", zh="共同基金", cat="instruments", L=["L20"],
         search=["mutual fund"],
         def_zh="公開募集、每日報價、依規範分散持股的集合投資工具；按 Investment Company Act 1940 在美國設立。",
         def_en="Publicly offered, daily-priced, regulated pooled investment vehicle—established under the 1940 Investment Company Act in the U.S."),
    dict(en="United East India Company", zh="荷蘭東印度公司", cat="instruments", L=["L04"],
         search=["united east india", "east india company", "amsterdam stock exchange"],
         def_zh="1602 年成立的荷蘭東印度公司是第一家發行可轉讓股票的公司，催生阿姆斯特丹證交所——現代股份制公司的起源。",
         def_en="Founded 1602, the VOC was the first company to issue tradable shares, giving rise to the Amsterdam Stock Exchange—the origin of the modern joint-stock corporation."),
    dict(en="Pension Fund", zh="退休金基金", cat="instruments", L=["L20"],
         search=["pension fund", "pension plan"],
         def_zh="為退休給付而設立的長期投資基金，分為確定給付（DB）與確定提撥（DC）兩種制度。",
         def_en="Long-horizon fund for retirement benefits, split into Defined Benefit (DB) and Defined Contribution (DC) plans."),
    dict(en="Defined Benefit vs. Defined Contribution", zh="DB 與 DC 退休制", cat="instruments", L=["L20"],
         search=["defined benefit", "defined contribution"],
         def_zh="DB：雇主承諾固定退休金額、承擔投資風險；DC（如 401(k)）：雇主按薪資提撥、員工自擔投資結果。美國正大規模從 DB 轉 DC。",
         def_en="DB: employer promises a fixed benefit and bears investment risk. DC (e.g., 401(k)): employer contributes a percentage of salary; employee bears outcomes. U.S. is shifting massively from DB to DC."),
    dict(en="Trust", zh="信託", cat="instruments", L=["L20"],
         search=["trust", "trustee"],
         def_zh="財產所有人（settlor）把財產交由受託人（trustee）為受益人（beneficiary）管理；常用於遺產規劃。",
         def_en="A legal arrangement in which a settlor transfers assets to a trustee to manage for beneficiaries—core of estate planning."),
    dict(en="Family Office", zh="家族辦公室", cat="instruments", L=["L20"],
         search=["family office"],
         def_zh="服務單一或少數家族的私人投資與行政機構；資產配置、信託、稅務、慈善全包，門檻通常上億美元。",
         def_en="Private investment and admin firm serving one or a few wealthy families—asset allocation, trusts, tax, philanthropy; usually $100M+ entry."),
    dict(en="Endowment", zh="捐贈基金", cat="instruments", L=["L20","L06"],
         search=["endowment"],
         def_zh="非營利機構（多為大學）的永久投資基金，提取年度支出但保留實質本金，使支持得以永續。",
         def_en="A permanent investment fund (often for a university) from which only a portion is spent annually, preserving real principal in perpetuity."),
    dict(en="Yale Model", zh="耶魯模式", cat="instruments", L=["L06"],
         search=["yale model", "swensen"],
         def_zh="David Swensen 主持 Yale 捐贈基金期間發展的配置框架：大量配置另類資產（PE、避險基金、不動產），減少股債傳統部位。",
         def_en="Allocation framework developed by David Swensen at Yale's endowment: heavy weighting toward alternatives (PE, hedge funds, real assets), lighter on traditional stocks/bonds."),
    dict(en="Municipal Bond", zh="市政債", cat="instruments", L=["L22"],
         search=["municipal bond", "muni"],
         def_zh="州、市、地方政府發行的債券；在美國其利息常為聯邦所得稅免稅，故殖利率較公司債低。",
         def_en="Bonds issued by U.S. state, city, or local governments; interest is typically exempt from federal income tax, lowering effective yields."),
    dict(en="Social Security / OASDI", zh="社會安全保險／OASDI", cat="instruments", L=["L22"],
         search=["social security", "oasdi"],
         def_zh="美國 1935 年立法的聯邦社會保險：以薪資稅資助老年（OA）、遺屬（S）與失能（DI）給付。",
         def_en="U.S. federal social insurance established in 1935: payroll-tax-funded benefits for Old Age (OA), Survivors (S), and Disability Insurance (DI)."),

    # ============== POLICY (18) ==============
    dict(en="Leverage Cycle (Geanakoplos)", zh="槓桿循環（Geanakoplos）", cat="policy", L=["L01","L08"],
         search=["leverage cycle", "geanakoplos"],
         def_zh="John Geanakoplos 提出：抵押要求（槓桿上限）隨景氣同向升降，放大泡沫與崩盤。2007-08 危機核心機制之一。",
         def_en="John Geanakoplos's theory: collateral requirements rise and fall procyclically, amplifying booms and busts—a core 2007-08 mechanism."),
    dict(en="John Geanakoplos", zh="John Geanakoplos（金融學者）", cat="policy", L=["L01","L19"],
         search=["geanakoplos"],
         def_zh="Yale 數理金融學者、Ellington Capital 研究主管。在 Yale 同時教 ECON 251 Financial Theory，與 Shiller 課程互補（理論／實務）。",
         def_en="Yale mathematical economist and Ellington Capital research director; teaches the companion ECON 251 Financial Theory at Yale, complementing Shiller's course."),
    dict(en="Democratization of Finance", zh="金融的民主化", cat="policy", L=["L23","L01"],
         search=["democratization of finance", "democratized"],
         def_zh="Shiller 標誌性主張：讓所有人（不只富人）都能享用先進金融工具的好處——保險、避險、分散投資。",
         def_en="Shiller's signature thesis: extending sophisticated financial tools (insurance, hedging, diversification) to everyone, not just the wealthy."),
    dict(en="Securities and Exchange Commission (SEC)", zh="美國證券交易委員會", cat="policy", L=["L12"],
         search=["securities and exchange commission", "sec "],
         def_zh="1934 年依《證券交易法》成立的美國聯邦證券監管機構；要求公開揭露、打擊內線交易與操縱。",
         def_en="U.S. federal securities regulator created by the 1934 Securities Exchange Act—mandates disclosure, polices insider trading and manipulation."),
    dict(en="Self-Regulatory Organization (SRO)", zh="自律組織", cat="policy", L=["L12"],
         search=["self-regulatory", "self regulation"],
         def_zh="非政府的同業自律機構，制定並執行行業規則；FINRA（前 NASD）為代表。",
         def_en="Non-governmental industry body that writes and enforces rules for its members; FINRA (formerly NASD) is the canonical example."),
    dict(en="Insider Trading", zh="內線交易", cat="policy", L=["L12"],
         search=["insider trading"],
         def_zh="以非公開重大資訊買賣證券；在美國依 SEC 規則 10b-5 與後續法案違法。",
         def_en="Trading on material non-public information; illegal in the U.S. under SEC Rule 10b-5 and subsequent statutes."),
    dict(en="Market Manipulation", zh="市場操縱", cat="policy", L=["L12"],
         search=["manipulation", "manipulate"],
         def_zh="以人為手段（散布假消息、誇大成交、合謀拉抬等）扭曲證券價格牟利；SEC 與交易所監控的核心違規類型。",
         def_en="Distorting securities prices by artificial means (false rumors, painted tape, collusive ramping) for gain; a core violation category policed by the SEC and exchanges."),
    dict(en="Glass-Steagall Act", zh="格拉斯—斯蒂格爾法案", cat="policy", L=["L13","L19"],
         search=["glass-steagall", "glass steagall"],
         def_zh="1933 年美國法律，分離商業銀行與投資銀行，並建立 FDIC 存款保險；1999 年 Gramm-Leach-Bliley 廢除。",
         def_en="1933 U.S. law separating commercial and investment banking and establishing FDIC deposit insurance; repealed by Gramm-Leach-Bliley in 1999."),
    dict(en="Dodd-Frank Act", zh="陶德—法蘭克法案", cat="policy", L=["L13","L19"],
         search=["dodd-frank", "dodd frank"],
         def_zh="2010 年美國金融改革法案，回應 2008 危機：成立 CFPB、Volcker Rule、SIFIs、清算 OTC 衍生品等。",
         def_en="2010 U.S. financial reform law responding to the 2008 crisis: created the CFPB, Volcker Rule, SIFI designation, OTC derivatives clearing."),
    dict(en="Sarbanes-Oxley Act", zh="沙賓法案", cat="policy", L=["L16","L12"],
         search=["sarbanes-oxley", "sarbanes oxley", "sox"],
         def_zh="2002 年回應 Enron/WorldCom 醜聞的美國法案：強化公司治理、內控與審計獨立性。",
         def_en="2002 U.S. law passed after Enron/WorldCom—stricter corporate governance, internal controls, and auditor independence."),
    dict(en="Consumer Financial Protection Bureau (CFPB)", zh="消費者金融保護局", cat="policy", L=["L08","L13"],
         search=["consumer financial protection", "cfpb"],
         def_zh="Elizabeth Warren 倡議、Dodd-Frank 法案下成立的聯邦機構，專責保護消費者於金融商品中的權益。",
         def_en="Federal agency created by Dodd-Frank (championed by Elizabeth Warren) to protect consumers in financial products."),
    dict(en="Volcker Rule", zh="沃爾克法則", cat="policy", L=["L19"],
         search=["volcker rule"],
         def_zh="Dodd-Frank 條款，禁止受聯邦保險的銀行從事自營交易與持有避險基金 / PE 重大部位。",
         def_en="Dodd-Frank provision barring federally insured banks from proprietary trading and significant hedge fund / PE positions."),
    dict(en="Risk-Weighted Assets", zh="風險加權資產", cat="policy", L=["L13","L18"],
         search=["risk-weighted", "risk weighted"],
         def_zh="Basel 框架中將不同資產按信用風險賦予權重（如政府公債 0%、抵押貸款 50%、企業 100%）後加總，作為資本要求的分母。",
         def_en="Under Basel, assets are weighted by credit risk (e.g., sovereign 0%, mortgage 50%, corporate 100%) and summed—the denominator of capital ratios."),
    dict(en="Bismarck Social Insurance Origin", zh="俾斯麥社會保險起源", cat="policy", L=["L22"],
         search=["bismarck", "germany", "1880"],
         def_zh="德國 1881-1889 年在俾斯麥執政下立法的社會保險（健保、職災、養老）是世界首例，奠定現代福利國家基礎。",
         def_en="Germany's 1881-1889 social insurance laws (health, accident, old-age) under Bismarck were the world's first, founding the modern welfare state."),
    dict(en="Social Insurance", zh="社會保險", cat="policy", L=["L22"],
         search=["social insurance"],
         def_zh="由政府強制執行、廣覆蓋的風險共擔安排；19 世紀末德國 Bismarck 首創，現代福利國家基礎。",
         def_en="Government-mandated, broad-coverage risk pooling; pioneered by Bismarck's Germany in the late 19th century—the basis of the modern welfare state."),
    dict(en="Suffolk System", zh="Suffolk 體系", cat="policy", L=["L18"],
         search=["suffolk system", "suffolk"],
         def_zh="1820 年代波士頓 Suffolk Bank 為清算新英格蘭各家銀行紙幣而建的私營清算機制；Shiller 視之為早期央行體系雛形。",
         def_en="A private clearing arrangement run by Boston's Suffolk Bank from the 1820s to clear notes of New England's banks; Shiller treats it as a proto-central-bank."),
    dict(en="Too Big To Fail", zh="大到不能倒", cat="policy", L=["L12","L14"],
         search=["too big to fail", "tbtf"],
         def_zh="若某機構倒閉將威脅整個體系，政府傾向救援；製造道德風險。Dodd-Frank 要 SIFIs 制定「生前遺囑」清算方案來緩解。",
         def_en="When an institution's failure would threaten the whole system, governments tend to bail it out—creating moral hazard. Dodd-Frank requires 'living wills' from SIFIs to mitigate this."),
    dict(en="Finding Purpose in Finance", zh="在金融中找尋使命", cat="policy", L=["L23","L01"],
         search=["purpose", "good society"],
         def_zh="Shiller《Finance and the Good Society》核心：金融是把事情做成的技術，從業者該服務於更大的目的而非僅追求個人致富。",
         def_en="Core of Shiller's Finance and the Good Society: finance is a technology for getting things done; practitioners should serve a larger purpose, not just personal enrichment."),
]

assert len({(t['en'], t['zh']) for t in TERMS}) == len(TERMS), "duplicate terms"
print(f"Total terms: {len(TERMS)}")

# Extract quotes
output_terms = []
missing_quotes = 0
for t in TERMS:
    quote, src = find_quote(t["L"], t["search"])
    if not quote:
        # fallback: search any speaker (guest lectures)
        quote, src = find_quote(t["L"], t["search"], shiller_only=False)
    if not quote:
        missing_quotes += 1
    output_terms.append({
        "term_en": t["en"],
        "term_zh": t["zh"],
        "category": t["cat"],
        "def_zh": t["def_zh"],
        "def_en": t["def_en"],
        "sources": t["L"],
        "shiller_quote": quote,
        "quote_source": src,
    })

print(f"Quotes found: {len(TERMS) - missing_quotes}/{len(TERMS)}; missing: {missing_quotes}")
for t in output_terms:
    if not t["shiller_quote"]:
        print(f"  MISSING: {t['term_en']} (lectures {t['sources']})")

out = {
    "_note": "Shiller《金融市場》(ECON 252, 2011) 100 個核心名詞；每條附定義與從原始逐字稿擷取的真實引用段落。",
    "_total": len(output_terms),
    "categories": CATEGORIES,
    "terms": output_terms,
}

(ROOT / "data" / "glossary.json").write_text(
    json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8"
)
print(f"Wrote {ROOT / 'data' / 'glossary.json'}")
