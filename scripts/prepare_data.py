"""Prepare one compact, auditable CSV from Olist's original Kaggle ZIP."""

from __future__ import annotations

import argparse
from pathlib import Path
from zipfile import ZipFile

import pandas as pd


DATASET_URL = "https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce"
ORDER_COLUMNS = [
    "order_id",
    "customer_id",
    "order_status",
    "order_purchase_timestamp",
    "order_delivered_carrier_date",
    "order_delivered_customer_date",
    "order_estimated_delivery_date",
]
OUTPUT_COLUMNS = [
    "order_id",
    "customer_state",
    "order_status",
    "order_purchase_timestamp",
    "order_delivered_carrier_date",
    "order_delivered_customer_date",
    "order_estimated_delivery_date",
    "product_categories",
]


def prepare(zip_path: Path, output_path: Path) -> None:
    with ZipFile(zip_path) as archive:
        with archive.open("olist_orders_dataset.csv") as source:
            orders = pd.read_csv(source, usecols=ORDER_COLUMNS, dtype="string")
        with archive.open("olist_customers_dataset.csv") as source:
            customers = pd.read_csv(
                source, usecols=["customer_id", "customer_state"], dtype="string"
            )
        with archive.open("olist_order_items_dataset.csv") as source:
            items = pd.read_csv(source, usecols=["order_id", "product_id"], dtype="string")
        with archive.open("olist_products_dataset.csv") as source:
            products = pd.read_csv(
                source, usecols=["product_id", "product_category_name"], dtype="string"
            )
        with archive.open("product_category_name_translation.csv") as source:
            translations = pd.read_csv(source, dtype="string")

    if orders["order_id"].duplicated().any():
        raise ValueError("order_id is not unique in source orders")
    if customers["customer_id"].duplicated().any():
        raise ValueError("customer_id is not unique in source customers")
    if products["product_id"].duplicated().any():
        raise ValueError("product_id is not unique in source products")

    category_items = items.merge(products, on="product_id", how="left", validate="many_to_one")
    category_items = category_items.merge(
        translations, on="product_category_name", how="left", validate="many_to_one"
    )
    category_items["category"] = category_items["product_category_name_english"].fillna(
        category_items["product_category_name"]
    )
    categories = (
        category_items.groupby("order_id", as_index=False)["category"]
        .agg(lambda values: "; ".join(sorted(set(values.dropna()))))
        .rename(columns={"category": "product_categories"})
    )

    merged = orders.merge(customers, on="customer_id", how="left", validate="many_to_one")
    merged = merged.merge(categories, on="order_id", how="left", validate="one_to_one")
    if len(merged) != len(orders):
        raise ValueError("Join changed the number of orders")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    merged.loc[:, OUTPUT_COLUMNS].to_csv(output_path, index=False)
    print(f"Source: {DATASET_URL}")
    print(f"Orders: {len(orders):,}; unmatched states: {merged['customer_state'].isna().sum():,}")
    print(f"Wrote: {output_path} ({output_path.stat().st_size / 1_000_000:.2f} MB)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("zip_path", type=Path, help="Original Olist ZIP downloaded from Kaggle")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/olist_delivery_orders.csv"),
        help="Compact CSV for the app",
    )
    args = parser.parse_args()
    prepare(args.zip_path, args.output)
