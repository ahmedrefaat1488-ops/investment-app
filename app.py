import streamlit as st
import yfinance as yf
import requests
import os
import uuid
from openai import OpenAI
from supabase import create_client

# -----------------------------
# Setup
# -----------------------------
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")
)

st.set_page_config(page_title="AI Investment App", layout="wide")

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

def get_price_trend(ticker):
    try:
        hist = yf.Ticker(ticker).history(period="5d")
        return ((hist["Close"].iloc[-1] - hist["Close"].iloc[0]) / hist["Close"].iloc[0]) * 100
    except:
        return 0

def get_news(ticker):
    try:
        url = f"https://newsapi.org/v2/everything?q={ticker}&apiKey={os.getenv('NEWS_API_KEY')}"
        articles = requests.get(url).json().get("articles", [])[:3]
        return "\n".join([f"- {a['title']}" for a in articles])
    except:
        return "No news"

# -----------------------------
# Supabase Functions
# -----------------------------
def load_portfolio():
    return supabase.table("portfolio").select("*").execute().data

def add_asset(asset):
    supabase.table("portfolio").insert(asset).execute()

def delete_asset(asset_id):
    supabase.table("portfolio").delete().eq("id", asset_id).execute()

def load_watchlist():
    return supabase.table("watchlist").select("*").execute().data

def add_watch(ticker):
    supabase.table("watchlist").insert({
        "id": str(uuid.uuid4()),
        "ticker": ticker
    }).execute()

def delete_watch(asset_id):
    supabase.table("watchlist").delete().eq("id", asset_id).execute()

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
st.title("📊 AI Investment Dashboard")

portfolio = load_portfolio()
watchlist = load_watchlist()

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
            add_asset({
                "id": str(uuid.uuid4()),
                "name": name,
                "ticker": ticker.upper(),
                "qty": qty,
                "buy_price": buy_price,
                "currency": currency
            })
            st.success("Added!")
            st.rerun()

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
        st.write(f"{asset['name']} ({asset['ticker']}) → {value:.2f} | ROI: {roi:.2f}%")

    with col2:
        if st.button("❌", key=asset["id"]):
            delete_asset(asset["id"])
            st.rerun()

# Total ROI
if total_investment > 0:
    total_roi = ((total_value - total_investment) / total_investment) * 100
else:
    total_roi = 0

st.subheader(f"💰 Total: {total_value:.2f} | ROI: {total_roi:.2f}%")

# -----------------------------
# Watchlist
# -----------------------------
st.header("⭐ Watchlist")

new_watch = st.text_input("Add ticker")

if st.button("Add to Watchlist"):
    if get_stock_price(new_watch) is None:
        st.error("Invalid ticker ❌")
    else:
        add_watch(new_watch.upper())
        st.success("Added!")
        st.rerun()

for item in watchlist:
    ticker = item["ticker"]
    price = get_stock_price(ticker)

    col1, col2, col3 = st.columns([3,1,1])

    with col1:
        st.write(f"{ticker} → {price:.2f}" if price else ticker)

    with col2:
        if st.button("Analyze", key=f"an_{item['id']}"):
            data = {
                "ticker": ticker,
                "price": price,
                "trend": get_price_trend(ticker),
                "news": get_news(ticker)
            }
            st.write(analyze_stock(data))

    with col3:
        if st.button("❌", key=f"del_{item['id']}"):
            delete_watch(item["id"])
            st.rerun()
