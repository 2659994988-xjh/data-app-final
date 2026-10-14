"""Order Delivery Delay Monitor — historical Olist dashboard."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from delivery_metrics import (
    ANALYSIS_END,
    ANALYSIS_START,
    analysis_orders,
    delivery_clues,
    late_rate_status,
    load_orders,
    state_rates,
    summary,
    weekly_rates,
)


DATA_PATH = Path(__file__).parent / "data" / "olist_delivery_orders.csv"
INK = "#11233f"
TEAL = "#087f79"
CORAL = "#ed6a5a"
GRID = "#e6edf1"

st.set_page_config(
    page_title="XuJinghan · Order Delivery Delay Monitor",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.html(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&display=swap');
html, body, [class*="css"], [data-testid="stApp"] {font-family: 'DM Sans',sans-serif;}
[data-testid="stApp"] {background: #f5f8fa; color: #11233f;}
.block-container {max-width: 1240px; padding-top: 2.2rem; padding-bottom: 3rem;}
[data-testid="stSidebar"] {background: #11233f;}
[data-testid="stSidebar"] h3, [data-testid="stSidebar"] h4,
[data-testid="stSidebar"] label, [data-testid="stSidebar"] p,
[data-testid="stSidebar"] [data-testid="stCaptionContainer"] {color: #edf7f7 !important;}
[data-testid="stSidebar"] [role="spinbutton"], [data-testid="stSidebar"] input {color: #11233f !important;}
.eyebrow {font-size: .74rem; font-weight: 700; letter-spacing: .16em; text-transform: uppercase; color: #087f79;}
.hero {background: linear-gradient(120deg,#11233f 0%,#174c60 72%,#087f79 100%); border-radius: 22px; padding: 28px 34px 30px; color: #fff; margin-bottom: 22px; box-shadow: 0 16px 40px rgba(17,35,63,.10);}
.hero h1 {font-size: clamp(1.65rem,3vw,2.65rem); letter-spacing: -.035em; margin: .3rem 0 .45rem; color: #fff;}
.hero p {margin: 0; max-width: 780px; color: #d9e9ec; font-size: .98rem;}
.hero .eyebrow {color: #9ee4da;}
.source-line {font-size: .82rem; color: #66758b; margin: -3px 0 22px;}
.section-kicker {color: #087f79; font-size: .72rem; letter-spacing: .12em; text-transform: uppercase; font-weight: 700; margin-top: 16px;}
.section-title {font-size: 1.33rem; font-weight: 700; color: #11233f; margin: 2px 0 6px;}
.section-subtitle {font-size: .88rem; color: #66758b; margin-bottom: 12px;}
[data-testid="stMetric"] {background: #fff; border: 1px solid #e5edf0; border-radius: 18px; padding: 19px 20px; box-shadow: 0 5px 20px rgba(22,48,67,.045);}
[data-testid="stMetricLabel"] {color: #66758b; font-size: .91rem;}
[data-testid="stMetricValue"] {color: #11233f; font-size: 2rem; font-weight: 700;}
.insight {background: #e9f5f2; border-left: 4px solid #087f79; border-radius: 0 12px 12px 0; padding: 12px 16px; color: #193d48; font-size: .91rem; margin: 11px 0 16px;}
.footnote {font-size: .79rem; color: #66758b; line-height: 1.5;}
.rate-status {display: inline-flex; align-items: center; gap: .45rem; margin-top: .55rem; padding: .4rem .72rem; border-radius: 999px; font-size: .83rem; font-weight: 700;}
.rate-status.good {background: #e5f5ef; color: #086b52;}
.rate-status.warning {background: #fff1d8; color: #965600;}
.rate-status.danger {background: #fde8e6; color: #bd2c2c;}
[data-testid="stColumn"]:has(.rate-status.danger) [data-testid="stMetricValue"] {color: #bd2c2c;}
.threshold-note {font-size: .78rem; color: #66758b; margin: .38rem 0 0;}
</style>
""",
)


@st.cache_data(show_spinner=False)
def get_data() -> pd.DataFrame:
    return analysis_orders(load_orders(DATA_PATH))


try:
    all_orders = get_data()
except (FileNotFoundError, ValueError) as exc:
    st.error(f"Could not load order data: {exc}")
    st.stop()

with st.sidebar:
    st.markdown("### ORDER DELIVERY DELAY")
    st.caption("Historical operations review")
    st.divider()
    st.markdown("#### Review scope")
    selected_dates = st.date_input(
        "Promised delivery dates",
        value=(ANALYSIS_START.date(), ANALYSIS_END.date()),
        min_value=ANALYSIS_START.date(),
        max_value=ANALYSIS_END.date(),
        help="Orders are grouped by promised delivery date, not actual delivery date.",
    )
    states = sorted(all_orders["customer_state"].dropna().unique().tolist())
    selected_state = st.selectbox(
        "Destination state",
        options=["All states", *states],
        help="The destination helps prioritize investigation; it does not identify the cause of a delay.",
    )
    st.divider()
    st.caption("Public historical Olist snapshot; current in-transit orders are not shown.")

if not isinstance(selected_dates, tuple) or len(selected_dates) != 2:
    st.info("Select both a start and an end date.")
    st.stop()

start_date, end_date = selected_dates
if start_date > end_date:
    st.warning("The start date must be on or before the end date.")
    st.stop()

filtered = all_orders.loc[
    all_orders["promise_date"].between(pd.Timestamp(start_date), pd.Timestamp(end_date))
    & (all_orders["customer_state"].eq(selected_state) if selected_state != "All states" else True)
].copy()

st.html(
    """
<div class="hero">
  <div class="eyebrow">XUJINGHAN · OLIST</div>
  <h1>Order Delivery Delay Monitor</h1>
  <p>For Olist logistics operations managers: track weekly delivery reliability and identify destination states to investigate first.</p>
</div>
""",
)
st.html(
    "<div class='source-line'>Source: Olist / Kaggle historical snapshot · Analysis window: Mar 2017–Aug 2018 · "
    "A production version would refresh nightly for a Monday review; this demo does not update automatically.</div>",
)

if filtered.empty:
    st.warning("No eligible delivered orders match these filters. Widen the date range or choose another state.")
    st.stop()

metrics = summary(filtered)
status_label, status_band, status_tone = late_rate_status(metrics["late_rate"])
st.html('<div class="section-kicker">01 / Key metrics</div>')
columns = st.columns(3, gap="medium")
with columns[0]:
    st.metric("Late delivery rate", f"{metrics['late_rate']:.1%}", help="Late delivered orders ÷ delivered orders with valid promised and actual dates", border=True)
    st.html(
        f'<div class="rate-status {status_tone}" role="status">'
        f'Selected period: {status_label} · {status_band}</div>'
        '<div class="threshold-note">Proposed bands: &lt;5% low · 5%–15% attention · &gt;15% high risk</div>'
    )
with columns[1]:
    st.metric("Late orders", f"{metrics['late_orders']:,}", help="Actual delivery date was after the promised delivery date", border=True)
with columns[2]:
    st.metric("Median days late", f"{metrics['median_late_days']:.0f} days", help="Calculated for late orders only; less sensitive to extreme delays than a mean", border=True)

weekly = weekly_rates(filtered)
regions = state_rates(filtered, minimum_orders=200).head(8)
if not regions.empty:
    leading = regions.iloc[0]
    st.html(
        f"<div class='insight'><b>Investigation lead:</b> {leading['customer_state']} had "
        f"<b>{int(leading['late_orders']):,}</b> late orders ({leading['late_rate']:.1%}) in the selected period. "
        "Check fulfillment and carrier records first; a state difference alone does not establish cause.</div>",
    )

st.html('<div class="section-kicker">02 / Find the change</div>')
st.html('<div class="section-title">When did performance worsen, and where?</div>')
st.html('<div class="section-subtitle">Each trend point represents one promised-delivery week. The date axis uses monthly tick labels for readability; states are ranked by late-order count.</div>')

left, right = st.columns([1.35, 1], gap="large")
with left:
    st.markdown("**Weekly late delivery rate · one point per week**")
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=weekly["week"],
            y=weekly["late_rate"] * 100,
            mode="lines+markers",
            line=dict(color=TEAL, width=3),
            marker=dict(size=5, color=TEAL),
            customdata=weekly[["late_orders", "orders"]].to_numpy(),
            hovertemplate="Promised week starts: %{x|%Y-%m-%d}<br>Late rate: %{y:.1f}%<br>Late: %{customdata[0]:,} / %{customdata[1]:,} orders<extra></extra>",
        )
    )
    fig.update_layout(
        height=345,
        margin=dict(l=8, r=12, t=14, b=6),
        paper_bgcolor="#ffffff",
        plot_bgcolor="#ffffff",
        showlegend=False,
        font=dict(family="DM Sans", color=INK, size=12),
        xaxis=dict(title="Promised delivery week (monthly date ticks)", showgrid=False, tickformat="%Y-%m", tickangle=-35),
        yaxis=dict(title="Late rate (%)", ticksuffix="%", gridcolor=GRID, zeroline=False, rangemode="tozero"),
        hoverlabel=dict(bgcolor=INK, font_color="#fff"),
    )
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False}, alt="Weekly late delivery rate trend")

with right:
    st.markdown("**Destination states with the most late orders**")
    if regions.empty:
        st.info("Each state has fewer than 200 eligible orders in this selection, so states are not compared.")
    else:
        plot_regions = regions.iloc[::-1]
        fig = go.Figure(
            go.Bar(
                x=plot_regions["late_orders"],
                y=plot_regions["customer_state"],
                orientation="h",
                marker=dict(color=CORAL, line=dict(width=0)),
                customdata=plot_regions[["late_rate", "orders"]].to_numpy(),
                hovertemplate="%{y}<br>Late orders: %{x:,}<br>Late rate: %{customdata[0]:.1%}<br>Eligible orders: %{customdata[1]:,}<extra></extra>",
            )
        )
        fig.update_layout(
            height=345,
            margin=dict(l=8, r=12, t=14, b=6),
            paper_bgcolor="#ffffff",
            plot_bgcolor="#ffffff",
            showlegend=False,
            font=dict(family="DM Sans", color=INK, size=12),
            xaxis=dict(title="Late orders", gridcolor=GRID, zeroline=False),
            yaxis=dict(showgrid=False),
            hoverlabel=dict(bgcolor=INK, font_color="#fff"),
        )
        st.plotly_chart(fig, width="stretch", config={"displayModeBar": False}, alt="Destination states ranked by late-order count")

st.html('<div class="section-kicker">03 / Investigation clues</div>')
st.html('<div class="section-title">Late orders: handoff timing and product categories</div>')
st.html('<div class="section-subtitle">The 20 most delayed orders show observable dates and categories; the table does not assign responsibility.</div>')
late_detail = (
    delivery_clues(filtered).loc[:, [
        "order_id",
        "customer_state",
        "product_categories",
        "promise_date",
        "handoff_date",
        "delivered_date",
        "late_days",
        "handoff_to_delivery_days",
        "handoff_clue",
    ]]
    .sort_values("late_days", ascending=False)
    .head(20)
    .rename(columns={
        "order_id": "Order ID",
        "customer_state": "Destination state",
        "product_categories": "Product categories",
        "promise_date": "Promised date",
        "handoff_date": "Carrier handoff",
        "delivered_date": "Delivered date",
        "late_days": "Days late",
        "handoff_to_delivery_days": "Days after handoff",
        "handoff_clue": "Handoff timing clue",
    })
)
late_detail["Product categories"] = late_detail["Product categories"].fillna("Not recorded")
st.dataframe(
    late_detail,
    hide_index=True,
    width="stretch",
    alt="Twenty most delayed orders with carrier handoff timing and product categories",
    column_config={
        "Promised date": st.column_config.DateColumn(format="YYYY-MM-DD"),
        "Carrier handoff": st.column_config.DateColumn(format="YYYY-MM-DD"),
        "Delivered date": st.column_config.DateColumn(format="YYYY-MM-DD"),
        "Days late": st.column_config.NumberColumn(format="%d days"),
        "Days after handoff": st.column_config.NumberColumn(format="%d days"),
    },
)
st.html(
    "<div class='footnote'><b>How to read the table:</b> Handoff after the promised date shows the promise was already missed before carrier handoff; it does not prove a warehouse fault. "
    "Handoff by the promised date followed by late delivery warrants checking the downstream journey, but does not prove carrier fault. "
    "Product categories are associations, and an order may contain several. The public data has no warehouse or carrier company ID, so responsibility cannot be assigned reliably. "
    "Days after handoff uses calendar dates; unusual timestamps should be checked against source records.</div>"
)
st.html(
    "<div class='footnote'>Definition: only orders marked delivered with valid promised and actual delivery dates are included. "
    "Dates are compared by calendar day, so delivery on the promised date is on time. Destination state only helps prioritize investigation. "
    "Sparse early 2016 and late 2018 promise months are excluded from the default analysis window.</div>",
)
