from typing import List, Dict, Optional
from dataclasses import dataclass
from datetime import datetime

@dataclass
class Position:
    """Represents an open trading position."""
    symbol: str
    size: float
    entry_price: float
    entry_time: datetime
    side: str  # 'long' or 'short'

class PortfolioNAV:
    """Portfolio tracking with NAV, P&L, and drawdown calculations."""
    
    def __init__(self, starting_balance: float = 10000.0):
        self.starting_balance = starting_balance
        self.realized_pnl = 0.0
        self.open_positions: Dict[str, Position] = {}
        self.nav_history: List[tuple] = []  # (timestamp, nav)
        self.peak_nav = starting_balance
        self.peak_nav_time = datetime.utcnow()
    
    def update_trade(self, trade_pnl: float, timestamp: Optional[datetime] = None) -> float:
        """Update portfolio with realized P&L from a trade.
        
        Args:
            trade_pnl: Realized profit/loss from the trade
            timestamp: Trade timestamp (defaults to now)
            
        Returns:
            Updated NAV
        """
        if timestamp is None:
            timestamp = datetime.utcnow()
        
        self.realized_pnl += trade_pnl
        current_nav = self.current_nav()
        self.nav_history.append((timestamp, current_nav))
        
        # Update peak NAV for drawdown calculation
        if current_nav > self.peak_nav:
            self.peak_nav = current_nav
            self.peak_nav_time = timestamp
        
        return current_nav
    
    def add_position(self, position: Position) -> None:
        """Add or update an open position.
        
        Args:
            position: Position object to add
        """
        self.open_positions[position.symbol] = position
    
    def remove_position(self, symbol: str) -> Optional[Position]:
        """Close an open position.
        
        Args:
            symbol: Symbol to close
            
        Returns:
            The removed position or None if not found
        """
        return self.open_positions.pop(symbol, None)
    
    def get_position_value(self, symbol: str, current_price: float) -> float:
        """Calculate unrealized P&L for a position.
        
        Args:
            symbol: Position symbol
            current_price: Current market price
            
        Returns:
            Unrealized P&L
        """
        if symbol not in self.open_positions:
            return 0.0
        
        position = self.open_positions[symbol]
        price_diff = current_price - position.entry_price
        
        if position.side == 'long':
            return position.size * price_diff
        else:  # short
            return -position.size * price_diff
    
    def get_total_unrealized_pnl(self, price_map: Dict[str, float]) -> float:
        """Calculate total unrealized P&L across all open positions.
        
        Args:
            price_map: Dict mapping symbol -> current price
            
        Returns:
            Total unrealized P&L
        """
        total = 0.0
        for symbol, position in self.open_positions.items():
            if symbol in price_map:
                total += self.get_position_value(symbol, price_map[symbol])
        return total
    
    def current_nav(self, price_map: Optional[Dict[str, float]] = None) -> float:
        """Calculate current Net Asset Value (NAV).
        
        NAV = Starting Balance + Realized P&L + Unrealized P&L
        
        Args:
            price_map: Optional dict of current prices for unrealized P&L calculation
            
        Returns:
            Current NAV
        """
        base_nav = self.starting_balance + self.realized_pnl
        
        if price_map:
            unrealized = self.get_total_unrealized_pnl(price_map)
            return base_nav + unrealized
        
        return base_nav
    
    def get_drawdown(self, price_map: Optional[Dict[str, float]] = None) -> float:
        """Calculate current drawdown as a percentage.
        
        Drawdown = (Peak NAV - Current NAV) / Peak NAV
        
        Args:
            price_map: Optional dict of current prices
            
        Returns:
            Drawdown as a decimal (e.g., 0.15 for 15%)
        """
        current = self.current_nav(price_map)
        if self.peak_nav == 0:
            return 0.0
        return (self.peak_nav - current) / self.peak_nav
    
    def get_max_drawdown(self) -> float:
        """Calculate maximum drawdown from all historical NAV values.
        
        Returns:
            Maximum drawdown as a decimal
        """
        if not self.nav_history:
            return 0.0
        
        max_drawdown = 0.0
        peak = self.starting_balance
        
        for timestamp, nav in self.nav_history:
            if nav > peak:
                peak = nav
            drawdown = (peak - nav) / peak if peak > 0 else 0
            max_drawdown = max(max_drawdown, drawdown)
        
        return max_drawdown
    
    def get_sharpe_ratio(self, risk_free_rate: float = 0.02) -> float:
        """Estimate Sharpe ratio from historical NAV.
        
        Args:
            risk_free_rate: Annual risk-free rate (default 2%)
            
        Returns:
            Sharpe ratio (annualized)
        """
        if len(self.nav_history) < 2:
            return 0.0
        
        # Calculate daily returns
        nav_values = [nav for _, nav in self.nav_history]
        returns = []
        for i in range(1, len(nav_values)):
            ret = (nav_values[i] - nav_values[i-1]) / nav_values[i-1]
            returns.append(ret)
        
        if not returns or sum(returns) == 0:
            return 0.0
        
        # Calculate mean and std of returns
        mean_return = sum(returns) / len(returns)
        variance = sum((r - mean_return) ** 2 for r in returns) / len(returns)
        std_dev = variance ** 0.5
        
        if std_dev == 0:
            return 0.0
        
        # Annualize (assuming 252 trading days)
        daily_risk_free = risk_free_rate / 252
        sharpe = (mean_return - daily_risk_free) / std_dev * (252 ** 0.5)
        
        return sharpe
    
    def get_stats(self, price_map: Optional[Dict[str, float]] = None) -> Dict:
        """Get comprehensive portfolio statistics.
        
        Args:
            price_map: Optional dict of current prices
            
        Returns:
            Dict containing key metrics
        """
        current_nav = self.current_nav(price_map)
        return {
            'starting_balance': self.starting_balance,
            'current_nav': current_nav,
            'realized_pnl': self.realized_pnl,
            'unrealized_pnl': current_nav - self.starting_balance - self.realized_pnl,
            'total_pnl': current_nav - self.starting_balance,
            'return_pct': ((current_nav - self.starting_balance) / self.starting_balance * 100),
            'drawdown': self.get_drawdown(price_map),
            'max_drawdown': self.get_max_drawdown(),
            'sharpe_ratio': self.get_sharpe_ratio(),
            'num_open_positions': len(self.open_positions),
            'peak_nav': self.peak_nav,
            'peak_nav_time': self.peak_nav_time
        }
