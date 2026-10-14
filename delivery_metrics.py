"""Shared, testable definitions for the Olist delivery dashboard."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


DATE_COLUMNS = (
    "order_purchase_timestamp",
    "order_delivered_carrier_date",
    "order_delivered_customer_date",
    "order_estimated_delivery_date",
)
ANALYSIS_START = pd.Timestamp("2017-03-01")
ANALYSIS_END = pd.Timestamp("2018-08-31")


def load_orders(path: str | Path) -> pd.DataFrame:
    """Read the compact CSV and derive outcomes at one-row-per-order grain."""
    df = pd.read_csv(path, dtype={"order_id": "string", "customer_state": "string"})
    if df["order_id"].duplicated().any():
        raise ValueError("Each order_id must appear once")
    for column in DATE_COLUMNS:
        df[column] = pd.to_datetime(df[column], errors="coerce")

    df["promise_date"] = df["order_estimated_delivery_date"].dt.normalize()
    df["delivered_date"] = df["order_delivered_customer_date"].dt.normalize()
    df["eligible"] = (
        df["order_status"].eq("delivered")
        & df["promise_date"].notna()
        & df["delivered_date"].notna()
    )
    df["late_days"] = (df["delivered_date"] - df["promise_date"]).dt.days
    df["is_late"] = df["eligible"] & df["late_days"].gt(0)
    return df


def analysis_orders(df: pd.DataFrame) -> pd.DataFrame:
    """Use complete historical promise months and observed delivered orders."""
    return df.loc[
        df["eligible"] & df["promise_date"].between(ANALYSIS_START, ANALYSIS_END)
    ].copy()


def summary(df: pd.DataFrame) -> dict[str, float | int]:
    n = len(df)
    late = df.loc[df["is_late"]]
    return {
        "orders": n,
        "late_orders": len(late),
        "late_rate": len(late) / n if n else 0.0,
        "median_late_days": float(late["late_days"].median()) if len(late) else 0.0,
    }


def late_rate_status(rate: float) -> tuple[str, str, str]:
    """Proposed review bands for the selected historical cohort, not an Olist SLA."""
    if rate > 0.15:
        return "High risk", "> 15%", "danger"
    if rate >= 0.05:
        return "Needs attention", "5%–15%", "warning"
    return "Low", "< 5%", "good"


def weekly_rates(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["week", "orders", "late_orders", "late_rate"])
    grouped = (
        df.assign(week=df["promise_date"].dt.to_period("W-SUN").dt.start_time)
        .groupby("week", as_index=False)
        .agg(orders=("order_id", "size"), late_orders=("is_late", "sum"))
    )
    grouped["late_rate"] = grouped["late_orders"] / grouped["orders"]
    return grouped


def state_rates(df: pd.DataFrame, minimum_orders: int = 200) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["customer_state", "orders", "late_orders", "late_rate"])
    grouped = (
        df.groupby("customer_state", as_index=False)
        .agg(orders=("order_id", "size"), late_orders=("is_late", "sum"))
    )
    grouped = grouped.loc[grouped["orders"] >= minimum_orders].copy()
    grouped["late_rate"] = grouped["late_orders"] / grouped["orders"]
    return grouped.sort_values(["late_orders", "late_rate"], ascending=False)


def delivery_clues(df: pd.DataFrame) -> pd.DataFrame:
    """Label observable handoff timing, without assigning a cause or carrier."""
    late = df.loc[df["is_late"]].copy()
    handoff = late["order_delivered_carrier_date"].dt.normalize()
    late["handoff_date"] = handoff
    late["handoff_to_delivery_days"] = (late["delivered_date"] - handoff).dt.days
    late["handoff_clue"] = "Handed off by promised date"
    late.loc[handoff.isna(), "handoff_clue"] = "Handoff date missing"
    late.loc[handoff.gt(late["promise_date"]), "handoff_clue"] = "Handed off after promised date"
    return late
