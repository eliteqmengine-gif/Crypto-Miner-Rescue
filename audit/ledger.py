import sqlite3
from datetime import datetime

DB_NAME = "trading_app.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            strategy TEXT,
            symbol TEXT,
            side TEXT,
            price REAL,
            size REAL,
            fees REAL,
            slippage REAL,
            pnl REAL
        )
    ''')
    conn.commit()
    conn.close()

def save_trade(trade):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        INSERT INTO trades 
        (timestamp, strategy, symbol, side, price, size, fees, slippage, pnl)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        str(trade.timestamp),
        trade.strategy,
        trade.symbol,
        trade.side,
        trade.price,
        trade.size,
        trade.fees,
        trade.slippage,
        trade.pnl
    ))
    conn.commit()
    conn.close()

def get_all_trades():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM trades")
    trades = c.fetchall()
    conn.close()
    return trades

def get_total_pnl():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT SUM(pnl) FROM trades")
    total = c.fetchone()[0]
    conn.close()
    return total or 0
