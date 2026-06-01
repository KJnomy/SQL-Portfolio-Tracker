CREATE DATABASE My_Portfolio;
USE My_Portfolio;

-- 1. Assets Master Table (Keeps track of stock sectors)
CREATE TABLE Assets (
    Ticker VARCHAR(50) PRIMARY KEY,
    Sector VARCHAR(100) NOT NULL
);

-- 2. Transactions Ledger Table (Tracks buys and sells)
CREATE TABLE Transactions (
    ID INT AUTO_INCREMENT PRIMARY KEY,
    Ticker VARCHAR(50),
    TradeType ENUM('BUY', 'SELL') NOT NULL,
    Quantity INT NOT NULL,
    PricePerUnit DECIMAL(10, 2) NOT NULL,
    TradeDate DATE NOT NULL,
    FOREIGN KEY (Ticker) REFERENCES Assets(Ticker)
);

-- 3. Current Price Table (Stores the latest LTP from yfinance)
CREATE TABLE CurrentPrice (
    Ticker VARCHAR(50) PRIMARY KEY,
    LTP DECIMAL(10, 2) NOT NULL,
    FOREIGN KEY (Ticker) REFERENCES Assets(Ticker)
);