# Revolut Growth Analytics


This project is my first hands-on experience with building a full analytics engineering workflow.  
I created it specifically as part of my application for a **Data / Analytics Engineering Internship at Revolut**.

My goal was to learn and demonstrate how core components of Revolut’s data stack may work in practice:
- **ETL development** in Python  
- **data cleaning & transformation**  
- **analytics engineering** (LookML)  
- **funnel & growth analytics**  
- **dashboard creation** for decision-making  

Although I am new to ETL pipelines and LookML, I wanted to challenge myself, explore these technologies independently, and show that I can quickly learn and apply new tools.

This repository documents the entire journey from raw synthetic banking data → ETL pipeline → data models → dashboards.  
Each step is explained in a clear, notes-style format to reflect my learning process and thought structure.

---

# 📌 **Project Steps (Overview)**

The project follows a real-world analytics engineering workflow:

1. **Synthetic Data Generation**  
   Create realistic Revolut-style banking data (users, KYC, card activation, transactions, funnel steps).

2. **ETL Pipeline (Python)**  
   Clean, transform, and enrich the raw data.  
   Produce warehouse-ready tables in Parquet format.

3. **Data Modeling (LookML)**  
   Define dimensions, measures, views, and explores for analytics use cases.

4. **Dashboards (Looker)**  
   Build funnel dashboards, growth dashboards, and revenue/transaction insights.

5. **(Optional) Airflow DAG**  
   Wrap the ETL pipeline in a scheduled workflow.

Each step has its own documentation section below.

---

# 🧬 **Step 1 — Synthetic Data Generation**

### **Purpose**
To create a realistic dataset that simulates key parts of a digital banking user journey:
- User sign-up  
- KYC verification  
- Card activation  
- First top-up  
- Realistic spending patterns  
- Funnel step tracking

This ensures we can later perform product analytics and build dashboards without relying on sensitive real banking data.

### **Output Files**
Generated and saved to: data/raw/


| File | Description |
|------|-------------|
| `users.csv` | Basic user profile (signup timestamp, device, country, marketing channel) |
| `kyc.csv` | Start/end KYC timestamps + approval / failed / pending |
| `cards.csv` | Card activation events for approved users |
| `transactions.csv` | Simulated card payments, transfers, withdrawals |
| `funnel_events.csv` | Complete event history for funnel steps |

---

## Generation Logic (Notes)

Below is a detailed explanation of each generated table, including the exact columns and how each value was simulated.

---

## 📘 1. `users.csv`

| Column | Description | How it was generated |
|--------|-------------|-----------------------|
| `user_id` | Unique user identifier | Sequential integers from 1 to 2000 |
| `signup_at` | Timestamp of signup | Random datetime between Jan–Dec 2024 |
| `country` | User’s country | Random choice: AT/DE/UK/FR/ES/IT |
| `device` | Device type | Random choice: iOS, Android, Web |
| `marketing_channel` | Acquisition channel | Random choice: Organic, Social, Paid Search, etc. |

**Purpose:**  
Forms the core *dimension table* for all user-related joins and metrics.

---

## 📘 2. `kyc.csv`

| Column | Description | How it was generated |
|--------|-------------|-----------------------|
| `user_id` | Matches users table | Inherited from users who started KYC |
| `kyc_started_at` | When KYC began | signup time + random delay (5–120 mins after registration) |
| `kyc_completed_at` | When KYC finished | `started_at` + random duration (2–60 mins) |
| `kyc_status` | Final outcome | 75% APPROVED, 15% FAILED, 10% PENDING (probabilities) |

**Notes:**  
Only ~85% of users entered KYC.  
This table is key for compliance analytics and the funnel.

---

## 📘 3. `cards.csv`

| Column | Description | How it was generated |
|--------|-------------|-----------------------|
| `user_id` | Matches users | Only users with `kyc_status = APPROVED` |
| `card_activated_at` | When card was activated | KYC completion + random delay (0–7 days, + 10–180 mins) |
| `card_type` | Virtual or Physical | Random choice between the two |

**Notes:**  
Only ~80% of APPROVED users activate a card.  
Represents the next stage in the financial onboarding funnel.

---

## 📘 4. `transactions.csv`

| Column | Description | How it was generated |
|--------|-------------|-----------------------|
| `user_id` | Matches users | Only users who completed a first top-up |
| `transaction_time` | Timestamp of each spend event | First top-up time + random offset (0–90 days) |
| `amount_eur` | Transaction amount | Lognormal distribution (realistic 5–80€ average range) |
| `category` | Spending category | Random choice: Groceries, Restaurants, Transport, etc. |
| `merchant_country` | Country of merchant | Random choice from country list |
| `transaction_type` | Payment type | CARD_PAYMENT, ATM_WITHDRAWAL, TRANSFER |

**Notes:**  
Users make between **1–20 transactions** each.  
This forms your `fact_transactions` table later.

---

## 📘 5. `funnel_events.csv`

| Column | Description | How it was generated |
|--------|-------------|-----------------------|
| `user_id` | Unique user | Inherited from users |
| `step_order` | Funnel step number | 1–5 depending on how far the user progressed |
| `step_name` | Name of funnel step | VIEWED_SIGNUP, STARTED_REGISTRATION, KYC_COMPLETED, CARD_ACTIVATED, FIRST_TOPUP |
| `event_time` | Timestamp of the event | Generated from real timing logic (registration delay, KYC duration, activation delay, top-up delay) |

**Notes:**  
This is the **core table** for product analytics, conversion rates, and drop-off insights.

---

## 🔗 Funnel Flow (Simulated)

The final funnel looks like:

VIEWED_SIGNUP

STARTED_REGISTRATION

KYC_COMPLETED

CARD_ACTIVATED

FIRST_TOPUP

Each step has its own probability, delay, and timestamp pattern.

---
This will later be used to build funnel dashboards.

---

## ▶️ Run the Data Generator

```bash
uv run etl/generate_fake_data.py
```
---

# 🧩 Step 2 — ETL Pipeline (Python)

### Purpose

The ETL pipeline transforms the raw CSV files from Step 1 into clean, analytics-ready warehouse tables.  
This mirrors how a real analytics engineering workflow at Revolut would structure raw → modeled data.

ETL = Extract → Transform → Load

---

# ETL Flow (Short Overview)

### Extract
- Load all raw CSV files from `data/raw/`
- Parse datetime columns for proper time calculations
- Ensure consistent schemas for all tables

### Transform

The transform step prepares **three different warehouse tables**:

#### 1. Transforming user-level data → `dim_users`
- Merge all user-level raw sources (`users`, `kyc`, `cards`, `transactions`)
- Aggregate to one row per user
- Derive behavioral flags:
  - `has_kyc_approved`
  - `has_card_activated`
  - `has_topup`
- Compute onboarding durations in hours:
  - signup → KYC  
  - KYC → card_activation  
  - card_activation → first_topup

#### 2. Transforming transactions → `fct_transactions`
- Clean transaction timestamps and enforce numeric types
- Add helpful time dimensions:
  - `transaction_date`
  - `transaction_hour`
- Keep one row per transaction for granular analysis

#### 3. Transforming funnel events → `fct_funnel`
- Sort funnel events chronologically for each user
- Enforce correct `step_order` typing
- Ensure there is one event per step per user
### Load
- Save all modeled tables to `data/warehouse/` in Parquet format
- Parquet is chosen because it is:
  - column-oriented (fast for analytics)
  - compressed (efficient)
  - used in modern data warehouses (BigQuery, Snowflake)
  - easy to preview with the VS Code “Parquet Viewer” extension

---

# 🗂️ Warehouse Tables Created

## 📘 1. `dim_users.parquet`
A dimension table containing one row per user with:

- country, device, marketing_channel  
- signup timestamp  
- KYC timestamps + final status  
- card activation timestamp + card type  
- first transaction timestamp  
- behavioral flags:
  - `has_kyc_approved`
  - `has_card_activated`
  - `has_topup`
- duration metrics in hours:
  - `time_to_kyc_hours`
  - `time_kyc_to_card_hours`
  - `time_card_to_first_tx_hours`

Purpose: Core user-level model for onboarding, funnel conversion, and behavioral insights.

---

## 📘 2. `fct_transactions.parquet`
A fact table with one row per transaction, including:

- `transaction_time`
- `transaction_date`
- `transaction_hour`
- `amount_eur`
- `category`
- `merchant_country`
- `transaction_type`

Purpose: Transaction-level analysis for revenue, spending patterns, and time-based analytics.

---

## 📘 3. `fct_funnel.parquet`
A funnel event table with one row per onboarding step:

- `user_id`
- `step_order`
- `step_name`
- `event_time`

Purpose: Conversion funnel analysis, drop-off identification, and sequencing of onboarding events.

---

# ▶️ Run the ETL Pipeline
uv run etl/etl_pipeline.py

This generates all warehouse tables under:

They can be viewed using:
- VS Code “Parquet Viewer”
- or loaded via Pandas / any BI tool.


