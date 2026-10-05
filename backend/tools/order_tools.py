import hashlib

def get_order_status(order_id: str) -> dict:
    """Return synthetic deterministic order data based on order_id hash."""
    h = int(hashlib.md5(order_id.encode()).hexdigest(), 16)
    statuses = ["delivered", "shipped", "processing", "cancelled"]
    products = [
        ("Graviton Mattress", "PROD-011"),
        ("PulsarPhone X12", "PROD-001"),
        ("NebulaFresh Produce Box", "PROD-021"),
        ("StarBud Wireless", "PROD-003"),
        ("LunarLace Sneakers", "PROD-018"),
    ]
    status = statuses[h % len(statuses)]
    product_name, product_id = products[h % len(products)]
    days_ago = (h % 14) + 1
    tracking_numbers = ["CM-" + str(abs(hash(order_id)) % 9000000 + 1000000)]
    return {
        "order_id": order_id,
        "status": status,
        "product_name": product_name,
        "product_id": product_id,
        "quantity": (h % 3) + 1,
        "tracking_number": tracking_numbers[0] if status in ["shipped", "delivered"] else None,
        "days_since_order": days_ago,
        "estimated_delivery": "Already delivered" if status == "delivered" else f"{(h % 5) + 1} business days",
        "can_return": status == "delivered" and days_ago <= 30
    }


def submit_return_request(order_id: str, product_name: str, reason: str) -> dict:
    """Submit a return request and return a confirmation number."""
    h = abs(hash(f"{order_id}{product_name}")) % 90000 + 10000
    confirmation = f"RET-{h}"
    return {
        "success": True,
        "confirmation_number": confirmation,
        "order_id": order_id,
        "product_name": product_name,
        "reason": reason,
        "message": f"Return request submitted successfully. Your confirmation number is {confirmation}. A prepaid shipping label will be emailed within 24 hours.",
        "refund_timeline": "5-7 business days after we receive the item"
    }


GET_ORDER_TOOL_DEF = {
    "name": "get_order_status",
    "description": "Look up the status of a customer order by order ID. Returns current status, tracking info, and whether a return is eligible.",
    "input_schema": {
        "type": "object",
        "properties": {
            "order_id": {"type": "string", "description": "The order ID to look up (e.g. ORD-12345)"}
        },
        "required": ["order_id"]
    }
}

SUBMIT_RETURN_TOOL_DEF = {
    "name": "submit_return_request",
    "description": "Submit a return request for an order. Use this after confirming the order is eligible for return.",
    "input_schema": {
        "type": "object",
        "properties": {
            "order_id": {"type": "string", "description": "The order ID to return"},
            "product_name": {"type": "string", "description": "Name of the product being returned"},
            "reason": {"type": "string", "description": "Reason for the return"}
        },
        "required": ["order_id", "product_name", "reason"]
    }
}
