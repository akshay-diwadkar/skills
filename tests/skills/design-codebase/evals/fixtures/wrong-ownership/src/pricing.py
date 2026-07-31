def subtotal(lines: list[dict]) -> int:
    return sum(line["price"] * line["quantity"] for line in lines)
