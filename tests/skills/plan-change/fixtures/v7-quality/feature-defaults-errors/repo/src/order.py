def place_order(items: list[str], shipping: str = "standard") -> str:
    if shipping not in {"standard", "express"}:
        raise ValueError("unsupported shipping")
    return ",".join(items) + "|" + shipping
