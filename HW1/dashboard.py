import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta

st.set_page_config(page_title="SET50 Dashboard", layout="wide")
st.title("📈 SET50 Thailand Dashboard")

SET50_SYMBOLS = {
    "ADVANC": "Advanced Info Service",
    "AOT": "Airports of Thailand",
    "BDMS": "Bangkok Dusit Medical",
    "BBL": "Bangkok Bank",
    "CPALL": "CP All",
    "CPF": "CP Foods",
    "DELTA": "Delta Electronics",
    "GULF": "Gulf Energy",
    "INTUCH": "Intouch Holdings",
    "KBANK": "Kasikornbank",
    "KTB": "Krung Thai Bank",
    "KTC": "Krungthai Card",
    "LH": "Land and Houses",
    "MINT": "Minor International",
    "OR": "PTT Oil and Retail",
    "PTT": "PTT",
    "PTTEP": "PTT Exploration",
    "SCB": "SCB Bank",
    "SCC": "Siam Cement",
    "TU": "Thai Union",
}

suffix = ".BK"
tickers = [s + suffix for s in SET50_SYMBOLS]

with st.sidebar:
    st.header("Settings")
    period = st.selectbox("Period", ["1mo", "3mo", "6mo", "1y", "2y", "5y"], index=2)

st.subheader("SET50 Index")
try:
    set50 = yf.download("^SET50.BK", period=period, auto_adjust=True)
    if not set50.empty:
        col1, col2, col3, col4 = st.columns(4)
        latest = set50["Close"].iloc[-1]
        prev = set50["Close"].iloc[0]
        hi = set50["High"].max()
        lo = set50["Low"].min()
        chg = latest - prev
        pct = (chg / prev) * 100
        col1.metric("Current", f"{latest:.2f}", f"{chg:.2f} ({pct:+.2f}%)")
        col2.metric("Open", f"{set50['Open'].iloc[-1]:.2f}")
        col3.metric("High (period)", f"{hi:.2f}")
        col4.metric("Low (period)", f"{lo:.2f}")

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=set50.index, y=set50["Close"], mode="lines", name="Close"))
        fig.update_layout(height=400, margin=dict(l=0, r=0, t=10, b=0))
        st.plotly_chart(fig, width="stretch")
    else:
        st.warning("No SET50 data available.")
except Exception as e:
    st.error(f"Could not fetch SET50 index: {e}")

st.subheader("Top SET50 Stocks")
try:
    data = yf.download(tickers, period=period, group_by="ticker", auto_adjust=True, progress=False)
    if not data.empty:
        rows = []
        for sym, name in SET50_SYMBOLS.items():
            try:
                if isinstance(data.columns, pd.MultiIndex):
                    close = data[(sym + suffix, "Close")]
                else:
                    close = data[sym + suffix]["Close"]
                if close.dropna().empty:
                    continue
                first = close.dropna().iloc[0]
                last = close.dropna().iloc[-1]
                chg = last - first
                pct = (chg / first) * 100
                low = close.dropna().min()
                high = close.dropna().max()
                rows.append({"Symbol": sym, "Company": name, "Price": round(last, 2),
                             "Change%": round(pct, 2), "High": round(high, 2), "Low": round(low, 2)})
            except Exception:
                continue

        if rows:
            df = pd.DataFrame(rows).sort_values("Change%", ascending=False)
            col_l, col_r = st.columns(2)
            with col_l:
                st.markdown("**Top Gainers**")
                st.dataframe(df.head(5).reset_index(drop=True), width="stretch", hide_index=True)
            with col_r:
                st.markdown("**Top Losers**")
                st.dataframe(df.tail(5).sort_values("Change%").reset_index(drop=True), width="stretch", hide_index=True)

            st.subheader("All SET50 Stocks")
            st.dataframe(df.reset_index(drop=True), width="stretch", hide_index=True)

            df["color"] = df["Change%"].apply(lambda x: "green" if x >= 0 else "red")
            fig2 = px.pie(df, names="Symbol", values="Change%", title="SET50 Performance (%)",
                          color="color", color_discrete_map={"green": "#2ca02c", "red": "#d62728"}, height=400)
            fig2.update_traces(textposition="inside", textinfo="percent+label")
            st.plotly_chart(fig2, width="stretch")
    else:
        st.warning("No stock data available.")
except Exception as e:
    st.error(f"Could not fetch stock data: {e}")

st.subheader("Top 5 Stakeholders")
selected = st.selectbox("Select a company", options=list(SET50_SYMBOLS.keys()), format_func=lambda s: f"{s} - {SET50_SYMBOLS[s]}")
try:
    ticker = yf.Ticker(selected + suffix)
    holders = ticker.institutional_holders
    if holders is not None and not holders.empty:
        top5 = holders.head(5)[["Holder", "% Out", "Value"]].copy()
        top5["% Out"] = top5["% Out"].apply(lambda x: f"{x:.2f}%")
        top5["Value"] = top5["Value"].apply(lambda x: f"${x:,.0f}")
        st.dataframe(top5.reset_index(drop=True), width="stretch", hide_index=True)
    else:
        st.info("No institutional holder data available.")
except Exception as e:
    st.error(f"Could not fetch stakeholders: {e}")
