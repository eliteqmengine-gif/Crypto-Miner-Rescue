import sqlite3
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Iterable, List, Optional, Tuple

DB_NAME = "trading_app.db"
_db_lock = threading.RLock()


@dataclass
class TradeRecord:
    timestamp: datetime
    strategy: str
    symbol: str
    side: str
    price: float
    size: float
    fees: float
    slippage: float
    pnl: float


def _format_timestamp(ts: Any) -> str:
    """Normalize timestamp to ISO 8601 string for consistent ordering."""
    if isinstance(ts, datetime):
        return ts.isoformat()
    return str(ts)


def _with_retries(fn, max_retries: int = 5, base_delay: float = 0.05):
    """Retry helper for transient sqlite errors (e.g. database is locked).

    The wrapped function should perform the DB operation and return a value.
    """
    for attempt in range(max_retries):
        try:
            return fn()
        except sqlite3.OperationalError as e:
            msg = str(e).lower()
            if "locked" in msg or "database is locked" in msg or "busy" in msg:
                time.sleep(base_delay * (2 ** attempt))
                continue
            raise
    # final attempt - let exceptions bubble
    return fn()


@contextmanager
def get_db(readonly: bool = False):
    """Context manager providing a fresh sqlite3.Connection.

    If readonly is False, a re-entrant lock is acquired to serialize writes.
    WAL mode is set to improve concurrency between readers and writers. The
    connection is always closed before returning to avoid cross-thread reuse.
    """
    conn = sqlite3.connect(DB_NAME, timeout=30, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")
    try:
        if readonly:
            yield conn
        else:
            with _db_lock:
                yield conn
                conn.commit()
    except Exception:
        # Only rollback when there's an active transaction / writers
        try:
            conn.rollback()
        except Exception:
            pass
        raise
    finally:
        conn.close()


def init_db() -> None:
    """Initialize database schema and indexes."""
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

        # single-column indexes and composite indexes for common queries
        c.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON trades(timestamp)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_symbol ON trades(symbol)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_strategy ON trades(strategy)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_symbol_timestamp ON trades(symbol, timestamp DESC)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_strategy_timestamp ON trades(strategy, timestamp DESC)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_pnl ON trades(pnl)')


def save_trade(trade: TradeRecord) -> None:
    """Save a single trade with retries for transient failures."""

    def _do():
        with get_db() as conn:
            c = conn.cursor()
            c.execute(
                """
                INSERT INTO trades
                (timestamp, strategy, symbol, side, price, size, fees, slippage, pnl)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    _format_timestamp(trade.timestamp),
                    trade.strategy,
                    trade.symbol,
                    trade.side,
                    float(trade.price),
                    float(trade.size),
                    float(trade.fees),
                    float(trade.slippage),
                    float(trade.pnl),
                ),
            )

    _with_retries(_do)


def save_trades_batch(trades: Iterable[TradeRecord], chunk_size: int = 5000) -> int:
    """Batch insert trades in internal chunks with retries.

    Returns the total number of inserted rows.
    """
    total_inserted = 0

    # Ensure we can iterate multiple times by consuming into small lists per chunk
    batch = []
    for tr in trades:
        batch.append(tr)
        if len(batch) >= chunk_size:
            def _do_chunk(b=batch):
                with get_db() as conn:
                    c = conn.cursor()
                    data = [
                        (
                            _format_timestamp(t.timestamp),
                            t.strategy,
                            t.symbol,
                            t.side,
                            float(t.price),
                            float(t.size),
                            float(t.fees),
                            float(t.slippage),
                            float(t.pnl),
                        )
                        for t in b
                    ]
                    c.executemany(
                        """
                        INSERT INTO trades
                        (timestamp, strategy, symbol, side, price, size, fees, slippage, pnl)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        data,
                    )
            _with_retries(_do_chunk)
            total_inserted += len(batch)
            batch = []

    # final partial batch
    if batch:
        def _do_final(b=batch):
            with get_db() as conn:
                c = conn.cursor()
                data = [
                    (
                        _format_timestamp(t.timestamp),
                        t.strategy,
                        t.symbol,
                        t.side,
                        float(t.price),
                        float(t.size),
                        float(t.fees),
                        float(t.slippage),
                        float(t.pnl),
                    )
                    for t in b
                ]
                c.executemany(
                    """
                    INSERT INTO trades
                    (timestamp, strategy, symbol, side, price, size, fees, slippage, pnl)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    data,
                )
        _with_retries(_do_final)
        total_inserted += len(batch)

    return total_inserted


def _safe_scalar_fetch(cursor) -> Optional[float]:
    row = cursor.fetchone()
    if not row:
        return None
    v = row[0]
    if v is None:
        return None
    return float(v)


def get_trades(limit: int = 100, offset: int = 0) -> List[Tuple]:
    """Get paginated trades."""
    with get_db(readonly=True) as conn:
        c = conn.cursor()
        c.execute(
            "SELECT * FROM trades ORDER BY timestamp DESC LIMIT ? OFFSET ?",
            (limit, offset),
        )
        return c.fetchall()


def get_trades_by_symbol(symbol: str, limit: int = 100, offset: int = 0) -> List[Tuple]:
    """Get paginated trades for a specific symbol."""
    with get_db(readonly=True) as conn:
        c = conn.cursor()
        c.execute(
            "SELECT * FROM trades WHERE symbol = ? ORDER BY timestamp DESC LIMIT ? OFFSET ?",
            (symbol, limit, offset),
        )
        return c.fetchall()


def get_trades_by_strategy(strategy: str, limit: int = 100, offset: int = 0) -> List[Tuple]:
    """Get paginated trades for a specific strategy."""
    with get_db(readonly=True) as conn:
        c = conn.cursor()
        c.execute(
            "SELECT * FROM trades WHERE strategy = ? ORDER BY timestamp DESC LIMIT ? OFFSET ?",
            (strategy, limit, offset),
        )
        return c.fetchall()


def get_total_pnl() -> float:
    """Get total realized P&L across all trades."""
    with get_db(readonly=True) as conn:
        c = conn.cursor()
        c.execute("SELECT SUM(pnl) FROM trades")
        total = _safe_scalar_fetch(c)
        return float(total or 0.0)


def get_pnl_by_symbol(symbol: str) -> float:
    """Get total P&L for a specific symbol."""
    with get_db(readonly=True) as conn:
        c = conn.cursor()
        c.execute("SELECT SUM(pnl) FROM trades WHERE symbol = ?", (symbol,))
        total = _safe_scalar_fetch(c)
        return float(total or 0.0)


def get_pnl_by_strategy(strategy: str) -> float:
    """Get total P&L for a specific strategy."""
    with get_db(readonly=True) as conn:
        c = conn.cursor()
        c.execute("SELECT SUM(pnl) FROM trades WHERE strategy = ?", (strategy,))
        total = _safe_scalar_fetch(c)
        return float(total or 0.0)


def get_trade_count() -> int:
    """Get total number of trades in database."""
    with get_db(readonly=True) as conn:
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM trades")
        row = c.fetchone()
        return int(row[0]) if row and row[0] is not None else 0


def close_db():
    """No-op retained for backward compatibility with the shutdown sequence."""
    return None
