import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from weasyprint import HTML

st.title("📊 My Data Dashboard")

np.random.seed(42)
data = pd.DataFrame({
    'Month': ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
    'Revenue': np.random.randint(100, 200, 6),
    'Expenses': np.random.randint(50, 100, 6)
})

col1, col2 = st.columns(2)
col1.metric("Total Revenue", f"${data['Revenue'].sum()}")
col2.metric("Total Expenses", f"${data['Expenses'].sum()}")

fig = px.line(data, x='Month', y=['Revenue', 'Expenses'], title="Financial Performance")
st.plotly_chart(fig, use_container_width=True)
