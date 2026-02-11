import streamlit as st
import pandas as pd
import os

# =========================================
# Page Config
# =========================================

st.set_page_config(
    page_title="Bake by Energy Price",
    page_icon="🥧",
    layout="wide"
)

st.title("🥧 Bake by Energy Price")
st.caption("Making wholesale electricity prices human.")

# =========================================
# Load Gold Data
# =========================================

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(BASE_DIR, "Data", "gold.csv")

@st.cache_data
def load_data(path):
    df = pd.read_csv(path)
    df["date_cet"] = pd.to_datetime(df["date_cet"], errors="coerce")
    df = df.dropna(subset=["date_cet"]).sort_values("date_cet")
    return df

if not os.path.exists(DATA_PATH):
    st.error(f"❌ gold.csv not found at {DATA_PATH}")
    st.stop()

gold_df = load_data(DATA_PATH)
gold_ts = gold_df.set_index("date_cet").sort_index()

# =========================================
# Controls
# =========================================

price_cols = list(gold_ts.columns)

country = st.selectbox(
    "Choose market",
    price_cols,
    index=price_cols.index("netherlands_nl") if "netherlands_nl" in price_cols else 0
)

available_dates = sorted(gold_ts.index.normalize().unique())

selected_date = st.selectbox(
    "Choose date",
    available_dates,
    index=len(available_dates) - 1,
    format_func=lambda x: x.strftime("%Y-%m-%d")
)

today = gold_ts.loc[gold_ts.index.normalize() == selected_date, [country]].dropna()

if today.empty:
    st.error("No data for selected date.")
    st.stop()

# =========================================
# Convert to €/kWh
# =========================================

today["price_kwh"] = today[country] / 1000

# Latest hour
current_row = today.tail(1)
current_price_kwh = float(current_row["price_kwh"].iloc[0])
current_time = current_row.index[0]

daily_avg_kwh = float(today["price_kwh"].mean())

# =========================================
# Baking Cost Calculation
# =========================================

OVEN_KW = 2.5       # average oven
BAKE_HOURS = 1.0    # 1 hour baking
BAKE_KWH = OVEN_KW * BAKE_HOURS

bake_cost_now = BAKE_KWH * current_price_kwh
bake_cost_avg = BAKE_KWH * daily_avg_kwh

# =========================================
# Recommendation Logic
# =========================================

low_thr = today["price_kwh"].quantile(0.33)
high_thr = today["price_kwh"].quantile(0.66)

def bake_reco(price):
    if price <= low_thr:
        return "🥧 APPLE PIE TIME", "success"
    elif price >= high_thr:
        return "🍰 CHEESECAKE TIME", "error"
    else:
        return "🧁 FLEXIBLE BAKING HOUR", "info"

title_now, kind_now = bake_reco(current_price_kwh)
title_day, kind_day = bake_reco(daily_avg_kwh)

# =========================================
# % Difference vs Daily Avg
# =========================================

pct_vs_avg = ((current_price_kwh - daily_avg_kwh) / daily_avg_kwh) * 100

# =========================================
# Layout
# =========================================

col1, col2 = st.columns(2)

with col1:
    st.subheader("Latest available hour")
    getattr(st, kind_now)(
        f"""
        **{title_now}**

        • Price: **{current_price_kwh*100:.2f} cents/kWh**  
        • Baking cost (1h oven): **€{bake_cost_now:.2f}**  
        • {pct_vs_avg:+.1f}% vs daily average
        """
    )

with col2:
    st.subheader("Selected day average")
    getattr(st, kind_day)(
        f"""
        • Avg price: **{daily_avg_kwh*100:.2f} cents/kWh**  
        • Avg baking cost: **€{bake_cost_avg:.2f}**
        """
    )

st.divider()

# =========================================
# Chart (€/kWh)
# =========================================

st.subheader("Hourly electricity price (cents per kWh)")
chart_df = today[["price_kwh"]].copy()
chart_df["price_kwh"] = chart_df["price_kwh"] * 100
chart_df = chart_df.rename(columns={"price_kwh": "cents/kWh"})
st.line_chart(chart_df)

# =========================================
# Cheapest / Most Expensive Hours
# =========================================

best_n = st.slider("Show best/worst hours", 1, 8, 3)

cheapest = today.nsmallest(best_n, "price_kwh")
priciest = today.nlargest(best_n, "price_kwh")

c3, c4 = st.columns(2)

with c3:
    st.markdown("### 🥧 Cheapest hours")
    cheapest_display = cheapest.copy()
    cheapest_display["cents/kWh"] = cheapest_display["price_kwh"] * 100
    st.dataframe(cheapest_display[["cents/kWh"]])

with c4:
    st.markdown("### 🍰 Most expensive hours")
    priciest_display = priciest.copy()
    priciest_display["cents/kWh"] = priciest_display["price_kwh"] * 100
    st.dataframe(priciest_display[["cents/kWh"]])

st.caption("Prices converted from wholesale €/MWh to consumer-friendly cents per kWh.")
