"""
Generate synthetic banking data for the Revolut Growth Analytics project.

Creates 5 CSVs:
- users.csv
- kyc.csv
- cards.csv
- transactions.csv
- funnel_events.csv

Stored in: data/raw/
"""

from datetime import datetime, timedelta
from pathlib import Path
import random

import numpy as np
import pandas as pd
from faker import Faker

# ----------------------------------------
# Setup paths and random seeds
# ----------------------------------------
# Purpose:
# - Ensure data ends up in the correct folder
# - Make results reproducible for debugging / consistency

BASE_DIR = Path(__file__).resolve().parents[1]
RAW_DIR = BASE_DIR / "data" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

fake = Faker()
Faker.seed(42)
np.random.seed(42)
random.seed(42)

# ----------------------------------------
# 1. Users table
# ----------------------------------------
# Purpose:
# - Create basic user profiles
# - Simulate signup times, device types, marketing channels, countries
# - Acts as the main dimension table

N_USERS = 2000

countries = ["AT", "DE", "UK", "FR", "ES", "IT"]
devices = ["iOS", "Android", "Web"]
channels = ["Organic", "Paid Search", "Referral", "Social", "Influencer"]

signup_start = datetime(2024, 1, 1)
signup_end = datetime(2024, 12, 31)
days_range = (signup_end - signup_start).days

users = []

for user_id in range(1, N_USERS + 1):
    # random signup timestamp
    signup_date = signup_start + timedelta(
        days=random.randint(0, days_range),
        seconds=random.randint(0, 24 * 3600),
    )
    
    users.append({
        "user_id": user_id,
        "signup_at": signup_date,
        "country": random.choice(countries),
        "device": random.choice(devices),
        "marketing_channel": random.choice(channels)
    })

users_df = pd.DataFrame(users)

# ----------------------------------------
# 2. KYC + Funnel steps
# ----------------------------------------
# Purpose:
# - Simulate the user journey from signup → registration → KYC
# - This is important for funnel analytics dashboards
# Notes:
# - Not every user completes the next step (drop-off simulation)
# - KYC status is not always APPROVED (adds realism)

kyc_rows = []
funnel_rows = []

for _, user in users_df.iterrows():
    uid = user["user_id"]
    signup_at = user["signup_at"]

    # Funnel step: viewed signup page
    funnel_rows.append({
        "user_id": uid,
        "step_order": 1,
        "step_name": "VIEWED_SIGNUP",
        "event_time": signup_at
    })

    # ~95% start registration
    if random.random() < 0.95:
        start_reg_at = signup_at + timedelta(minutes=random.randint(1, 60))
        funnel_rows.append({
            "user_id": uid,
            "step_order": 2,
            "step_name": "STARTED_REGISTRATION",
            "event_time": start_reg_at
        })
    else:
        continue  # user dropped out early

    # ~85% proceed to KYC
    if random.random() < 0.85:
        kyc_start = start_reg_at + timedelta(minutes=random.randint(5, 120))
        kyc_duration = random.randint(2, 60)
        kyc_end = kyc_start + timedelta(minutes=kyc_duration)

        # decide KYC outcome
        r = random.random()
        if r < 0.75:
            status = "APPROVED"
        elif r < 0.90:
            status = "FAILED"
        else:
            status = "PENDING"

        kyc_rows.append({
            "user_id": uid,
            "kyc_started_at": kyc_start,
            "kyc_completed_at": kyc_end,
            "kyc_status": status
        })

        # funnel step
        funnel_rows.append({
            "user_id": uid,
            "step_order": 3,
            "step_name": "KYC_COMPLETED",
            "event_time": kyc_end
        })

# ----------------------------------------
# 3. Cards table
# ----------------------------------------
# Purpose:
# - Only APPROVED KYC users can get a card
# - ~80% activate one (simulating real drop-off after approval)
# - Important for conversion rate analytics

cards = []

for kyc in kyc_rows:
    if kyc["kyc_status"] != "APPROVED":
        continue  # no card for non-approved users

    if random.random() < 0.8:  # 80% card activation rate
        activated_at = kyc["kyc_completed_at"] + timedelta(
            days=random.randint(0, 7),
            minutes=random.randint(10, 180)
        )
        
        cards.append({
            "user_id": kyc["user_id"],
            "card_activated_at": activated_at,
            "card_type": random.choice(["Virtual", "Physical"])
        })

        funnel_rows.append({
            "user_id": kyc["user_id"],
            "step_order": 4,
            "step_name": "CARD_ACTIVATED",
            "event_time": activated_at
        })

cards_df = pd.DataFrame(cards)

# ----------------------------------------
# 4. Transactions table
# ----------------------------------------
# Purpose:
# - After card activation → simulate spending behaviour
# - Users can make multiple transactions
# - Amounts follow a lognormal distribution (more realistic)

transactions = []

categories = [
    "Groceries",
    "Restaurants",
    "Transport",
    "Online Shopping",
    "Travel",
    "Subscriptions"
]

for card in cards:
    uid = card["user_id"]
    
    # simulate first top-up
    first_topup = card["card_activated_at"] + timedelta(
        hours=random.randint(1, 72)
    )

    # ~70% make a top-up + transactions
    if random.random() < 0.7:

        # funnel step
        funnel_rows.append({
            "user_id": uid,
            "step_order": 5,
            "step_name": "FIRST_TOPUP",
            "event_time": first_topup
        })

        # simulate 1–20 transactions
        n_tx = random.randint(1, 20)

        for _ in range(n_tx):
            tx_time = first_topup + timedelta(
                days=random.randint(0, 90),
                minutes=random.randint(0, 24 * 60)
            )

            # lognormal amount ~ realistic 5–80€
            amount = round(np.random.lognormal(mean=3.0, sigma=0.6), 2)

            transactions.append({
                "user_id": uid,
                "transaction_time": tx_time,
                "amount_eur": amount,
                "category": random.choice(categories),
                "merchant_country": random.choice(countries),
                "transaction_type": random.choice([
                    "CARD_PAYMENT", "ATM_WITHDRAWAL", "TRANSFER"
                ])
            })

transactions_df = pd.DataFrame(transactions)

# ----------------------------------------
# 5. Funnel events table
# ----------------------------------------
# Purpose:
# - Central table for funnel dashboards
# - Contains: user_id, step order, step name, timestamp

funnel_df = pd.DataFrame(funnel_rows)

# ----------------------------------------
# 6. Save as CSV in data/raw/
# ----------------------------------------
users_df.to_csv(RAW_DIR / "users.csv", index=False)
pd.DataFrame(kyc_rows).to_csv(RAW_DIR / "kyc.csv", index=False)
cards_df.to_csv(RAW_DIR / "cards.csv", index=False)
transactions_df.to_csv(RAW_DIR / "transactions.csv", index=False)
funnel_df.to_csv(RAW_DIR / "funnel_events.csv", index=False)

print("Fake banking data generated!")
print("Saved to:", RAW_DIR)
for file in RAW_DIR.glob("*.csv"):
    print(" -", file.name)
