"""Integration tests for the optimized database and event logger."""

import asyncio
import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import audit.ledger as ledger
import events
from models import TradeEvent


class PerformanceIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = str(Path(self.temp_dir.name) / "trades.sqlite3")
        self.log_path = Path(self.temp_dir.name) / "risk_events.jsonl"
        ledger.close_db()
        self.db_patch = patch.object(ledger, "DB_NAME", self.db_path)
        self.log_patch = patch.object(events, "RISK_LOG", str(self.log_path))
        self.db_patch.start()
        self.log_patch.start()
        ledger.init_db()

    def tearDown(self):
        ledger.close_db()
        self.log_patch.stop()
        self.db_patch.stop()
        self.temp_dir.cleanup()

    def make_trade(self, pnl: float, symbol: str = "BTCUSD") -> TradeEvent:
        return TradeEvent(
            timestamp=datetime(2026, 1, 1),
            strategy="test",
            symbol=symbol,
            side="buy",
            price=100.0,
            size=1.0,
            fees=0.1,
            slippage=0.01,
            pnl=pnl,
        )

    def test_batch_insert_pagination_and_aggregates(self):
        trades = [self.make_trade(10.0), self.make_trade(-2.5, "ETHUSD")]

        self.assertEqual(ledger.save_trades_batch(trades), 2)
        self.assertEqual(ledger.get_trade_count(), 2)
        self.assertEqual(ledger.get_total_pnl(), 7.5)
        self.assertEqual(len(ledger.get_trades(limit=1)), 1)
        self.assertEqual(ledger.get_pnl_by_symbol("BTCUSD"), 10.0)
        self.assertEqual(ledger.get_pnl_by_strategy("test"), 7.5)

    def test_indexes_are_created(self):
        with ledger.get_db() as conn:
            indexes = {
                row[1]
                for row in conn.execute(
                    "SELECT type, name FROM sqlite_master "
                    "WHERE type = 'index' AND tbl_name = 'trades'"
                )
            }
        self.assertTrue({"idx_timestamp", "idx_symbol", "idx_strategy", "idx_pnl"}.issubset(indexes))

    def test_async_event_logger_flushes_events(self):
        async def scenario():
            await events.init_event_logger()
            await events.log_risk_event("test_alert", "WARNING", {"value": 42})
            # Let the worker consume the queued event before shutdown.
            await asyncio.sleep(0.01)
            await events.shutdown_event_logger()

        asyncio.run(scenario())

        with self.log_path.open() as file:
            records = [json.loads(line) for line in file if line.strip()]
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["type"], "test_alert")
        self.assertEqual(records[0]["details"]["value"], 42)


if __name__ == "__main__":
    unittest.main()
