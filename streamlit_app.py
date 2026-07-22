from __future__ import annotations

import math
import re
from datetime import datetime, timezone
from typing import Any

import numpy as np
import pandas as pd
import requests
import streamlit as st
import yfinance as yf
from bs4 import BeautifulSoup

st.set_page_config(page_title="Market Lens｜市場透視", page_icon="◉", layout="wide")

st.markdown(
    """
    <style>
      .block-container {padding-top: 1.2rem; padding-bottom: 3rem;}
      .card {border:1px solid rgba(128,128,128,.25);border-radius:14px;padding:14px 16px;background:rgba(128,128,128,.04);min-height:110px}
      .source {border-left:4px solid rgba(128,128,128,.45);padding:8px 12px;margin:8px 0;background:rgba(128,128,128,.04)}
      .pos {color:#27a55b;font-weight:650}.neg {color:#e05b67;font-weight:650}.neu {color:#d0aa35;font-weight:650}
    </style>
    """,
    unsafe_allow_html=True,
)

MARKETS = {
    "^GSPC": "S&P 500", "^IXIC": "Nasdaq", "^SOX": "Semiconductors",
    "^VIX": "VIX", "^TNX": "US 10Y yield", "DX-Y.NYB": "US Dollar Index",
    "GBPUSD=X": "GBP/USD", "CL=F": "WTI oil", "NG=F": "US natural gas", "GC=F": "Gold",
}
WATCHLIST = {
    "APLD": "Applied Digital", "MU": "Micron", "NBIS": "Nebius",
    "BE": "Bloom Energy", "TE": "T1 Energy", "GOOGL": "Alphabet", "MSFT": "Microsoft",
}
FRED = {
    "DFF": "Fed effective rate", "DGS2": "US 2Y Treasury", "DGS10": "US 10Y Treasury",
    "T10Y2": "10Y–2Y curve", "DFII10": "US 10Y real yield",
    "BAMLH0A0HYM2": "US high-yield spread", "CPIAUCSL": "US CPI",
    "PCEPILFE": "US core PCE", "UNRATE": "US unemployment",
}

TOPICS = {
    "Central bank policy": [
        "央行透過政策利率、資產負債表和流動性工具影響借貸成本、通脹與金融條件。",
        "政策聲明、投票分歧、通脹預測、工資、失業率、金融穩定風險。",
        "偏鷹 → 短端利率上升 → 美元通常轉強 → 成長股估值受壓。",
        "只看加息或減息，忽略市場事前已定價多少。",
    ],
    "Yield curve": [
        "不同期限國債收益率的排列。2年期較敏感於政策，10年期較反映長期增長、通脹與期限溢價。",
        "2Y、10Y、10Y–2Y、實質利率、期限溢價。",
        "長端收益率上升 → 折現率提高 → 遠期盈利型資產通常承壓。",
        "把所有收益率上升都視為同一件事。",
    ],
    "FX": [
        "匯率反映兩地利差、增長差、避險需求、貿易與資本流動。",
        "利率預期、央行分歧、經常帳、商品價格、政治風險。",
        "美元上升 → 英鎊投資者的美元資產換算回報可能增加。",
        "只看股票美元回報，忽略本幣回報。",
    ],
    "Credit spreads": [
        "企業債收益率相對國債的額外補償，反映違約與流動性風險。",
        "高收益債利差、投資級利差、銀行貸款標準、再融資牆。",
        "利差擴大 → 融資成本上升 → 高負債、高CapEx公司受壓。",
        "只看無風險利率，忽略信用溢價。",
    ],
    "Inflation surprise": [
        "實際通脹相對市場預期的差異，往往比同比數字本身更能驅動短期市場。",
        "核心服務、住房、工資、能源、通脹預期。",
        "高於預期 → 減息預期後移 → 收益率與美元可能上升。",
        "看到通脹下降就認為必然利好。",
    ],
    "Earnings vs cash flow": [
        "盈利按權責發生制確認；現金流顯示實際現金進出。",
        "營運現金流、CapEx、自由現金流、應收帳、股票薪酬。",
        "收入增長但CapEx更快 → FCF受壓 → 可能需要債務或股權融資。",
        "只看EPS beat，忽略盈利質量與現金消耗。",
    ],
    "CapEx cycle": [
        "企業大規模投資設備、廠房、數據中心或基礎設施的周期。",
        "訂單、交付期、利用率、供應鏈、融資、投資回報率。",
        "CapEx上升 → 上游受惠；若回報不足，後期可能削減並出現供應過剩。",
        "把今天的資本開支永久外推。",
    ],
}

SHOCKS = {
    "央行意外加息": [("短端收益率", "上升", "高"), ("美元", "通常上升", "中"), ("成長股估值", "受壓", "高"), ("高負債公司", "融資壓力上升", "高")],
    "油價急升": [("通脹預期", "上升", "高"), ("央行減息預期", "後移", "中高"), ("能源生產商", "相對受惠", "中"), ("消費者可支配收入", "受壓", "中")],
    "美元急升": [("非美貨幣", "承壓", "高"), ("美元計價商品", "通常受壓", "中"), ("英鎊投資者持有美元資產", "換算回報增加", "高"), ("新興市場美元債務", "壓力上升", "高")],
    "信用利差擴大": [("企業再融資成本", "上升", "高"), ("高收益債", "價格下跌", "高"), ("高CapEx公司", "估值和流動性受壓", "高"), ("防禦性資產", "相對受惠", "中")],
    "AI資本開支上調": [("GPU／HBM／網絡設備", "需求上升", "高"), ("數據中心電力與容量", "更緊張", "高"), ("供應商訂單", "增加", "中高"), ("大型科技FCF", "短期受壓", "中"), ("中期供應過剩風險", "亦可能上升", "中")],
    "通脹低於預期": [("減息預期", "提前", "中高"), ("短端收益率", "下降", "高"), ("美元", "可能轉弱", "中"), ("長久期成長股", "通常受惠", "中高")],
}


def safe_float(value: Any) -> float | None:
    try:
        x = float(value)
        return None if math.isnan(x) else x
    except (TypeError, ValueError):
        return None


def fmt(x: float | None, pct: bool = False) -> str:
    if x is None:
        return "—"
    return f"{x:+.2f}%" if pct else f"{x:,.2f}"


@st.cache_data(ttl=900, show_spinner=False)
def market_history(tickers: tuple[str, ...], period: str) -> pd.DataFrame:
    if not tickers:
        return pd.DataFrame()
    try:
        raw = yf.download(list(tickers), period=period, auto_adjust=True, progress=False, threads=True)
        if raw.empty:
            return pd.DataFrame()
        close = raw["Close"] if isinstance(raw.columns, pd.MultiIndex) else raw[["Close"]].rename(columns={"Close": tickers[0]})
        if isinstance(close, pd.Series):
            close = close.to_frame(name=tickers[0])
        return close.dropna(how="all")
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=900, show_spinner=False)
def snapshot(tickers: tuple[str, ...]) -> pd.DataFrame:
    hist = market_history(tickers, "1mo")
    rows = []
    for t in tickers:
        s = hist[t].dropna() if not hist.empty and t in hist.columns else pd.Series(dtype=float)
        last = float(s.iloc[-1]) if len(s) else np.nan
        d1 = (last / float(s.iloc[-2]) - 1) * 100 if len(s) >= 2 else np.nan
        d5 = (last / float(s.iloc[-6]) - 1) * 100 if len(s) >= 6 else np.nan
        rows.append({"Ticker": t, "Name": MARKETS.get(t, WATCHLIST.get(t, t)), "Last": last, "1D %": d1, "5D %": d5})
    return pd.DataFrame(rows)


@st.cache_data(ttl=3600, show_spinner=False)
def fred_series(series_id: str, key: str) -> pd.Series:
    if not key:
        return pd.Series(dtype=float)
    try:
        r = requests.get(
            "https://api.stlouisfed.org/fred/series/observations",
            params={"series_id": series_id, "api_key": key, "file_type": "json", "sort_order": "desc", "limit": 500},
            timeout=20,
        )
        r.raise_for_status()
        values = {}
        for item in r.json().get("observations", []):
            if item.get("value") not in (None, "."):
                values[pd.to_datetime(item["date"])] = float(item["value"])
        return pd.Series(values, dtype=float).sort_index()
    except Exception:
        return pd.Series(dtype=float)


@st.cache_data(ttl=3600, show_spinner=False)
def boe_rate() -> tuple[str, str]:
    url = "https://www.bankofengland.co.uk/monetary-policy/the-interest-rate-bank-rate"
    try:
        r = requests.get(url, timeout=18, headers={"User-Agent": "MarketLens educational dashboard"})
        text = BeautifulSoup(r.text, "html.parser").get_text(" ", strip=True)
        m = re.search(r"Current Bank Rate\s*([0-9]+(?:\.[0-9]+)?)\s*%", text, flags=re.I)
        return (f"{m.group(1)}%" if m else "See source", url)
    except Exception:
        return "Unavailable", url


@st.cache_data(ttl=3600, show_spinner=False)
def ecb_rate() -> tuple[str, str]:
    url = "https://www.ecb.europa.eu/stats/policy_and_exchange_rates/key_ecb_interest_rates/html/index.en.html"
    try:
        for table in pd.read_html(url):
            cols = " ".join(map(str, table.columns))
            if "Deposit facility" in cols:
                numbers = table.apply(pd.to_numeric, errors="coerce")
                vals = numbers.stack().dropna()
                if not vals.empty:
                    return f"{float(vals.iloc[-3]):.2f}%", url
        return "See source", url
    except Exception:
        return "Unavailable", url


@st.cache_data(ttl=900, show_spinner=False)
def news_search(query: str, timespan: str, maxrecords: int) -> pd.DataFrame:
    try:
        r = requests.get(
            "https://api.gdeltproject.org/api/v2/doc/doc",
            params={"query": query, "mode": "artlist", "maxrecords": maxrecords, "timespan": timespan, "sort": "datedesc", "format": "json"},
            timeout=25,
        )
        r.raise_for_status()
        rows = []
        for a in r.json().get("articles", []):
            rows.append({"Date": a.get("seendate", ""), "Title": a.get("title", "Untitled"), "Source": a.get("domain", ""), "Country": a.get("sourcecountry", ""), "URL": a.get("url", "")})
        return pd.DataFrame(rows)
    except Exception:
        return pd.DataFrame()


def classify(title: str) -> tuple[str, str, str]:
    x = title.lower()
    themes = []
    if any(k in x for k in ["federal reserve", "central bank", "interest rate", "inflation", "cpi", "pce"]): themes.append("Rates/Inflation")
    if any(k in x for k in ["dollar", "sterling", "pound", "yen", "euro", "currency", "fx"]): themes.append("FX")
    if any(k in x for k in ["oil", "gas", "energy", "brent", "wti"]): themes.append("Commodities")
    if any(k in x for k in [" ai ", "data center", "datacenter", "gpu", "semiconductor", "memory", "cloud"]): themes.append("AI/Tech CapEx")
    if any(k in x for k in ["tariff", "sanction", "war", "conflict", "export control"]): themes.append("Geopolitics/Policy")
    negative = ["hike", "war", "sanction", "slump", "downgrade", "default", "shortage"]
    positive = ["rate cut", "beats", "raises outlook", "record", "surge", "accelerates", "eases"]
    direction = "Potential risk" if any(k in x for k in negative) else "Potential support" if any(k in x for k in positive) else "Needs context"
    return ", ".join(themes) or "General markets", direction, "Medium" if direction != "Needs context" else "Low"


def brief_rows(df: pd.DataFrame) -> list[str]:
    if df.empty or df["Last"].isna().all():
        return ["Live market data is unavailable. Retry later or check network access."]
    d = df.set_index("Ticker")
    out = []
    vix = safe_float(d.loc["^VIX", "Last"]) if "^VIX" in d.index else None
    usd = safe_float(d.loc["DX-Y.NYB", "1D %"]) if "DX-Y.NYB" in d.index else None
    oil = safe_float(d.loc["CL=F", "5D %"]) if "CL=F" in d.index else None
    nas = safe_float(d.loc["^IXIC", "1D %"]) if "^IXIC" in d.index else None
    sox = safe_float(d.loc["^SOX", "1D %"]) if "^SOX" in d.index else None
    if vix is not None: out.append(f"VIX is {vix:.1f}: " + ("risk aversion is elevated." if vix >= 30 else "volatility is above calm conditions." if vix >= 20 else "volatility is relatively contained."))
    if usd is not None: out.append(f"The dollar is {'stronger' if usd > 0 else 'weaker'} by {abs(usd):.2f}% today, relevant for global liquidity and GBP-based returns.")
    if oil is not None and abs(oil) >= 3: out.append(f"WTI is {'up' if oil > 0 else 'down'} {abs(oil):.1f}% over five sessions, meaningful for inflation expectations.")
    if nas is not None and sox is not None: out.append(f"Nasdaq is {nas:+.2f}% and semiconductors are {sox:+.2f}% today; the gap separates broad tech from chip-specific sentiment.")
    return out or ["No unusually large cross-asset signal was detected."]


st.sidebar.title("Market Lens｜市場透視")
st.sidebar.caption("Macro • Central banks • FX • News • Learning")
try:
    secret_key = st.secrets.get("FRED_API_KEY", "")
except Exception:
    secret_key = ""
with st.sidebar.expander("Data settings"):
    fred_key = st.text_input("FRED API 金鑰 / API key", value=secret_key, type="password", help="Optional; enables official FRED series.")
page = st.sidebar.radio("導覽 Navigate", ["晨間簡報 Morning Brief", "宏觀儀表板 Macro Dashboard", "新聞監察 News Monitor", "學習實驗室 Learning Lab", "觀察名單 Watchlist", "研究筆記 Research Notebook"])
st.sidebar.divider()
st.sidebar.caption("教育用途，並非投資建議。重要事實請以第一手來源核實。\nEducational tool, not investment advice.")

if page == "晨間簡報 Morning Brief":
    st.title("晨間簡報 Morning Brief")
    st.caption("用跨資產視角訓練買方投資者的資訊處理習慣。 / A cross-asset briefing designed to train a buy-side information habit.")
    snap = snapshot(tuple(MARKETS))
    st.caption("Refresh attempt: " + datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"))
    idx = snap.set_index("Ticker") if not snap.empty else pd.DataFrame()
    cols = st.columns(4)
    for col, ticker in zip(cols, ["^GSPC", "^IXIC", "^VIX", "GBPUSD=X"]):
        with col:
            if not idx.empty and ticker in idx.index:
                st.metric(MARKETS[ticker], fmt(safe_float(idx.loc[ticker, "Last"])), fmt(safe_float(idx.loc[ticker, "1D %"]), True))
            else:
                st.metric(MARKETS[ticker], "—")
    st.subheader("今日市場重點 What matters today")
    for row in brief_rows(snap): st.markdown(f"- {row}")
    st.subheader("央行概覽 Central-bank snapshot")
    fed = fred_series("DFF", fred_key) if fred_key else pd.Series(dtype=float)
    br, bu = boe_rate(); er, eu = ecb_rate()
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown('<div class="card"><b>Federal Reserve</b><br><br>Effective fed funds: <b>' + (f"{fed.iloc[-1]:.2f}%" if not fed.empty else "Add FRED key") + '</b><br><span style="opacity:.7">Watch inflation surprises, labour, financial conditions and what is already priced.</span></div>', unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div class="card"><b>Bank of England</b><br><br>Bank Rate: <b>{br}</b><br><span style="opacity:.7">Watch services inflation, wages, energy and vote split.</span></div>', unsafe_allow_html=True); st.link_button("英倫銀行官方來源 Official BoE source", bu)
    with c3:
        st.markdown(f'<div class="card"><b>European Central Bank</b><br><br>Deposit rate: <b>{er}</b><br><span style="opacity:.7">Watch energy, wages, euro and fragmentation.</span></div>', unsafe_allow_html=True); st.link_button("歐洲央行官方來源 Official ECB source", eu)
    st.subheader("每日資訊紀律 Daily discipline")
    st.info("Read in this order: **price action → macro driver → primary source → exposure → what would disprove the thesis**. Do not begin with social-media commentary and search only for confirmation.")

elif page == "宏觀儀表板 Macro Dashboard":
    st.title("宏觀儀表板 Macro Dashboard")
    selected = st.multiselect("市場指標 Market series", list(MARKETS), default=["^GSPC", "^SOX", "^VIX", "^TNX", "DX-Y.NYB", "GBPUSD=X", "CL=F"], format_func=lambda x: f"{MARKETS[x]} ({x})")
    period = st.selectbox("歷史區間 History", ["1mo", "3mo", "6mo", "1y", "2y"], index=2)
    hist = market_history(tuple(selected), period)
    if hist.empty: st.warning("Live market data could not be loaded.")
    else:
        norm = hist / hist.ffill().iloc[0] * 100; norm.columns = [MARKETS.get(c, c) for c in norm.columns]
        st.line_chart(norm, height=420); st.caption("Selected series are rebased to 100.")
    st.subheader("官方宏觀數據 Official macro series")
    if not fred_key:
        st.warning("Add a free FRED API key in the sidebar."); st.code('FRED_API_KEY = "your_key_here"', language="toml")
    else:
        sid = st.selectbox("FRED 指標 / FRED series", list(FRED), format_func=lambda x: f"{FRED[x]} ({x})")
        s = fred_series(sid, fred_key)
        if s.empty: st.error("FRED data unavailable. Check the key.")
        else: st.line_chart(s.rename(FRED[sid]).to_frame(), height=350); st.metric("最新值 Latest", f"{s.iloc[-1]:,.2f}")
    st.subheader("市場環境檢查表 Regime checklist")
    st.dataframe(pd.DataFrame([
        ["Inflation", "CPI/core PCE, wages, oil", "Faster or slower than priced?"],
        ["Growth", "PMI, payrolls, retail sales", "Resilient, reaccelerating or contracting?"],
        ["Policy", "2Y yield, futures, speeches", "What path is already priced?"],
        ["Liquidity", "Dollar, credit spreads, bank standards", "Easing or tightening?"],
        ["Risk appetite", "VIX, breadth, credit, small caps", "Is the move broad and fundamental?"],
    ], columns=["Pillar", "Indicators", "Core question"]), hide_index=True, use_container_width=True)

elif page == "新聞監察 News Monitor":
    st.title("新聞監察 News Monitor")
    presets = {
        "Central banks & inflation": '(Federal Reserve OR ECB OR "Bank of England" OR inflation OR interest rates)',
        "FX & liquidity": '(dollar OR sterling OR euro OR yen OR currency OR FX)',
        "AI infrastructure": '("artificial intelligence" OR "data center" OR datacenter OR GPU OR semiconductor OR cloud)',
        "Energy & commodities": '(oil OR gas OR power OR electricity OR copper OR gold)',
        "Geopolitics & trade": '(tariff OR sanctions OR export controls OR conflict OR war OR trade)',
    }
    preset = st.selectbox("主題 Theme", list(presets)); query = st.text_input("GDELT query", presets[preset])
    a, b = st.columns(2); span = a.selectbox("回看期間 Lookback", ["12h", "1d", "3d", "1w", "2w"], index=2); maximum = b.slider("最多文章 Maximum articles", 10, 100, 30, 10)
    news = news_search(query, span, maximum)
    if news.empty: st.warning("No live articles returned. Broaden the query or retry later.")
    else:
        for _, row in news.iterrows():
            theme, direction, confidence = classify(row["Title"])
            with st.container(border=True):
                st.markdown(f"**{row['Title']}**"); st.caption(f"{row['Source']} • {row['Date']} • {row['Country']}")
                x, y, z = st.columns(3); x.write(f"**Theme:** {theme}"); y.write(f"**Initial read:** {direction}"); z.write(f"**Confidence:** {confidence}")
                if row["URL"]: st.link_button("開啟原文 Open original article", row["URL"])
        st.download_button("Download news CSV", news.to_csv(index=False).encode("utf-8"), "market_lens_news.csv", "text/csv")
    st.info("A headline is not a trade. Ask: **What changed versus expectations? Is the source primary? Which cash-flow or discount-rate channel is affected? Is it temporary or structural?**")

elif page == "學習實驗室 Learning Lab":
    st.title("學習實驗室 Learning Lab")
    tab1, tab2, tab3 = st.tabs(["概念庫 Concept library", "衝擊傳導 Shock transmission", "小測驗 Mini quiz"])
    with tab1:
        topic = st.selectbox("Concept", list(TOPICS)); definition, watch, chain, mistake = TOPICS[topic]
        st.subheader(topic); st.write(definition)
        c1, c2 = st.columns(2)
        with c1: st.markdown("**需要觀察 What to watch**"); st.write(watch); st.markdown("**典型傳導 Typical transmission**"); st.write(chain)
        with c2: st.markdown("**常見錯誤 Common mistake**"); st.warning(mistake); st.markdown("**Exercise**"); st.write("Find a primary-source release. Record consensus, actual, first market reaction, and whether it persisted after 24 hours.")
    with tab2:
        shock = st.selectbox("Shock", list(SHOCKS)); st.write("A first-pass map; real outcomes depend on valuation, positioning and what was already priced.")
        for i, (asset, direction, confidence) in enumerate(SHOCKS[shock], 1):
            css = "pos" if any(x in direction for x in ["受惠", "增加", "提前", "需求上升"]) else "neg" if any(x in direction for x in ["受壓", "下降", "壓力", "後移", "價格下跌"]) else "neu"
            st.markdown(f'<div class="source"><b>{i}. {asset}</b><br><span class="{css}">{direction}</span> · Confidence: {confidence}</div>', unsafe_allow_html=True)
        st.write("**Second-order question:** Does the shock affect only the discount rate, or also revenue, margins, funding access and competition?")
    with tab3:
        quiz = [
            ("CPI低於上月但高於市場預期，短期市場通常最重視甚麼？", ["只看按月方向", "相對市場預期的差異", "指數絕對水平"], "相對市場預期的差異", "市場交易的是新資訊相對已定價預期。"),
            ("10年期實質利率上升為何常壓制高增長股？", ["提高近期銷售", "提高遠期現金流折現率", "自動造成衰退"], "提高遠期現金流折現率", "遠期現金流的現值會下降。"),
            ("EPS超預期但FCF因CapEx急升而轉差，應調查甚麼？", ["只看EPS", "CapEx回報與融資是否可信", "自動賣出"], "CapEx回報與融資是否可信", "CapEx可創造價值，但回報需高於資金成本。"),
        ]
        for i, (q, opts, answer, exp) in enumerate(quiz):
            choice = st.radio(q, opts, key=f"q{i}", index=None)
            if choice: st.success("正確。" + exp) if choice == answer else st.error("不完全正確。" + exp)

elif page == "觀察名單 Watchlist":
    st.title("觀察名單 Watchlist")
    st.caption("Optional portfolio context; the app remains macro-first.")
    text = st.text_input("Tickers separated by commas", ", ".join(WATCHLIST))
    tickers = tuple(dict.fromkeys(x.strip().upper() for x in text.split(",") if x.strip()))
    snap = snapshot(tickers)
    if snap.empty: st.warning("No live watchlist data available.")
    else: st.dataframe(snap.style.format({"Last": "{:,.2f}", "1D %": "{:+.2f}", "5D %": "{:+.2f}"}), hide_index=True, use_container_width=True)
    exposure = pd.DataFrame([
        ["APLD", "AI data-centre real estate", "Rates, credit, construction, power, tenant credit"],
        ["MU", "Memory/HBM cycle", "AI servers, DRAM pricing, supply, margins"],
        ["NBIS", "AI cloud", "GPU supply, utilisation, CapEx, funding, customer concentration"],
        ["BE", "On-site power", "Data-centre demand, gas economics, backlog, margins"],
        ["TE", "US solar/manufacturing", "Policy, tariffs, factory execution, funding"],
        ["GOOGL", "Search/cloud/AI", "Ads, AI monetisation, cloud, CapEx returns"],
        ["MSFT", "Enterprise cloud/AI", "Azure, AI utilisation, margins, CapEx returns"],
    ], columns=["Ticker", "Primary exposure", "Key drivers"])
    st.subheader("曝險地圖 Exposure map"); st.dataframe(exposure[exposure.Ticker.isin(tickers)], hide_index=True, use_container_width=True)
    if "positions" not in st.session_state:
        st.session_state.positions = pd.DataFrame([{"Ticker": t, "Shares": 0.0, "Average cost": 0.0, "Currency": "USD", "Thesis confidence (1-5)": 3} for t in tickers])
    st.subheader("持倉紀錄 Position log"); edited = st.data_editor(st.session_state.positions, num_rows="dynamic", use_container_width=True); st.session_state.positions = edited
    st.download_button("下載持倉紀錄 / Download position log", edited.to_csv(index=False).encode("utf-8"), "market_lens_positions.csv", "text/csv")

else:
    st.title("研究筆記 Research Notebook")
    st.caption("寫下一個可以被推翻的投資論點，而不是堆砌利好。 / Write a thesis that can be disproved.")
    if "notes" not in st.session_state:
        st.session_state.notes = pd.DataFrame(columns=["Asset / theme", "Core thesis", "Catalysts", "Disconfirming evidence", "Key metric", "Review date", "Confidence (1-5)"])
    notes = st.data_editor(st.session_state.notes, num_rows="dynamic", use_container_width=True, column_config={"Review date": st.column_config.DateColumn(), "Confidence (1-5)": st.column_config.NumberColumn(min_value=1, max_value=5, step=1)})
    st.session_state.notes = notes
    st.download_button("下載研究筆記 / Download research notebook", notes.to_csv(index=False).encode("utf-8"), "market_lens_research_notebook.csv", "text/csv")
    st.subheader("投資論點模板 Thesis template")
    st.code("""Asset/theme:
Why the market may be wrong:
Mechanism from event to cash flow:
What is already priced:
Three catalysts:
Three disconfirming signals:
Valuation / position-size rule:
Next review date:
Primary sources:""", language="text")
