"""
Simple ETL pipeline for the Revolut Growth Analytics project.

Goal:
- Read raw CSVs from data/raw/  (Extract)
- Clean and transform them into analytics-friendly tables (Transform)
- Save the result as Parquet files in data/warehouse/  (Load)

Resulting warehouse tables:
- dim_users.parquet        (user-level dimension table)
- fct_transactions.parquet (transaction-level fact table)
- fct_funnel.parquet       (funnel event fact table)
"""

from pathlib import Path

import numpy as np
import pandas as pd

# ----------------------------------------
# Setup: paths and basic config
# ----------------------------------------
# Purpose:
# - Make sure we always read/write from the correct folders
# - Avoid hard-coded absolute paths

# BASE_DIR = project root folder (one level above /etl)
BASE_DIR = Path(__file__).resolve().parents[1]

# Folder for raw CSVs (output of generate_fake_data.py)
RAW_DIR = BASE_DIR / "data" / "raw"

# Folder for warehouse tables (cleaned & modeled)
WAREHOUSE_DIR = BASE_DIR / "data" / "warehouse"
WAREHOUSE_DIR.mkdir(parents=True, exist_ok=True)


# ----------------------------------------
# Helper: load all raw CSVs
# ----------------------------------------
# Purpose:
# - Keep file loading in one place
# - Ensure date columns are parsed as real datetimes

def load_raw_data():
    """Load all raw CSVs from data/raw/ as DataFrames."""
    users = pd.read_csv(RAW_DIR / "users.csv", parse_dates=["signup_at"])

    kyc = pd.read_csv(
        RAW_DIR / "kyc.csv",
        parse_dates=["kyc_started_at", "kyc_completed_at"],
    )

    cards = pd.read_csv(
        RAW_DIR / "cards.csv",
        parse_dates=["card_activated_at"],
    )

    transactions = pd.read_csv(
        RAW_DIR / "transactions.csv",
        parse_dates=["transaction_time"],
    )

    funnel = pd.read_csv(
        RAW_DIR / "funnel_events.csv",
        parse_dates=["event_time"],
    )

    return users, kyc, cards, transactions, funnel


# ----------------------------------------
# Build dim_users
# ----------------------------------------
# Purpose:
# - Create one row per user (dimension table)
# - Combine:
#   - basic attributes (country, device, marketing_channel, signup_at)
#   - KYC info and status
#   - card activation info
#   - first transaction info
#   - derived durations between steps
#
# Pattern used for each source table (kyc, cards, transactions):
# 1. Sort by a time column (e.g. kyc_started_at, card_activated_at, transaction_time)
# 2. Group by user_id
# 3. Aggregate:
#    - use "min" for "first time"
#    - use "last" for "final status" or "latest type"
# 4. Merge the aggregated result into dim_users on user_id

def build_dim_users(users, kyc, cards, transactions, funnel):
    """Create the dim_users table with one row per user and summary metrics."""
    # Start from the users table (one row per user already)
    dim = users.copy()

    # -----------------------------
    # KYC summary per user
    # -----------------------------
    # Step 1: sort by kyc_started_at so that "min"/"last" aggregations behave predictably
    kyc_sorted = kyc.sort_values("kyc_started_at")

    # Step 2: group by user_id and aggregate
    # - "min" on a datetime column → earliest timestamp
    # - "last" on kyc_status → last value in the time order (final outcome)
    kyc_agg = (
        kyc_sorted
        .groupby("user_id", as_index=False)
        .agg(
            first_kyc_started_at=("kyc_started_at", "min"),
            first_kyc_completed_at=("kyc_completed_at", "min"),
            kyc_status=("kyc_status", "last"),
        )
    )

    # Step 3: boolean flag if user ever had KYC approved
    kyc_agg["has_kyc_approved"] = kyc_agg["kyc_status"].eq("APPROVED")

    # Step 4: merge KYC summary into dim_users
    dim = dim.merge(kyc_agg, on="user_id", how="left")

    # -----------------------------
    # Card summary per user
    # -----------------------------
    # Same pattern:
    # 1. sort by activation time
    # 2. group by user_id
    # 3. aggregate first activation time and "last" card_type
    cards_sorted = cards.sort_values("card_activated_at")

    cards_agg = (
        cards_sorted
        .groupby("user_id", as_index=False)
        .agg(
            card_activated_at=("card_activated_at", "min"),
            card_type=("card_type", "last"),
        )
    )

    # has_card_activated = True if card_activated_at is NOT null
    # .isna()  → True where value is missing
    # ~.isna() → True where value is present (tilde ~ negates the boolean Series)
    cards_agg["has_card_activated"] = ~cards_agg["card_activated_at"].isna()

    # Merge card info into dim_users
    dim = dim.merge(cards_agg, on="user_id", how="left")

    # -----------------------------
    # First top-up / transaction per user
    # -----------------------------
    # Again same pattern:
    # 1. sort by transaction_time
    # 2. group by user_id
    # 3. aggregate:
    #    - first_transaction_at → earliest (min) transaction_time
    #    - total_transactions  → count of transactions
    #    - total_amount_eur    → sum of amounts
    tx_sorted = transactions.sort_values("transaction_time")

    tx_agg = (
        tx_sorted
        .groupby("user_id", as_index=False)
        .agg(
            first_transaction_at=("transaction_time", "min"),
            total_transactions=("transaction_time", "count"),
            total_amount_eur=("amount_eur", "sum"),
        )
    )

    # has_topup = True if user has at least one transaction (first_transaction_at not null)
    tx_agg["has_topup"] = ~tx_agg["first_transaction_at"].isna()

    # Merge transaction summary into dim_users
    dim = dim.merge(tx_agg, on="user_id", how="left")

    # -----------------------------
    # Time-based metrics (durations)
    # -----------------------------
    # We compute durations in HOURS between important steps.
    # Using dt.total_seconds() gives us seconds → divide by 3600 to get hours.

    # Time from signup to first KYC completion
    dim["time_to_kyc_hours"] = (
        (dim["first_kyc_completed_at"] - dim["signup_at"])
        .dt.total_seconds()
        .div(3600)
    )

    # Time from KYC completion to card activation
    dim["time_kyc_to_card_hours"] = (
        (dim["card_activated_at"] - dim["first_kyc_completed_at"])
        .dt.total_seconds()
        .div(3600)
    )

    # Time from card activation to first transaction (approx. first top-up)
    dim["time_card_to_first_tx_hours"] = (
        (dim["first_transaction_at"] - dim["card_activated_at"])
        .dt.total_seconds()
        .div(3600)
    )

    return dim


# ----------------------------------------
# Build fct_transactions
# ----------------------------------------
# Purpose:
# - Use the raw transactions table
# - Make sure dtypes are correct
# - Add a few helper columns for analysis (date, hour)

def build_fct_transactions(transactions):
    """Create a cleaned transaction fact table."""
    fct_tx = transactions.copy()

    # Ensure amount is float
    fct_tx["amount_eur"] = fct_tx["amount_eur"].astype(float)

    # Simple time dimensions for grouping later (e.g. by day, by hour)
    fct_tx["transaction_date"] = fct_tx["transaction_time"].dt.date
    fct_tx["transaction_hour"] = fct_tx["transaction_time"].dt.hour

    return fct_tx


# ----------------------------------------
# Build fct_funnel
# ----------------------------------------
# Purpose:
# - Clean up the funnel_events table
# - Ensure ordering and types are correct
# - Use this table for funnel / conversion dashboards

def build_fct_funnel(funnel):
    """Create a cleaned funnel fact table."""
    fct_funnel = funnel.copy()

    # step_order should be an integer
    fct_funnel["step_order"] = fct_funnel["step_order"].astype(int)

    # Sort by user and step for readability and consistent analysis
    fct_funnel = fct_funnel.sort_values(
        ["user_id", "step_order", "event_time"]
    ).reset_index(drop=True)

    return fct_funnel


# ----------------------------------------
# Main ETL flow
# ----------------------------------------
# Purpose:
# - Orchestrate the full ETL process:
#   1. Load raw data
#   2. Build dim_users, fct_transactions, fct_funnel
#   3. Save them as Parquet into data/warehouse/

def run_etl():
    """Run the full ETL pipeline."""
    print("Loading raw data...")
    users, kyc, cards, transactions, funnel = load_raw_data()

    print("Building dim_users (one row per user)...")
    dim_users = build_dim_users(users, kyc, cards, transactions, funnel)

    print("Building fct_transactions (one row per transaction)...")
    fct_transactions = build_fct_transactions(transactions)

    print("Building fct_funnel (one row per funnel step per user)...")
    fct_funnel = build_fct_funnel(funnel)

    # Save as Parquet files (simulated warehouse layer)
    print("Writing Parquet files to data/warehouse/...")

    dim_users.to_parquet(WAREHOUSE_DIR / "dim_users.parquet", index=False)
    fct_transactions.to_parquet(WAREHOUSE_DIR / "fct_transactions.parquet", index=False)
    fct_funnel.to_parquet(WAREHOUSE_DIR / "fct_funnel.parquet", index=False)

    print("✅ ETL completed successfully.")
    print("📁 Warehouse directory:", WAREHOUSE_DIR)
    for file in WAREHOUSE_DIR.glob("*.parquet"):
        print(" -", file.name)


if __name__ == "__main__":
    run_etl()
