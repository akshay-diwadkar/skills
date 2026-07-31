import vendor_sdk


def charge(amount: int, token: str):
    request = vendor_sdk.Charge(amount=amount, token=token)
    return vendor_sdk.submit(request)
