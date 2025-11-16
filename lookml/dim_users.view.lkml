# dim_users.view.lkml
# View definition for the dim_users warehouse table.

view: dim_users {
  # This should match the table name in your warehouse.
  # In a real Looker project, this would point to a table in BigQuery/Snowflake/etc.
  sql_table_name: dim_users ;;

  # -----------------------------
  # Primary key
  # -----------------------------
  dimension: user_id {
    primary_key: yes
    type: number
    sql: ${TABLE}.user_id ;;
  }

  # -----------------------------
  # Core user attributes
  # -----------------------------

  dimension_group: signup_at {
    # Time dimension group from signup_at timestamp
    type: time
    timeframes: [raw, date, week, month, year]
    sql: ${TABLE}.signup_at ;;
  }

  dimension: country {
    type: string
    sql: ${TABLE}.country ;;
  }

  dimension: device {
    type: string
    sql: ${TABLE}.device ;;
  }

  dimension: marketing_channel {
    type: string
    sql: ${TABLE}.marketing_channel ;;
  }

  # -----------------------------
  # KYC information
  # -----------------------------

  dimension_group: first_kyc_started_at {
    type: time
    timeframes: [raw, date, week, month]
    sql: ${TABLE}.first_kyc_started_at ;;
  }

  dimension_group: first_kyc_completed_at {
    type: time
    timeframes: [raw, date, week, month]
    sql: ${TABLE}.first_kyc_completed_at ;;
  }

  dimension: kyc_status {
    type: string
    sql: ${TABLE}.kyc_status ;;
  }

  dimension: has_kyc_approved {
    # yesno type is useful for filters and segments
    type: yesno
    sql: ${TABLE}.has_kyc_approved ;;
  }

  # -----------------------------
  # Card activation
  # -----------------------------

  dimension_group: card_activated_at {
    type: time
    timeframes: [raw, date, week, month]
    sql: ${TABLE}.card_activated_at ;;
  }

  dimension: card_type {
    type: string
    sql: ${TABLE}.card_type ;;
  }

  dimension: has_card_activated {
    type: yesno
    sql: ${TABLE}.has_card_activated ;;
  }

  # -----------------------------
  # Transactions / top-up
  # -----------------------------

  dimension_group: first_transaction_at {
    type: time
    timeframes: [raw, date, week, month]
    sql: ${TABLE}.first_transaction_at ;;
  }

  dimension: has_topup {
    type: yesno
    sql: ${TABLE}.has_topup ;;
  }

  dimension: total_transactions {
    type: number
    sql: ${TABLE}.total_transactions ;;
  }

  dimension: total_amount_eur {
    type: number
    sql: ${TABLE}.total_amount_eur ;;
    value_format_name: eur_0 ;;
  }

  # -----------------------------
  # Onboarding duration metrics
  # -----------------------------
  # These are already precomputed in hours in the warehouse.
  # Expose them as numeric dimensions.

  dimension: time_to_kyc_hours {
    type: number
    sql: ${TABLE}.time_to_kyc_hours ;;
    value_format_name: decimal_1 ;;
  }

  dimension: time_kyc_to_card_hours {
    type: number
    sql: ${TABLE}.time_kyc_to_card_hours ;;
    value_format_name: decimal_1 ;;
  }

  dimension: time_card_to_first_tx_hours {
    type: number
    sql: ${TABLE}.time_card_to_first_tx_hours ;;
    value_format_name: decimal_1 ;;
  }

  # -----------------------------
  # Measures (aggregations)
  # -----------------------------

  measure: users_count {
    type: count
    sql: ${user_id} ;;
  }

  measure: approved_users {
    type: count
    filters: [kyc_status: "APPROVED"]
  }

  measure: card_activated_users {
    type: count
    filters: [has_card_activated: "yes"]
  }

  measure: topup_users {
    type: count
    filters: [has_topup: "yes"]
  }

  measure: total_amount_all_users_eur {
    type: sum
    sql: ${total_amount_eur} ;;
    value_format_name: eur_0 ;;
  }

  # Example conversion metric as a measure
  measure: card_activation_rate {
    type: number
    sql: ${card_activated_users} / NULLIF(${users_count}, 0) ;;
    value_format_name: percent_1 ;;
  }

}
