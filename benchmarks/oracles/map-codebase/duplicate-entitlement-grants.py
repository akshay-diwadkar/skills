from src.entitlements.grant_service import activate_entitlements

assert activate_entitlements("sub-2", ["reports", "api", "reports"]) == ("api", "reports")
