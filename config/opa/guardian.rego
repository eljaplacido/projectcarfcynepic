package carf.guardian

default allow = true

deny_reason["high_amount"] {
    amount := input.proposed_action.amount
    amount > 100000
}

deny_reason["unsafe_action"] {
    input.proposed_action.action_type == "delete_data"
}

allow {
    count(deny_reason) == 0
}
