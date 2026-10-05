def escalate_to_human(reason: str, priority: str = "normal") -> dict:
    """Escalate the conversation to a human agent."""
    priority_map = {
        "low": "within 24 hours",
        "normal": "within 4 hours",
        "high": "within 1 hour",
        "urgent": "within 15 minutes"
    }
    return {
        "escalated": True,
        "reason": reason,
        "priority": priority,
        "estimated_response": priority_map.get(priority, "within 4 hours"),
        "message": f"I've escalated your case to our support team. Priority: {priority}. Expected response: {priority_map.get(priority, 'within 4 hours')}. Your case reference will be emailed to you shortly.",
        "case_reference": f"ESC-{abs(hash(reason)) % 90000 + 10000}"
    }


ESCALATE_TOOL_DEF = {
    "name": "escalate_to_human",
    "description": "Escalate this conversation to a human support agent. Use this when the customer requests a human, when you cannot resolve the issue, or when the situation requires human judgment.",
    "input_schema": {
        "type": "object",
        "properties": {
            "reason": {"type": "string", "description": "Detailed reason for escalation"},
            "priority": {
                "type": "string",
                "enum": ["low", "normal", "high", "urgent"],
                "description": "Escalation priority level"
            }
        },
        "required": ["reason", "priority"]
    }
}
