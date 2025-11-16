# revolut_growth.model.lkml
#
# Purpose:
# - This is the main LookML model file for the Revolut Growth Analytics project.
# - It tells Looker:
#     * which views belong to this project,
#     * which explores are available, (= Explores are the starting points for analysis, where Looker knows which tables to include and how to join them.)
#     * how the warehouse tables (dim_users, fct_transactions, fct_funnel)
#       are joined together for analysis.
#
# ----------------------------------------
# Connection (placeholder)
# ----------------------------------------
# This is the logical name of the database connection.
# In a real environment, this must match a Looker connection name.
connection: "revolut_growth_demo"

# ----------------------------------------
# Include all view files
# ----------------------------------------
# This makes LookML aware of all .view.lkml files in the same folder.
# We defined:
#   - dim_users.view.lkml
#   - fct_transactions.view.lkml
#   - fct_funnel.view.lkml
include: "*.view.lkml"


# ----------------------------------------
# Explore 1: dim_users (primary explore)
# ----------------------------------------
# This is the main entry point for analysis.
# It represents one row per user and joins to:
#   - fct_transactions (many transactions per user)
#   - fct_funnel (many funnel steps per user)
#
# Typical use cases:
# - Onboarding funnels (signup -> KYC -> card -> top-up)
# - Conversion rates by country, device, marketing_channel
# - Time to KYC, time to card activation, time to first top-up
# - Total amount spent per user

explore: dim_users {
  label: "Users"
  description: "User-level onboarding, KYC, card activation, and top-up behavior."

  # -----------------------------
  # Join: fct_transactions
  # -----------------------------
  # Left join: keep all users, attach transactions when available.
  # Relationship:
  # - One user in dim_users
  # - Many related rows in fct_transactions
  #
  # This enables:
  # - Total spend per user
  # - Average transaction amount by cohort
  # - User segmentation by transaction behavior

  join: fct_transactions {
    type: left_outer
    relationship: one_to_many
    sql_on: ${dim_users.user_id} = ${fct_transactions.user_id} ;;
  }

  # -----------------------------
  # Join: fct_funnel
  # -----------------------------
  # Left join: keep all users, attach funnel events when available.
  # Relationship:
  # - One user in dim_users
  # - Many related rows in fct_funnel
  #
  # This enables:
  # - Counting how many users reached each funnel step
  # - Calculating drop-off rates between steps
  # - Analyzing funnels by country, device, or marketing_channel

  join: fct_funnel {
    type: left_outer
    relationship: one_to_many
    sql_on: ${dim_users.user_id} = ${fct_funnel.user_id} ;;
  }
}


# ----------------------------------------
# Explore 2: fct_transactions (transaction-centric view)
# ----------------------------------------
# This explore focuses on transactions as the primary grain.
# Use cases:
# - Time series of total spend
# - Category-level spend by day/week/month
# - Merchant_country and transaction_type breakdowns
#
# - dim_users is joined in case user attributes (country, device, marketing_channel) are needed for segmentation.

explore: fct_transactions {
  label: "Transactions"
  description: "Transaction-level analytics: volume, amount, categories, and time patterns."

  join: dim_users {
    type: left_outer
    relationship: many_to_one
    sql_on: ${fct_transactions.user_id} = ${dim_users.user_id} ;;
  }
}


# ----------------------------------------
# Explore 3: fct_funnel (funnel-centric view)
# ----------------------------------------
# This explore focuses on funnel events as the primary grain.
# Use cases:
# - Counting users per funnel step
# - Understanding how many users reach each stage
# - Building funnel conversion charts
#
# - dim_users is joined to segment funnel performance by country, device, etc.

explore: fct_funnel {
  label: "Funnel Events"
  description: "Onboarding funnel events: signup views, registration, KYC, card activation, top-up."

  join: dim_users {
    type: left_outer
    relationship: many_to_one
    sql_on: ${fct_funnel.user_id} = ${dim_users.user_id} ;;
  }
}
