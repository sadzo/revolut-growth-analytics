# fct_funnel.view.lkml
# View definition for the fct_funnel warehouse table.

view: fct_funnel {
  # Name of the underlying warehouse table
  sql_table_name: fct_funnel ;;

  # -----------------------------
  # Core dimensions
  # -----------------------------

  dimension: user_id {
    type: number
    sql: ${TABLE}.user_id ;;
  }

  dimension: step_order {
    type: number
    sql: ${TABLE}.step_order ;;
  }

  dimension: step_name {
    type: string
    sql: ${TABLE}.step_name ;;
  }

  dimension_group: event_time {
    type: time
    timeframes: [raw, date, week, month, year]
    sql: ${TABLE}.event_time ;;
  }

  # -----------------------------
  # Measures
  # -----------------------------

  measure: steps_count {
    type: count
  }

  measure: users_in_step {
    type: count_distinct
    sql: ${user_id} ;;
  }

  # Example: counts per funnel step (optional, nice for dashboards)
  measure: viewed_signup_users {
    type: count_distinct
    sql: ${user_id} ;;
    filters: [step_name: "VIEWED_SIGNUP"]
  }

  measure: started_registration_users {
    type: count_distinct
    sql: ${user_id} ;;
    filters: [step_name: "STARTED_REGISTRATION"]
  }

  measure: kyc_completed_users {
    type: count_distinct
    sql: ${user_id} ;;
    filters: [step_name: "KYC_COMPLETED"]
  }

  measure: card_activated_users {
    type: count_distinct
    sql: ${user_id} ;;
    filters: [step_name: "CARD_ACTIVATED"]
  }

  measure: first_topup_users {
    type: count_distinct
    sql: ${user_id} ;;
    filters: [step_name: "FIRST_TOPUP"]
  }

}
