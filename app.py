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
    return yf.Ticker(ticker).history(period="1d")["Close"].iloc[-1]

def get_stock_fundamentals(ticker):
    info = yf.Ticker(ticker).info
    return {
        "pe": info.get("trailingPE"),
        "market_cap": info.get("marketCap"),
        "sector": info.get("sector")
    }

def get_price_trend(ticker):
    hist = yf.Ticker(ticker).history(period="5d")
    return ((hist["Close"].iloc[-1] - hist["Close"].iloc[0]) / hist["Close"].iloc[0]) * 100

NEWS_API_KEY = "YOUR_NEWS_API_KEY"

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
    - BUY / HOLD / SELL
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
# Portfolio UI
# -----------------------------
st.title("📊 AI Investment Dashboard")

st.header("➕ Add Asset")

with st.form("add"):
    name = st.text_input("Name")
    ticker = st.text_input("Ticker")
    qty = st.number_input("Quantity", min_value=0.0)
    buy_price = st.number_input("Buy Price", min_value=0.0)

    if st.form_submit_button("Add"):
        portfolio.append({
            "name": name,
            "ticker": ticker,
            "qty": qty,
            "buy_price": buy_price
        })
        save_portfolio(portfolio)
        st.success("Added!")

# -----------------------------
# Portfolio Display
# -----------------------------
st.header("💼 Portfolio")

total = 0
summary = ""

for asset in portfolio:
    try:
        price = get_stock_price(asset["ticker"])
        value = price * asset["qty"]
        roi = ((price - asset["buy_price"]) / asset["buy_price"]) * 100

        total += value

        st.write(f"{asset['name']} → ${value:.2f} | ROI: {roi:.2f}%")

        summary += f"""
        {asset['ticker']} ROI: {roi:.2f}% price: {price}
        """

    except:
        st.warning(f"Error loading {asset['ticker']}")

st.subheader(f"Total: ${total:.2f}")

# -----------------------------
# AI Portfolio Advisor
# -----------------------------
st.header("🤖 Portfolio Advisor")

if st.button("Analyze Portfolio"):
    result = analyze_stock(summary)
    st.write(result)

# -----------------------------
# Stock Scanner
# -----------------------------
st.header("🔎 Stock Scanner")

ticker_input = st.text_input("Enter ticker")

if st.button("Analyze Stock"):
    if ticker_input:
        fundamentals = get_stock_fundamentals(ticker_input)
        trend = get_price_trend(ticker_input)
        news = get_news(ticker_input)

        data = {
            "ticker": ticker_input,
            "pe": fundamentals["pe"],
            "market_cap": fundamentals["market_cap"],
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
            "pe": fundamentals["pe"],
            "market_cap": fundamentals["market_cap"],
            "trend": trend,
            "news": news
        }

        result = analyze_stock(data)
        st.write(result)