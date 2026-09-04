RECOGNISED_BUILTINS = {
    "IN", "IIF", "SQL_LIKE", "ISNULL", "DECODE", "LENGTH", "CONCAT",
    "LTRIM", "RTRIM", "SUBSTR", "UPPER", "IS_NUMBER", "TO_INTEGER",
    "REG_MATCH", "TO_CHAR", "INSTR", "TO_DATE", "REPLACECHR", "IS_DATE",
    "LPAD", "TO_DECIMAL", "SYSTIMESTAMP",
}
PARSEABLE_KINDS = {"expression", "lookup-condition", "filter-condition"}
OPAQUE_KINDS = {"join-condition", "sql-query", "update-dynamic-cache-condition"}
LOGIC_ATTRS = {
    "expression": "expression",
    "lookupCondition": "lookup-condition",
    "filterCondition": "filter-condition",
    "joinCondition": "join-condition",
    "sqlQuery": "sql-query",
    "updateDynamicCacheCondition": "update-dynamic-cache-condition",
}
OUTCOME_MAP = {
    "VALID": "VALID", "Valid": "VALID",
    "INVALID": "INVALID", "Invalid": "INVALID",
    "DONTEVAL": "NOT_EVALUATED",
}
CANON_CALLS = {
    "IIF":"conditional", "DECODE":"choose", "IN":"in_set", "SQL_LIKE":"pattern_like",
    "ISNULL":"is_null", "LENGTH":"length", "CONCAT":"concat", "LTRIM":"trim_left",
    "RTRIM":"trim_right", "SUBSTR":"substring", "UPPER":"upper", "IS_NUMBER":"is_number",
    "TO_INTEGER":"to_integer", "REG_MATCH":"regex_match", "TO_CHAR":"to_string",
    "INSTR":"position", "TO_DATE":"to_date", "REPLACECHR":"replace_char", "IS_DATE":"is_date",
    "LPAD":"pad_left", "TO_DECIMAL":"to_decimal", "SYSTIMESTAMP":"system_timestamp",
}
CANON_OPS = {
    "AND":"all_of", "OR":"any_of", "NOT":"not", "=":"equal", "!=":"not_equal", "<>":"not_equal",
    "^=":"not_equal_alt", "<":"less_than", "<=":"less_or_equal", ">":"greater_than", ">=":"greater_or_equal",
    "+":"add", "-":"subtract", "*":"multiply", "/":"divide", "%":"modulo", "||":"concat_op",
    "U+":"positive", "U-":"negative",
}
INV_CALLS = {v:k for k,v in CANON_CALLS.items()}
INV_OPS = {v:k for k,v in CANON_OPS.items()}
