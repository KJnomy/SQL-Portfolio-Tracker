import streamlit as st
import pandas as pd
import plotly.express as px
from sqlalchemy import create_engine, text
import urllib.parse
import yfinance as yf
from pyxirr import xirr
from datetime import date
import numpy as np

# 1. PAGE CONFIGURATION
st.set_page_config(page_title="My Quant Dashboard", layout="wide")

# 2. DATABASE CONNECTION SETUP
raw_password = "YOUR_PASSWORD"  
safe_password = urllib.parse.quote_plus(raw_password)
engine = create_engine(f"mysql+pymysql://root:{safe_password}@localhost/MyPortfolio")

# SIDEBAR: DATA CONTROLS 
st.sidebar.header(" Data Controls")

# FEATURE 1: Manual Data Entry Form
with st.sidebar.expander(" Add New Transaction", expanded=False):
    with st.form("entry_form"):
        t_ticker = st.text_input("Ticker (e.g. RELIANCE)").upper().strip()
        t_type = st.selectbox("Trade Type", ["BUY", "SELL"])
        t_qty = st.number_input("Quantity", min_value=1)
        t_price = st.number_input("Price Per Unit", min_value=0.1)
        t_date = st.date_input("Trade Date", date.today())
        t_sector = st.text_input("Sector (Required for new stock)")
        
        if st.form_submit_button("Add to Database"):
            if not t_ticker:
                st.sidebar.error("Put the ticker!")
            else:
                try:
                    with engine.connect() as conn:
                        if t_sector:
                            conn.execute(text("INSERT IGNORE INTO Assets (Ticker, Sector) VALUES (:t, :s)"), {"t": t_ticker, "s": t_sector})
                        conn.execute(text("INSERT INTO Transactions (Ticker, TradeType, Quantity, PricePerUnit, TradeDate) VALUES (:t, :ty, :q, :p, :d)"),
                                     {"t": t_ticker, "ty": t_type, "q": t_qty, "p": t_price, "d": t_date})
                        conn.execute(text("INSERT IGNORE INTO CurrentPrice (Ticker, LTP) VALUES (:t, :p)"), {"t": t_ticker, "p": t_price})
                        conn.commit()
                    st.sidebar.success(f"Added {t_ticker} successfully!")
                    st.rerun()
                except Exception as e:
                    st.sidebar.error(f"Error: {e}")

# FEATURE 2: Live Price Update Button
if st.sidebar.button(' Update Live Prices'):
    with st.sidebar.status("Fetching Market Data...") as status:
        try:
            with engine.connect() as conn:
                tickers_df = pd.read_sql(text("SELECT Ticker FROM CurrentPrice"), conn)
            for ticker in tickers_df['Ticker'].tolist():
                search_ticker = ticker if "." in ticker else f"{ticker}.NS"
                data = yf.Ticker(search_ticker).history(period='1d')
                if not data.empty:
                    latest_price = float(data['Close'].iloc[-1])
                    with engine.connect() as conn:
                        conn.execute(text("UPDATE CurrentPrice SET LTP = :price WHERE Ticker = :ticker"), 
                                     {"price": latest_price, "ticker": ticker})
                        conn.commit()
            st.rerun()
        except Exception as e:
            st.sidebar.error(f"Update failed: {e}")

# MAIN DASHBOARD LOGIC 
try:
    with engine.connect() as conn:
        # Complex SQL Queries to aggregate portfolios
        df_sector = pd.read_sql(text("SELECT a.Sector, SUM(p.Net_Quantity * p.AvgBuyPrice) as InvestedValue FROM (SELECT Ticker, SUM(CASE WHEN TradeType = 'BUY' THEN Quantity ELSE 0 END) - SUM(CASE WHEN TradeType = 'SELL' THEN Quantity ELSE 0 END) AS Net_Quantity, SUM(CASE WHEN TradeType = 'BUY' THEN Quantity * PricePerUnit ELSE 0 END) / SUM(CASE WHEN TradeType = 'BUY' THEN Quantity ELSE 0 END) AS AvgBuyPrice FROM Transactions GROUP BY Ticker) AS p JOIN Assets a ON p.Ticker = a.Ticker WHERE p.Net_Quantity > 0 GROUP BY a.Sector;"), conn)
        df_pnl = pd.read_sql(text("SELECT p.Ticker, (c.LTP - p.AvgBuyPrice) * p.Net_Quantity AS PnL, (p.Net_Quantity * c.LTP) as CurrentValue FROM (SELECT Ticker, SUM(CASE WHEN TradeType = 'BUY' THEN Quantity ELSE 0 END) - SUM(CASE WHEN TradeType = 'SELL' THEN Quantity ELSE 0 END) AS Net_Quantity, SUM(CASE WHEN TradeType = 'BUY' THEN Quantity * PricePerUnit ELSE 0 END) / SUM(CASE WHEN TradeType = 'BUY' THEN Quantity ELSE 0 END) AS AvgBuyPrice FROM Transactions GROUP BY Ticker) AS p JOIN CurrentPrice c ON p.Ticker = c.Ticker WHERE p.Net_Quantity > 0;"), conn)
        df_trans = pd.read_sql(text("SELECT TradeDate, TradeType, Quantity, PricePerUnit, (Quantity * PricePerUnit) as Amount, Ticker FROM Transactions"), conn)

    st.title("My Personal Quant Dashboard")

    # 3. TOP KPI METRICS
    if not df_sector.empty:
        total_invested = df_sector['InvestedValue'].sum()
        current_value = df_pnl['CurrentValue'].sum()
        total_pnl = current_value - total_invested
        pnl_pct = (total_pnl / total_invested * 100) if total_invested > 0 else 0

        m1, m2, m3 = st.columns(3)
        m1.metric("Total Invested", f"₹{total_invested:,.2f}")
        m2.metric("Current Value", f"₹{current_value:,.2f}")
        m3.metric("Absolute P&L", f"₹{total_pnl:,.2f}", f"{pnl_pct:.2f}%")

        st.markdown("---")

        # 4. INVESTMENT VS MARKET VALUE (HISTORICAL ENGINE)
        st.subheader(" Investment Cost vs Market Value")
        col_ctrl1, col_ctrl2 = st.columns(2)
        with col_ctrl1:
            start_date, end_date = st.date_input("Select Range", [pd.to_datetime("2025-12-01"), pd.to_datetime("today")])
        with col_ctrl2:
            freq = st.radio("Group By:", ["Daily", "Weekly", "Monthly"], horizontal=True)

        freq_map = {"Daily": "D", "Weekly": "W-MON", "Monthly": "MS"}

        with st.spinner("Calculating Historical Performance..."):
            df_trans['TradeDate'] = pd.to_datetime(df_trans['TradeDate']).dt.date
            all_tickers = df_trans['Ticker'].unique().tolist()
            
            idx = pd.date_range(start=start_date, end=end_date).date
            df_final = pd.DataFrame(index=idx)
            df_final['Total_Investment'] = 0.0
            df_final['Total_Market_Value'] = 0.0

            for ticker in all_tickers:
                yt_ticker = ticker if "." in ticker else f"{ticker}.NS"
                try:
                    stock_data = yf.download(yt_ticker, start=start_date, end=end_date, progress=False)
                    if not stock_data.empty:
                        if 'Close' in stock_data.columns:
                            prices_raw = stock_data['Close']
                        else:
                            prices_raw = stock_data
                        
                        prices_series = prices_raw.reindex(pd.to_datetime(idx)).ffill().bfill()
                        prices = prices_series.values.flatten()
                        
                        ticker_ts = df_trans[df_trans['Ticker'] == ticker]
                        qty_arr, cost_arr = [], []
                        current_qty, current_cost = 0.0, 0.0
                        
                        for d in idx:
                            day_trans = ticker_ts[ticker_ts['TradeDate'] == d]
                            for _, row in day_trans.iterrows():
                                if row['TradeType'] == 'BUY':
                                    current_qty += row['Quantity']
                                    current_cost += (row['Quantity'] * row['PricePerUnit'])
                                else:
                                    avg_price = current_cost / current_qty if current_qty > 0 else 0
                                    current_qty -= row['Quantity']
                                    current_cost -= (row['Quantity'] * avg_price)
                            qty_arr.append(max(current_qty, 0))
                            cost_arr.append(max(current_cost, 0))

                        df_final['Total_Investment'] += np.array(cost_arr)
                        df_final['Total_Market_Value'] += np.array(qty_arr) * prices
                except:
                    continue

            df_final.index = pd.to_datetime(df_final.index)
            df_plot = df_final.resample(freq_map[freq]).last().reset_index()
            df_plot.columns = ['Date', 'Investment', 'Market Value']
            
            fig_growth = px.line(df_plot, x='Date', y=['Investment', 'Market Value'], 
                                 template="plotly_dark", 
                                 color_discrete_map={'Investment': '#F4D03F', 'Market Value': '#2ECC71'})
            fig_growth.update_traces(line_width=3)
            st.plotly_chart(fig_growth, use_container_width=True)

        st.markdown("---")

        # 5. SEPARATE XIRR ANALYSIS
        st.subheader(" Performance Analysis (XIRR)")
        cashflows = df_trans.copy()
        cashflows['Val'] = cashflows.apply(lambda x: -x['Amount'] if x['TradeType'] == 'BUY' else x['Amount'], axis=1)
        d, v = cashflows['TradeDate'].tolist(), cashflows['Val'].tolist()
        d.append(date.today())
        v.append(current_value)
        try:
            res_xirr = xirr(d, v) * 100
            st.metric("Personal XIRR", f"{res_xirr:.2f}%")
        except:
            st.warning("XIRR ke liye aur data chahiye.")

        st.markdown("---")
        
        # 6. ALLOCATION CHARTS
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Sector Allocation")
            st.plotly_chart(px.pie(df_sector, values='InvestedValue', names='Sector', hole=0.4, template="plotly_dark"), use_container_width=True)
        with c2:
            st.subheader("Stock Wise P&L")
            st.plotly_chart(px.bar(df_pnl, x='Ticker', y='PnL', color='PnL', template="plotly_dark", color_continuous_scale='RdYlGn'), use_container_width=True)
    else:
        st.info("Bhai, pehle sidebar se transactions add karo!")

except Exception as e:
    st.error(f"Locha: {e}")
finally:
    engine.dispose()


# run by  "streamlit run Dashboard_final"
