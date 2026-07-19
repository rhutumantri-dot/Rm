"""A starter Streamlit application.

Run locally with:
    pip install -r requirements.txt
    streamlit run app.py
    # open http://localhost:8501
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Streamlit Starter",
    page_icon="🚀",
    layout="wide",
)


def make_sample_data(rows: int, seed: int) -> pd.DataFrame:
    """Generate a small reproducible sample dataset."""
    rng = np.random.default_rng(seed)
    dates = pd.date_range(end=pd.Timestamp.today().normalize(), periods=rows)
    return pd.DataFrame(
        {
            "date": dates,
            "revenue": rng.integers(100, 1000, size=rows),
            "users": rng.integers(10, 200, size=rows),
            "region": rng.choice(["North", "South", "East", "West"], size=rows),
        }
    )


def main() -> None:
    st.title("🚀 Streamlit Starter App")
    st.caption("A minimal, working scaffold — edit `app.py` to build your app.")

    with st.sidebar:
        st.header("Controls")
        rows = st.slider("Rows of sample data", min_value=10, max_value=365, value=90)
        seed = st.number_input("Random seed", min_value=0, value=42, step=1)
        region = st.selectbox("Filter region", ["All", "North", "South", "East", "West"])

    data = make_sample_data(rows, int(seed))
    if region != "All":
        data = data[data["region"] == region]

    col1, col2, col3 = st.columns(3)
    col1.metric("Total revenue", f"${data['revenue'].sum():,}")
    col2.metric("Total users", f"{data['users'].sum():,}")
    col3.metric("Avg daily revenue", f"${data['revenue'].mean():,.0f}")

    st.subheader("Revenue over time")
    st.line_chart(data.set_index("date")[["revenue", "users"]])

    st.subheader("Data")
    st.dataframe(data, use_container_width=True)

    st.download_button(
        "Download CSV",
        data.to_csv(index=False).encode("utf-8"),
        file_name="sample_data.csv",
        mime="text/csv",
    )


if __name__ == "__main__":
    main()
