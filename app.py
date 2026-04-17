import streamlit as st
import yfinance as yf
import requests
import json
import os
from openai import OpenAI

# -----------------------------
# Setup
# -----------------------------
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

st.set_page_config(page_title="AI Investment App", layout="wide")

PORTFOLIO_FILE = "portfolio.json"
WATCHLIST = ["AAPL", "MSFT", "NVDA", "GOOGL"]

# -----------------------------
# Load / Save Portfolio
# -----------------------------
def load_portfolio():
    if os.path.exists(PORTFOLIO_FILE):
        with open(PORTFOLIO_FILE, "r") as f:
            return json.load(f)
    return []

def save_portfolio(data):
    with open(PORTFOLIO_FILE, "w") as f:
        json.dump(data, f)

portfolio = load_portfolio()

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
            "sector": info.get("sector")
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
        return "No news available"

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
    - Risks
    """

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[{"role": "user", "content": prompt}]
    )

    return response.choices[0].message.content

# -----------------------------
# UI
# -----------------------------
st.title("📊 AI Investment Dashboard")

# -----------------------------
# Add Asset
# -----------------------------
st.header("➕ Add Asset")

with st.form("add"):
    name = st.text_input("Name")
    ticker = st.text_input("Ticker (e.g. AAPL)")
    qty = st.number_input("Quantity", min_value=0.0)
    buy_price = st.number_input("Buy Price", min_value=0.0)
    currency = st.selectbox("Currency", ["USD", "EUR", "GBP"])

    if st.form_submit_button("Add"):
        price_test = get_stock_price(ticker)

        if price_test is None:
            st.error("Invalid ticker ❌")
        else:
            portfolio.append({
                "name": name,
                "ticker": ticker.upper(),
                "qty": qty,
                "buy_price": buy_price,
                "currency": currency
            })
            save_portfolio(portfolio)
            st.success("Asset added!")

# -----------------------------
# Portfolio
# -----------------------------
st.header("💼 Portfolio")

total_value = 0
total_investment = 0
summary = ""

for i, asset in enumerate(portfolio):
    try:
        price = get_stock_price(asset["ticker"])

        if price is None:
            st.warning(f"Invalid ticker: {asset['ticker']}")
            continue

        value = price * asset["qty"]
        investment = asset["buy_price"] * asset["qty"]
        roi = ((value - investment) / investment) * 100

        total_value += value
        total_investment += investment

        col1, col2 = st.columns([4,1])

        with col1:
            st.write(f"**{asset['name']} ({asset['ticker']})** → {asset['currency']} {value:.2f} | ROI: {roi:.2f}%")

        with col2:
            if st.button("❌", key=i):
                portfolio.pop(i)
                save_portfolio(portfolio)
                st.experimental_rerun()

        summary += f"{asset['ticker']} ROI: {roi:.2f}% price: {price}\n"

    except Exception as e:
        st.warning(f"Error loading {asset['ticker']}")

# Total ROI
if total_investment > 0:
    total_roi = ((total_value - total_investment) / total_investment) * 100
else:
    total_roi = 0

st.subheader(f"💰 Total Value: {total_value:.2f} | ROI: {total_roi:.2f}%")

# -----------------------------
# AI Portfolio Advisor
# -----------------------------
st.header("🤖 Portfolio Advisor")

if st.button("Analyze Portfolio"):
    if summary.strip() == "":
        st.warning("Add assets first")
    else:
        result = analyze_stock(summary)
        st.write(result)

# -----------------------------
# Stock Scanner
# -----------------------------
st.header("🔎 Stock Scanner")

ticker_input = st.text_input("Enter ticker")

if st.button("Analyze Stock"):
    if ticker_input:
        price = get_stock_price(ticker_input)

        if price is None:
            st.error("Invalid ticker ❌")
        else:
            fundamentals = get_stock_fundamentals(ticker_input)
            trend = get_price_trend(ticker_input)
            news = get_news(ticker_input)

            data = {
                "ticker": ticker_input,
                "pe": fundamentals.get("pe"),
                "market_cap": fundamentals.get("market_cap"),
                "trend": trend,
                "news": news
            }

            result = analyze_stock(data)
            st.write(result)

# -----------------------------
# Watchlist Scanner
# -----------------------------
st.header("📡 Watchlist Scanner")

if st.button("Scan Watchlist"):
    for t in WATCHLIST:
        st.subheader(t)

        fundamentals = get_stock_fundamentals(t)
        trend = get_price_trend(t)
        news = get_news(t)

        data = {
            "ticker": t,
            "pe": fundamentals.get("pe"),
            "market_cap": fundamentals.get("market_cap"),
            "trend": trend,
            "news": news
        }

        result = analyze_stock(data)
        st.write(result)
