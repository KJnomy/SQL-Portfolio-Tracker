# SQL Portfolio Tracker

A full-stack financial portfolio tracking dashboard built using **Python, Streamlit, and MySQL**. 
This tool fetches live market data using the `yfinance` API and calculates advanced financial metrics
like **XIRR** to track true annualized wealth growth.

##  Key Features
* **Live Price Sync**: One-click integration with Yahoo Finance to fetch current prices (`LTP`) for Indian equities.
* **Investment vs Market Value**: Dynamic interactive line chart (Daily/Weekly/Monthly) showing the gap between
    deployed capital and current portfolio valuation.
* **XIRR Engine**: Time-weighted performance metrics calculated using the `pyxirr` library for irregular cash flows.
* **Manual Ledger Input**: Sidebar form to seamlessly insert new BUY/SELL transactions directly into the MySQL database.
* **Asset Allocation**: Visual pie and bar charts for sector-wise and stock-wise P&L breakdown.

##  Tech Stack
* **Frontend**: Streamlit, Plotly Express
* **Backend**: MySQL (Relational DB Design)
* **Data & Math**: Pandas, NumPy, SQLAlchemy, yfinance, pyxirr
