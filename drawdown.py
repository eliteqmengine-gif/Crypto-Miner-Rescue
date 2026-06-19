class PortfolioNAV:
    def __init__(self):
        self.starting_balance = 10000
        self.realized_pnl = 0
        self.open_positions = []

    def update_trade(self, pnl):
        self.realized_pnl += pnl

    def current_nav(self):
        return self.starting_balance + self.realized_pnl
