USER_TYPE_JSON_SCHEMA = {
    "type": "json_schema",
    "name": "user_type_response",
    "schema": {
        "type": "object",
        "properties": {
            "userType": {
                "type": "string",
                "enum": [
                    "ELDERLY",
                    "WHEELCHAIR",
                    "VISUAL_IMPAIRMENT",
                    "HEARING_IMPAIRMENT",
                    "NORMAL",
                    "UNKNOWN",
                ],
            },
            "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
            "reason": {"type": "string"},
        },
        "required": ["userType", "confidence", "reason"],
        "additionalProperties": False,
    },
    "strict": True,
}


SERVICE_RECOMMEND_JSON_SCHEMA = {
    "type": "json_schema",
    "name": "service_recommend_response",
    "schema": {
        "type": "object",
        "properties": {
            "intent": {
                "type": "string",
                "enum": [
                    "issue_document",
                    "submit_application",
                    "pay_or_check",
                    "welfare_service",
                    "general_question",
                    "unknown",
                ],
            },
            "serviceId": {
                "type": "string",
                "enum": [
                    "RESIDENT_REGISTRATION_COPY",
                    "RESIDENT_REGISTRATION_ABSTRACT",
                    "MOVE_IN_REPORT",
                    "MOVE_OUT_REPORT",
                    "",
                ],
            },
            "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
            "answer": {"type": "string"},
        },
        "required": ["intent", "serviceId", "confidence", "answer"],
        "additionalProperties": False,
    },
    "strict": True,
}


CHAT_JSON_SCHEMA = {
    "type": "json_schema",
    "name": "chat_response",
    "schema": {
        "type": "object",
        "properties": {
            "answer": {"type": "string"},
        },
        "required": ["answer"],
        "additionalProperties": False,
    },
    "strict": True,
}
