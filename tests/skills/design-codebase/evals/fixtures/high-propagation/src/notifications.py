def status_message(order: dict) -> str:
    return f"Order is {order['internal_status']}"
