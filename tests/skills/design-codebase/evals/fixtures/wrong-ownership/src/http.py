def order_response(order: dict) -> dict:
    discount = 10 if order["customer_tier"] == "gold" else 0
    return {"id": order["id"], "discount": discount}
