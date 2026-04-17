import streamlit as st
import yfinance as yf
import requests
import json
import os
import uuid
from openai import OpenAI

# -----------------------------
# Setup
# -----------------------------
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

st.set_page_config(page_title="AI Investment App", layout="wide")

# -----------------------------
# User Login (simple)
# -----------------------------
if "user" not in st.session_state:
    st.session_state.user = None

if st.session_state.user is None:
    username = st.text_input("Enter your username")
    if st.button("Login"):
        st.session_state.user = username
        st.rerun()
    st.stop()

# -----------------------------
# File per user
# -----------------------------
PORTFOLIO_FILE = f"portfolio_{st.session_state.user}.json"
WATCHLIST_FILE = f"watchlist_{st.session_state.user}.json"

# -----------------------------
# Load / Save
# -----------------------------
def load_data(file):
    if os.path.exists(file):
        with open(file, "r") as f:
            return json.load(f)
    return []

def save_data(file, data):
    with open(file, "w") as f:
        json.dump(data, f)

portfolio = load_data(PORTFOLIO_FILE)
watchlist = load_data(WATCHLIST_FILE)

# -----------------------------
# Data Functions
# -----------------------------
def get_stock_price(ticker):
    try:
        data = yf.Ticker(ticker).history(period="1d")
        if data.empty:
            return None
        return data["Close"].iloc[-1]
    except:
        return None

def get_stock_fundamentals(ticker):
    try:
        info = yf.Ticker(ticker).info
        return {
            "pe": info.get("trailingPE"),
            "market_cap": info.get("marketCap"),
        }
    except:
        return {}

def get_price_trend(ticker):
    try:
        hist = yf.Ticker(ticker).history(period="5d")
        return ((hist["Close"].iloc[-1] - hist["Close"].iloc[0]) / hist["Close"].iloc[0]) * 100
    except:
        return 0

NEWS_API_KEY = os.getenv("NEWS_API_KEY")

def get_news(ticker):
    try:
        url = f"https://newsapi.org/v2/everything?q={ticker}&apiKey={NEWS_API_KEY}"
        articles = requests.get(url).json().get("articles", [])[:3]
        return "\n".join([f"- {a['title']}" for a in articles])
    except:
        return "No news"

# -----------------------------
# AI Engine
# -----------------------------
def analyze_stock(data):
    prompt = f"""
    You are a professional investor.

    Analyze:
    {data}

    Give:
    - Decision (BUY / HOLD / SELL)
    - Confidence (1-10)
    - Reasoning
    """

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[{"role": "user", "content": prompt}]
    )

    return response.choices[0].message.content

# -----------------------------
# UI
# -----------------------------
st.title(f"📊 AI Investment App ({st.session_state.user})")

# -----------------------------
# Add Asset
# -----------------------------
st.header("➕ Add Asset")

with st.form("add"):
    name = st.text_input("Name")
    ticker = st.text_input("Ticker")
    qty = st.number_input("Quantity", min_value=0.0)
    buy_price = st.number_input("Buy Price", min_value=0.0)
    currency = st.selectbox("Currency", ["USD", "EUR", "GBP"])

    if st.form_submit_button("Add"):
        if get_stock_price(ticker) is None:
            st.error("Invalid ticker ❌")
        else:
            portfolio.append({
                "id": str(uuid.uuid4()),
                "name": name,
                "ticker": ticker.upper(),
                "qty": qty,
                "buy_price": buy_price,
                "currency": currency
            })
            save_data(PORTFOLIO_FILE, portfolio)
            st.success("Added!")

# -----------------------------
# Portfolio
# -----------------------------
st.header("💼 Portfolio")

total_value = 0
total_investment = 0

for asset in portfolio:
    price = get_stock_price(asset["ticker"])
    if price is None:
        continue

    value = price * asset["qty"]
    investment = asset["buy_price"] * asset["qty"]
    roi = ((value - investment) / investment) * 100

    total_value += value
    total_investment += investment

    col1, col2 = st.columns([4,1])

    with col1:
        st.write(f"{asset['name']} → {value:.2f} | ROI: {roi:.2f}%")

    with col2:
        if st.button("❌", key=asset["id"]):
            portfolio = [a for a in portfolio if a["id"] != asset["id"]]
            save_data(PORTFOLIO_FILE, portfolio)
            st.rerun()

if total_investment > 0:
    total_roi = ((total_value - total_investment) / total_investment) * 100
else:
    total_roi = 0

st.subheader(f"Total: {total_value:.2f} | ROI: {total_roi:.2f}%")

# -----------------------------
# WATCHLIST SECTION (NEW 🔥)
# -----------------------------
st.header("⭐ Watchlist")

# Add to watchlist
new_watch = st.text_input("Add ticker to watchlist")

if st.button("Add to Watchlist"):
    if get_stock_price(new_watch) is None:
        st.error("Invalid ticker ❌")
    else:
        if new_watch.upper() not in watchlist:
            watchlist.append(new_watch.upper())
            save_data(WATCHLIST_FILE, watchlist)
            st.success("Added to watchlist")

# Display watchlist
for ticker in watchlist:
    price = get_stock_price(ticker)

    col1, col2, col3 = st.columns([3,1,1])

    with col1:
        st.write(f"{ticker} → {price:.2f}" if price else ticker)

    with col2:
        if st.button("Analyze", key=f"an_{ticker}"):
            data = {
                "ticker": ticker,
                "price": price,
                "trend": get_price_trend(ticker),
                "news": get_news(ticker)
            }
            result = analyze_stock(data)
            st.write(result)

    with col3:
        if st.button("❌", key=f"del_{ticker}"):
            watchlist.remove(ticker)
            save_data(WATCHLIST_FILE, watchlist)
            st.rerun()

# -----------------------------
# Stock Scanner
# -----------------------------
st.header("🔎 Quick Stock Analysis")

ticker_input = st.text_input("Enter ticker for quick analysis")

if st.button("Analyze Stock"):
    if get_stock_price(ticker_input) is None:
        st.error("Invalid ticker ❌")
    else:
        data = {
            "ticker": ticker_input,
            "price": get_stock_price(ticker_input),
            "trend": get_price_trend(ticker_input),
            "news": get_news(ticker_input)
        }
        result = analyze_stock(data)
        st.write(result)