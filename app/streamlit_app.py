"""FORESIGHT interactive dashboard. Run with: streamlit run app/streamlit_app.py"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.forecast import forecast_next_days, train_forecast_model
from src.pipeline import clean_sales_data, create_demo_sales, read_sales_file
from src.risk import recommendations, score_inventory_risk

@st.cache_data(show_spinner=False)
def load_demo() -> pd.DataFrame:
    source = ROOT / "data" / "raw" / "demo_sales.csv"
    return create_demo_sales(source) if not source.exists() else read_sales_file(source)

def run_pipeline(raw: pd.DataFrame):
    clean = clean_sales_data(raw)
    (ROOT / "data" / "processed").mkdir(parents=True, exist_ok=True)
    clean.to_csv(ROOT / "data" / "processed" / "sales_clean.csv", index=False)
    _, accuracy = train_forecast_model(clean, ROOT / "model.pkl")
    forecasts = forecast_next_days(clean, ROOT / "model.pkl", horizon=30)
    risks = score_inventory_risk(forecasts)
    return clean, forecasts, risks, accuracy

def main():
    st.set_page_config(page_title="FORESIGHT", page_icon="🔭", layout="wide")

    st.title("FORESIGHT")
    st.caption("AI-powered demand forecasting and inventory intelligence for SKU-level planning.")

    if st.session_state.get("logged_in"):
        with st.sidebar:
            st.header("Data pipeline")
            uploaded = st.file_uploader("Upload sales data", type=["csv", "xlsx", "xls"], help="Required: date, sku, product, quantity_sold, current_stock")
            use_demo = st.checkbox("Use demo supermarket data", value=uploaded is None)
            st.divider()
            st.write("**Workflow**")
            st.caption("1. Ingest data\n\n2. Clean & engineer features\n\n3. Train demand model\n\n4. Score inventory risk\n\n5. Recommend action")
    else:
        uploaded = None
        use_demo = True

    try:
        if uploaded is not None and not use_demo:
            suffix = Path(uploaded.name).suffix
            temp = ROOT / "data" / "raw" / f"uploaded{suffix}"
            temp.write_bytes(uploaded.getbuffer())
            raw_data = read_sales_file(temp)
        else:
            raw_data = load_demo()
        with st.spinner("Cleaning data, training model, and calculating risks..."):
            clean, forecast, risks, accuracy = run_pipeline(raw_data)
    except Exception as exc:
        st.error(f"Unable to process the sales file: {exc}")
        st.stop()

    stockouts = risks[risks["risk"] == "Stockout"]
    overstock = risks[risks["risk"] == "Overstock"]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Forecasted demand", f"{int(forecast.predicted_demand.sum()):,}", "Next 30 days")
    c2.metric("Active SKUs", risks.sku.nunique())
    c3.metric("Stockout risks", len(stockouts), "Needs reorder", delta_color="inverse")
    c4.metric("Model accuracy", f"{accuracy:.1%}", "Holdout MAPE")

    st.subheader("Demand forecast")
    selected_skus = st.multiselect("SKUs", sorted(forecast.sku.unique()), default=sorted(forecast.sku.unique())[:3])
    display = forecast[forecast.sku.isin(selected_skus)] if selected_skus else forecast
    fig = px.line(display, x="date", y="predicted_demand", color="product", markers=True, labels={"predicted_demand": "Forecast units", "date": "Date"})
    fig.update_layout(height=360, legend_title_text="SKU")
    st.plotly_chart(fig, use_container_width=True)

    left, right = st.columns([1.25, 1])
    with left:
        st.subheader("Inventory risk register")
        st.dataframe(risks[["sku", "product", "risk", "priority", "current_stock", "forecast_units", "days_of_cover"]].style.format({"days_of_cover": "{:.1f}"}), use_container_width=True, hide_index=True)
    with right:
        st.subheader("Recommended actions")
        action_df = recommendations(risks)
        for _, row in action_df[action_df.risk != "Healthy"].iterrows():
            st.warning(f"**{row['product']}** - {row['recommendation']}\n\n{row['risk']} risk | {row['days_of_cover']:.1f} days cover | Recommended order: {row['recommended_order']} units")

    with st.expander("Data quality & model details"):
        a, b, c = st.columns(3)
        a.metric("Raw records", len(raw_data)); b.metric("Usable records", len(clean)); c.metric("Forecast horizon", "30 days")
        st.caption("Features: day of week, month, weekend, holiday, seasonality, 7-day lag and rolling average. Model: Random Forest Regressor.")

if __name__ == "__main__":
    main()
