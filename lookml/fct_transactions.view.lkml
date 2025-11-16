# fct_transactions.view.lkml
# View definition for the fct_transactions warehouse table.

view: fct_transactions {
  # Name of the underlying warehouse table
  sql_table_name: fct_transactions ;;

  # -----------------------------
  # Keys and core dimensions
  # -----------------------------

  dimension: user_id {
    type: number
    sql: ${TABLE}.user_id ;;
  }

  dimension_group: transaction_time {
    # Time dimension group from transaction_time
    type: time
    timeframes: [raw, date, hour_of_day, week, month, year]
    sql: ${TABLE}.transaction_time ;;
  }

  dimension: transaction_date {
    type: date
    sql: ${TABLE}.transaction_date ;;
  }

  dimension: transaction_hour {
    type: number
    sql: ${TABLE}.transaction_hour ;;
  }

  dimension: amount_eur {
    type: number
    sql: ${TABLE}.amount_eur ;;
    value_format_name: eur_0 ;;
  }

  dimension: category {
    type: string
    sql: ${TABLE}.category ;;
  }

  dimension: merchant_country {
    type: string
    sql: ${TABLE}.merchant_country ;;
  }

  dimension: transaction_type {
    type: string
    sql: ${TABLE}.transaction_type ;;
  }

  # -----------------------------
  # Measures (aggregations)
  # -----------------------------

  measure: transactions_count {
    type: count
  }

  measure: total_amount_eur {
    type: sum
    sql: ${amount_eur} ;;
    value_format_name: eur_0 ;;
  }

  measure: avg_transaction_amount_eur {
    type: average
    sql: ${amount_eur} ;;
    value_format_name: eur_0 ;;
  }

  measure: card_payments_count {
    type: count
    filters: [transaction_type: "CARD_PAYMENT"]
  }

  measure: atm_withdrawals_count {
    type: count
    filters: [transaction_type: "ATM_WITHDRAWAL"]
  }

  measure: transfers_count {
    type: count
    filters: [transaction_type: "TRANSFER"]
  }

}
