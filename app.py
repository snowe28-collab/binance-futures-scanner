# -*- coding: utf-8 -*-
import time
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st

st.set_page_config(
    page_title="Binance Futures Scanner",
    page_icon="📊",
    layout="wide",
)

st.markdown("""
<style>
[data-testid="stAppViewContainer"] {direction:rtl;}
[data-testid="stMarkdownContainer"] {text-align:right;}
.block-container {padding:1rem;max-width:1500px;}
h1 {font-size:1.7rem!important;}
[data-testid="stDataFrame"] {direction:ltr;}
</style>
""", unsafe_allow_html=True)

BASE = "https://fapi.binance.com"


class StopScan(Exception):
    pass


def api(path, **params):
    try:
        response = requests.get(
            BASE + path, params=params, timeout=20
        )
    except requests.RequestException as exc:
        raise RuntimeError("تعذر الاتصال ببايننس") from exc

    if response.status_code in (403, 451):
        raise StopScan(
            "بايننس رفضت اتصال خادم الاستضافة. "
            "قد يكون الوصول مقيدًا من موقع الخادم. "
            "لم يتم استبدال البيانات ببيانات وهمية."
        )
    if response.status_code in (418, 429):
        raise StopScan(
            "تم بلوغ حد طلبات بايننس. "
            "توقف الفحص؛ انتظر قبل إعادة المحاولة."
        )
    response.raise_for_status()
    data = response.json()
    if isinstance(data, dict) and data.get("code", 0) < 0:
        raise RuntimeError(str(data.get("msg", "خطأ من بايننس")))
    return data


@st.cache_data(ttl=1800, show_spinner=False)
def universe():
    data = api("/fapi/v1/exchangeInfo")
    return [
        x["symbol"] for x in data["symbols"]
        if x.get("quoteAsset") == "USDT"
        and x.get("contractType") == "PERPETUAL"
        and x.get("status") == "TRADING"
    ]


@st.cache_data(ttl=300, show_spinner=False)
def candles(symbol, interval):
    rows = api(
        "/fapi/v1/klines",
        symbol=symbol,
        interval=interval,
        limit=499,
    )
    columns = [
        "time", "open", "high", "low", "close", "volume",
        "end", "quote_volume", "trades", "buy_volume",
        "buy_quote_volume", "ignore",
    ]
    d = pd.DataFrame(rows, columns=columns)
    for col in columns:
        d[col] = pd.to_numeric(d[col], errors="coerce")
    now_ms = int(time.time() * 1000)
    d = d[d["end"] < now_ms].copy()
    d = d.dropna(subset=["open", "high", "low", "close"])
    d = d.sort_values("time").drop_duplicates("time")
    if len(d) < 210:
        raise ValueError("تاريخ غير كافٍ: نحتاج 210 شموع مغلقة")
    durations = {"4h": 14400000, "1d": 86400000}
    duration = durations[interval]
    if now_ms - d["end"].iloc[-1] > duration * 1.25:
        raise ValueError("الشموع قديمة")
    if (d["time"].diff().dropna() != duration).any():
        raise ValueError("توجد فجوات في الشموع")
    d["date"] = pd.to_datetime(d["time"], unit="ms", utc=True)
    return d.reset_index(drop=True)


def indicators(d):
    d = d.copy()
    c = d["close"]
    for n in (20, 50, 200):
        d[f"ema{n}"] = c.ewm(span=n, adjust=False).mean()

    change = c.diff()
    gain = change.clip(lower=0).ewm(
        alpha=1 / 14, adjust=False, min_periods=14
    ).mean()
    loss = (-change.clip(upper=0)).ewm(
        alpha=1 / 14, adjust=False, min_periods=14
    ).mean()
    d["rsi"] = 100 - 100 / (1 + gain / loss.replace(0, np.nan))
    d.loc[(loss == 0) & (gain > 0), "rsi"] = 100
    d.loc[(loss == 0) & (gain == 0), "rsi"] = 50

    previous = c.shift()
    tr = pd.concat([
        d["high"] - d["low"],
        (d["high"] - previous).abs(),
        (d["low"] - previous).abs(),
    ], axis=1).max(axis=1)
    d["atr"] = tr.ewm(
        alpha=1 / 14, adjust=False, min_periods=14
    ).mean()

    macd = c.ewm(span=12, adjust=False).mean()
    macd -= c.ewm(span=26, adjust=False).mean()
    d["hist"] = macd - macd.ewm(span=9, adjust=False).mean()
    d["momentum"] = c.pct_change(18) * 100
    baseline = d["volume"].shift().rolling(20).mean()
    d["volume_ratio"] = d["volume"] / baseline.replace(0, np.nan)
    return d


def direction_score(h, daily, side):
    score = 0
    reasons = []

    tests = [
        (side * (h["close"] - h["ema20"]) > 0, 20,
         "السعر والمتوسط القصير متوافقان"),
        (side * (h["ema20"] - h["ema50"]) > 0, 20,
         "اتجاه 4 ساعات داعم"),
        (side * (daily["close"] - daily["ema50"]) > 0, 20,
         "الاتجاه اليومي داعم"),
        (side * h["hist"] > 0, 15,
         "زخم MACD داعم"),
        (side * h["momentum"] > 0, 15,
         "زخم آخر 3 أيام داعم"),
        (
            48 <= h["rsi"] <= 70 if side == 1
            else 30 <= h["rsi"] <= 52,
            10, "RSI مناسب للاتجاه",
        ),
    ]
    for passed, points, reason in tests:
        if passed:
            score += points
            reasons.append(reason)
    return score, reasons


def historical_comparison(d, side):
    """مقارنة وصفية بحالات سابقة، وليست اختبار صفقات."""
    features = pd.DataFrame({
        "rsi": (d["rsi"] - 50) / 20,
        "distance": (
            (d["close"] - d["ema20"]) / d["atr"]
        ).clip(-6, 6),
        "trend": (
            (d["ema20"] - d["ema50"]) / d["atr"]
        ).clip(-6, 6),
        "momentum": (
            d["close"].pct_change(18) * d["close"] / d["atr"]
        ).clip(-10, 10),
    })
    current = features.iloc[-1]
    candidates = features.iloc[200:len(d) - 42].dropna()
    if candidates.empty or current.isna().any():
        return pd.DataFrame()

    distances = ((candidates - current) ** 2).mean(axis=1)
    chosen = []
    for index in distances.sort_values().index:
        if all(abs(index - old) >= 42 for old in chosen):
            chosen.append(index)
        if len(chosen) == 20:
            break

    rows = []
    for days in (3, 5, 7):
        horizon = days * 6
        returns = np.array([
            side * (
                d["close"].iloc[i + horizon] /
                d["close"].iloc[i] - 1
            ) * 100
            for i in chosen
        ])
        enough = len(returns) >= 8
        rows.append({
            "الأفق": f"{days} أيام",
            "العينات": len(returns),
            "حالات في صالح الاتجاه %": (
                float((returns > 0).mean() * 100)
                if enough else np.nan
            ),
            "وسيط الحركة لصالح الاتجاه %": (
                float(np.median(returns)) if enough else np.nan
            ),
            "الحالة": "مقارنة وصفية" if enough else "عينات قليلة",
        })
    return pd.DataFrame(rows)


def analyze(symbol, ticker, funding, threshold):
    h = indicators(candles(symbol, "4h"))
    daily = indicators(candles(symbol, "1d"))
    last, day = h.iloc[-1], daily.iloc[-1]

    long_score, long_reasons = direction_score(last, day, 1)
    short_score, short_reasons = direction_score(last, day, -1)
    side = 1 if long_score >= short_score else -1
    score = max(long_score, short_score)
    reasons = long_reasons if side == 1 else short_reasons

    price = float(ticker["lastPrice"])
    atr_value = float(last["atr"])
    if not np.isfinite(price) or price <= 0:
        raise ValueError("سعر غير صالح")
    if not np.isfinite(atr_value) or atr_value <= 0:
        raise ValueError("ATR غير صالح")

    support = float(h["low"].tail(30).min())
    resistance = float(h["high"].tail(30).max())
    if side == 1:
        stop = min(support - 0.3 * atr_value, price - 1.8 * atr_value)
    else:
        stop = max(
            resistance + 0.3 * atr_value, price + 1.8 * atr_value
        )
    risk = abs(price - stop)
    targets = [price + side * risk * r for r in (1.5, 2, 3)]

    obstacles = []
    if score < threshold:
        obstacles.append("درجة الاتجاه أقل من الحد المختار")
    if abs(price - last["ema20"]) > 3 * atr_value:
        obstacles.append("السعر ممتد عن المتوسط؛ انتظار تصحيح")
    if abs(price - last["close"]) > 1.5 * atr_value:
        obstacles.append("حركة كبيرة منذ آخر شمعة مغلقة")
    if risk / price > 0.15:
        obstacles.append("مسافة الوقف تتجاوز 15%")
    if stop <= 0 or min(targets) <= 0:
        obstacles.append("المستويات غير مناسبة")

    signal = ("شراء Long" if side == 1 else "بيع Short")
    if obstacles:
        signal = "مراقبة"

    # لا نعرض خطة دخول فعالة للصفوف التي لم تستوفِ الشروط.
    active = not obstacles
    rate = float(funding.get("lastFundingRate", np.nan))
    row = {
        "العملة": symbol,
        "القرار": signal,
        "الميل": "صاعد" if side == 1 else "هابط",
        "درجة الاتجاه": score,
        "السعر عند الفحص": price,
        "دخول مرجعي": price if active else np.nan,
        "وقف": stop if active else np.nan,
        "هدف 1": targets[0] if active else np.nan,
        "هدف 2": targets[1] if active else np.nan,
        "هدف 3": targets[2] if active else np.nan,
        "مسافة الوقف %": risk / price * 100,
        "تغير 24 ساعة %": float(ticker["priceChangePercent"]),
        "حجم 24 ساعة USDT": float(ticker["quoteVolume"]),
        "التمويل الحالي %": rate * 100,
        "RSI": float(last["rsi"]),
        "حجم نسبي": float(last["volume_ratio"]),
        "الدعم": support,
        "المقاومة": resistance,
        "السبب": " • ".join(obstacles or reasons),
        "TradingView": (
            "https://www.tradingview.com/chart/"
            f"?symbol=BINANCE%3A{symbol}.P"
        ),
    }
    detail = {
        "candles": h,
        "history": historical_comparison(h, side),
        "long_score": long_score,
        "short_score": short_score,
        "reasons": reasons,
        "candle_time": str(last["date"]),
    }
    return row, detail


st.title("📊 محلل بايننس فيوتشر")
st.caption(
    "عقود USDT الدائمة | اتجاه يومي + 4 ساعات | "
    "مقارنة تاريخية لآفاق 3 و5 و7 أيام"
)
st.info(
    "أداة تحليل فقط. درجة الاتجاه ليست نسبة نجاح. "
    "الأهداف مستويات حسابية وليست توقعًا مضمونًا أو موعدًا للوصول."
)

with st.expander("⚙️ إعدادات الفحص", expanded=True):
    count = st.selectbox(
        "عدد العملات حسب حجم التداول",
        [20, 50, 100, 200, "الكل"],
        index=1,
    )
    min_volume = st.number_input(
        "أقل حجم تداول خلال 24 ساعة — مليون USDT",
        min_value=0.0, value=10.0, step=5.0,
    )
    threshold = st.slider("أقل درجة لإشارة دخول", 50, 95, 65, 5)
    st.caption(
        "الفحص يدوي، والشموع تُخزّن مؤقتًا 5 دقائق. "
        "فحص السوق كاملًا قد يستغرق عدة دقائق."
    )
    run = st.button("🔎 تحليل السوق الآن", type="primary")

if run:
    rows, details, errors = [], {}, []
    st.session_state.pop("results", None)
    progress = st.progress(0)
    note = st.empty()
    total = 0
    eligible_count = 0
    try:
        symbols = set(universe())
        tickers = api("/fapi/v1/ticker/24hr")
        now_ms = int(time.time() * 1000)
        eligible = [
            t for t in tickers
            if t["symbol"] in symbols
            and float(t["quoteVolume"]) >= min_volume * 1_000_000
            and 0 <= now_ms - int(t["closeTime"]) <= 300_000
        ]
        eligible.sort(
            key=lambda t: float(t["quoteVolume"]), reverse=True
        )
        eligible_count = len(eligible)
        if count != "الكل":
            eligible = eligible[:int(count)]
        total = len(eligible)

        funding_map = {}
        try:
            funding_rows = api("/fapi/v1/premiumIndex")
            funding_map = {x["symbol"]: x for x in funding_rows}
        except StopScan:
            raise
        except Exception:
            errors.append({
                "العملة": "التمويل",
                "السبب": "تعذر تحميل التمويل؛ يظهر كقيمة مفقودة",
            })

        for i, ticker in enumerate(eligible):
            symbol = ticker["symbol"]
            note.caption(f"تحليل {symbol} — {i + 1} / {total}")
            try:
                row, detail = analyze(
                    symbol, ticker,
                    funding_map.get(symbol, {}),
                    threshold,
                )
                rows.append(row)
                details[symbol] = detail
            except StopScan:
                raise
            except Exception as exc:
                errors.append({
                    "العملة": symbol,
                    "السبب": str(exc)[:220],
                })
            progress.progress((i + 1) / max(total, 1))
            time.sleep(0.15)
    except Exception as exc:
        errors.append({"العملة": "الفحص", "السبب": str(exc)})
    finally:
        progress.empty()
        note.empty()

    st.session_state.results = {
        "rows": rows,
        "details": details,
        "errors": errors,
        "requested": total,
        "eligible": eligible_count,
        "time": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    }

saved = st.session_state.get("results")
if not saved:
    st.caption("اضغط «تحليل السوق الآن» للبدء.")
    st.stop()

if saved["errors"]:
    with st.expander("تفاصيل البيانات غير المتاحة"):
        st.dataframe(
            pd.DataFrame(saved["errors"]),
            hide_index=True,
            use_container_width=True,
        )

if not saved["rows"]:
    st.error(
        "لم تتوفر نتائج. افتح تفاصيل البيانات غير المتاحة "
        "لمعرفة السبب وصوّرها."
    )
    st.stop()

result = pd.DataFrame(saved["rows"]).sort_values(
    ["درجة الاتجاه", "حجم 24 ساعة USDT"],
    ascending=False,
)
st.caption(
    f"وقت انتهاء الفحص: {saved['time']} | "
    f"تم تحليل {len(result)} من {saved['requested']} عملة مختارة | "
    f"المؤهلة بالحجم: {saved['eligible']}"
)
st.caption(
    "النتائج لقطة وقت الفحص وليست بثًا مباشرًا. "
    "تغيير الإعدادات يحتاج ضغط زر التحليل من جديد."
)
a, b, c = st.columns(3)
a.metric("تم تحليلها", len(result))
b.metric("شراء Long", int((result["القرار"] == "شراء Long").sum()))
c.metric("بيع Short", int((result["القرار"] == "بيع Short").sum()))

columns = [
    "TradingView", "القرار", "درجة الاتجاه",
    "السعر عند الفحص", "دخول مرجعي", "وقف",
    "هدف 1", "هدف 2", "هدف 3", "مسافة الوقف %",
    "التمويل الحالي %", "السبب",
]


def show_table(frame):
    view = frame[columns].copy()
    prices = [
        "السعر عند الفحص", "دخول مرجعي", "وقف",
        "هدف 1", "هدف 2", "هدف 3",
    ]
    for col in prices:
        view[col] = view[col].map(
            lambda x: f"{x:.9g}" if pd.notna(x) else "—"
        )
    st.dataframe(
        view,
        column_config={
            "TradingView": st.column_config.LinkColumn(
                "العملة ↗",
                display_text=r".*BINANCE%3A(.*)\.P",
            ),
        },
        hide_index=True,
        use_container_width=True,
    )


st.subheader("🏆 فرص الدخول")
opportunities = result[result["القرار"] != "مراقبة"]
if opportunities.empty:
    st.info(
        "لا توجد إشارات تستوفي شروط الدخول الحالية. "
        "جميع العملات وأسباب المراقبة موجودة بالجدول التالي."
    )
else:
    show_table(opportunities)

with st.expander("📋 جميع العملات وأسباب القرار", expanded=True):
    show_table(result)

st.download_button(
    "تنزيل نتائج الفحص CSV",
    result.to_csv(index=False).encode("utf-8-sig"),
    file_name="binance_futures_scan.csv",
    mime="text/csv",
)

st.subheader("🔎 تحليل عملة بالتفصيل")
symbol = st.selectbox("اختر العملة", result["العملة"].tolist())
row = result[result["العملة"] == symbol].iloc[0]
detail = saved["details"][symbol]

st.markdown(f"### {symbol} — {row['القرار']}")
st.write(row["السبب"])
x, y, z = st.columns(3)
x.metric("درجة الشراء", detail["long_score"])
y.metric("درجة البيع", detail["short_score"])
z.metric("RSI — 4 ساعات", f"{row['RSI']:.1f}")
st.caption(f"بداية آخر شمعة 4 ساعات مغلقة: {detail['candle_time']}")
st.write(
    f"الدعم: {row['الدعم']:.9g} | "
    f"المقاومة: {row['المقاومة']:.9g} | "
    f"الحجم النسبي: {row['حجم نسبي']:.2f}"
)
st.link_button("فتح العملة في TradingView", row["TradingView"])

chart_data = detail["candles"].tail(120)
fig = go.Figure(go.Candlestick(
    x=chart_data["date"],
    open=chart_data["open"],
    high=chart_data["high"],
    low=chart_data["low"],
    close=chart_data["close"],
    name=symbol,
))
for name in ("ema20", "ema50"):
    fig.add_trace(go.Scatter(
        x=chart_data["date"],
        y=chart_data[name],
        name=name.upper(),
        mode="lines",
    ))
if row["القرار"] != "مراقبة":
    for name, color in [
        ("دخول مرجعي", "blue"),
        ("وقف", "red"),
        ("هدف 1", "green"),
        ("هدف 2", "green"),
        ("هدف 3", "green"),
    ]:
        fig.add_hline(
            y=float(row[name]),
            line_color=color,
            line_dash="dot",
            annotation_text=name,
        )
fig.update_layout(
    height=480,
    xaxis_rangeslider_visible=False,
    margin=dict(l=10, r=10, t=30, b=20),
)
st.plotly_chart(fig, use_container_width=True)

st.subheader("📈 مقارنة بحالات تاريخية مشابهة")
history = detail["history"]
if history.empty:
    st.caption("لا توجد بيانات كافية للمقارنة.")
else:
    st.dataframe(
        history.round(2),
        hide_index=True,
        use_container_width=True,
    )
st.caption(
    "هذه إحصاءات وصفية لحركات السعر بعد حالات مشابهة؛ "
    "ليست اختبار نجاح الدخول والوقف والأهداف. "
    "العينات محدودة ولا تشمل الرسوم أو التمويل أو الانزلاق، "
    "ولا تمثل احتمال ربح مؤكد."
)

with st.expander("كيف تعمل النسخة؟"):
    st.write(
        "تُحسب درجتان مستقلتان للشراء والبيع من الاتجاه "
        "على اليومي و4 ساعات وRSI وMACD والزخم. "
        "يُستخدم الاتجاه الأقوى إذا استوفى الحد المختار "
        "وكان السعر غير ممتد والوقف مناسبًا."
    )
    st.write(
        "الدعم والمقاومة من آخر 30 شمعة على 4 ساعات. "
        "الوقف خارج المستوى مع هامش ATR. "
        "الأهداف تساوي 1.5 و2 و3 أضعاف مسافة الوقف، "
        "وليست مستويات مقاومة أو دعم متوقعة."
    )
    st.write(
        "الدخول مرجع سعري عند الفحص وليس أمرًا منفذًا. "
        "التمويل معروض للمراجعة ولا يُفترض أنه ثابت. "
        "النسب تخص حركة السعر دون رافعة مالية."
    )
    st.write(
        "هذه النسخة لا تتضمن أخبارًا أو توصيات محللين "
        "أو تنفيذ صفقات أو اختبارًا تاريخيًا كاملًا."
        )
