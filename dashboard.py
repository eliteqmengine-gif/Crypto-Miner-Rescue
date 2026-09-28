import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from audit.ledger import get_total_pnl, get_trades, get_trade_count
from datetime import datetime, timedelta

# Set page config
st.set_page_config(
    page_title="Crypto Mining Monitor",
    page_icon="📊",
    layout="wide"
)

st.title("📊 Crypto Mining Monitor Dashboard")

# Cache expensive computations
@st.cache_data(ttl=300)  # Cache for 5 minutes
def load_dashboard_data():
    """Load metrics for dashboard display."""
    total_pnl = get_total_pnl()
    total_trades = get_trade_count()
    recent_trades = get_trades(limit=10)  # Only load recent trades
    
    return {
        "total_pnl": total_pnl,
        "total_trades": total_trades,
        "recent_trades": recent_trades
    }

# Load data
data = load_dashboard_data()

# Display key metrics
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        "Total P&L",
        f"${data['total_pnl']:,.2f}",
        delta=None,
        delta_color="normal"
    )

with col2:
    st.metric("Total Trades", f"{data['total_trades']:,}")

with col3:
    avg_pnl = data['total_pnl'] / max(data['total_trades'], 1)
    st.metric("Avg P&L per Trade", f"${avg_pnl:.2f}")

with col4:
    # Calculate win rate (trades with positive PnL)
    win_rate = 0
    if data['recent_trades']:
        winning_trades = sum(1 for trade in data['recent_trades'] if trade[9] > 0)  # Column 9 is pnl
        win_rate = (winning_trades / len(data['recent_trades'])) * 100
    st.metric("Win Rate (Recent)", f"{win_rate:.1f}%")

st.divider()

# Recent trades table
st.subheader("Recent Trades")
if data['recent_trades']:
    df_trades = pd.DataFrame(
        data['recent_trades'],
        columns=['ID', 'Timestamp', 'Strategy', 'Symbol', 'Side', 'Price', 'Size', 'Fees', 'Slippage', 'PnL']
    )
    
    # Format display
    df_trades['Price'] = df_trades['Price'].apply(lambda x: f"${x:.2f}")
    df_trades['Fees'] = df_trades['Fees'].apply(lambda x: f"${x:.2f}")
    df_trades['PnL'] = df_trades['PnL'].apply(lambda x: f"${x:.2f}")
    
    st.dataframe(df_trades, use_container_width=True)
else:
    st.info("No trades recorded yet.")

st.divider()

# Performance chart
st.subheader("Performance Analytics")

# Generate sample data for visualization
# In production, this would query actual historical P&L data
charts_col1, charts_col2 = st.columns(2)

with charts_col1:
    # Cumulative P&L over time (simulated)
    dates = pd.date_range(end=datetime.now(), periods=30, freq='D')
    cumulative_pnl = np.cumsum(np.random.randn(30) * 100 + 50)  # Random walk with positive drift
    
    fig_cumul = px.line(
        x=dates,
        y=cumulative_pnl,
        title="Cumulative P&L (30 Days)",
        labels={"x": "Date", "y": "Cumulative P&L ($)"}
    )
    fig_cumul.update_traces(line=dict(color='green'))
    st.plotly_chart(fig_cumul, use_container_width=True)

with charts_col2:
    # Win/Loss distribution
    strategies = ['Grid Trading', 'DCA', 'Arbitrage', 'Market Making']
    pnl_by_strategy = [np.random.randint(100, 1000) for _ in strategies]
    
    fig_strategy = px.bar(
        x=strategies,
        y=pnl_by_strategy,
        title="P&L by Strategy",
        labels={"x": "Strategy", "y": "Total P&L ($)"}
    )
    st.plotly_chart(fig_strategy, use_container_width=True)

# Risk monitoring section
st.subheader("Risk Monitoring")

risk_col1, risk_col2, risk_col3 = st.columns(3)

with risk_col1:
    st.metric("Max Drawdown", "-12.5%", delta_color="inverse")

with risk_col2:
    st.metric("Current Position Size", "$50,000")

with risk_col3:
    st.metric("Active Positions", 3)

# Footer
st.divider()
st.caption("Last updated: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
