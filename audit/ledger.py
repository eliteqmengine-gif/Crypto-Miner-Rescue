import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime
from typing import List, Optional, Tuple

DB_NAME = "trading_app.db"
_db_lock = threading.RLock()


@contextmanager
def get_db():
    """Create a database connection for a single operation.

    The connection is opened per call, serialized by a re-entrant lock for
    thread-safe reads and writes, and always closed before returning.
    """
    conn = sqlite3.connect(DB_NAME, timeout=30, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")
    try:
        with _db_lock:
            yield conn
            conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """Initialize database with optimized schema and indexes."""
    with get_db() as conn:
        c = conn.cursor()
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                strategy TEXT NOT NULL,
                symbol TEXT NOT NULL,
                side TEXT NOT NULL,
                price REAL NOT NULL,
                size REAL NOT NULL,
                fees REAL NOT NULL,
                slippage REAL NOT NULL,
                pnl REAL NOT NULL
            )
            """
        )

        c.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON trades(timestamp)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_symbol ON trades(symbol)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_strategy ON trades(strategy)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_pnl ON trades(pnl)')


def save_trade(trade):
    """Save a single trade."""
    with get_db() as conn:
        c = conn.cursor()
        c.execute(
            """
            INSERT INTO trades
            (timestamp, strategy, symbol, side, price, size, fees, slippage, pnl)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(trade.timestamp),
                trade.strategy,
                trade.symbol,
                trade.side,
                trade.price,
                trade.size,
                trade.fees,
                trade.slippage,
                trade.pnl,
            ),
        )


def save_trades_batch(trades: List) -> int:
    """Batch insert trades for better performance.

    Args:
        trades: List of TradeEvent objects

    Returns:
        Number of trades inserted
    """
    with get_db() as conn:
        c = conn.cursor()
        data = [
            (
                str(trade.timestamp),
                trade.strategy,
                trade.symbol,
                trade.side,
                trade.price,
                trade.size,
                trade.fees,
                trade.slippage,
                trade.pnl,
            )
            for trade in trades
        ]

        c.executemany(
            """
            INSERT INTO trades
            (timestamp, strategy, symbol, side, price, size, fees, slippage, pnl)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            data,
        )

        return len(trades)


def get_trades(limit: int = 100, offset: int = 0) -> List[Tuple]:
    """Get paginated trades."""
    with get_db() as conn:
        c = conn.cursor()
        c.execute(
            "SELECT * FROM trades ORDER BY timestamp DESC LIMIT ? OFFSET ?",
            (limit, offset),
        )
        return c.fetchall()


def get_trades_by_symbol(symbol: str, limit: int = 100, offset: int = 0) -> List[Tuple]:
    """Get paginated trades for a specific symbol."""
    with get_db() as conn:
        c = conn.cursor()
        c.execute(
            "SELECT * FROM trades WHERE symbol = ? ORDER BY timestamp DESC LIMIT ? OFFSET ?",
            (symbol, limit, offset),
        )
        return c.fetchall()


def get_trades_by_strategy(strategy: str, limit: int = 100, offset: int = 0) -> List[Tuple]:
    """Get paginated trades for a specific strategy."""
    with get_db() as conn:
        c = conn.cursor()
        c.execute(
            "SELECT * FROM trades WHERE strategy = ? ORDER BY timestamp DESC LIMIT ? OFFSET ?",
            (strategy, limit, offset),
        )
        return c.fetchall()


def get_total_pnl() -> float:
    """Get total realized P&L across all trades."""
    with get_db() as conn:
        c = conn.cursor()
        c.execute("SELECT SUM(pnl) FROM trades")
        total = c.fetchone()[0]
        return total or 0.0


def get_pnl_by_symbol(symbol: str) -> float:
    """Get total P&L for a specific symbol."""
    with get_db() as conn:
        c = conn.cursor()
        c.execute("SELECT SUM(pnl) FROM trades WHERE symbol = ?", (symbol,))
        total = c.fetchone()[0]
        return total or 0.0


def get_pnl_by_strategy(strategy: str) -> float:
    """Get total P&L for a specific strategy."""
    with get_db() as conn:
        c = conn.cursor()
        c.execute("SELECT SUM(pnl) FROM trades WHERE strategy = ?", (strategy,))
        total = c.fetchone()[0]
        return total or 0.0


def get_trade_count() -> int:
    """Get total number of trades in database."""
    with get_db() as conn:
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM trades")
        return c.fetchone()[0] or 0


def close_db():
    """No-op retained for backward compatibility with the shutdown sequence."""
    return None
