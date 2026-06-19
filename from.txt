from dataclasses import dataclass
from datetime import datetime

@dataclass
class TradeEvent:
    timestamp: datetime
    strategy: str
    symbol: str
    side: str
    price: float
    size: float
    fees: float
    slippage: float
    pnl: float
