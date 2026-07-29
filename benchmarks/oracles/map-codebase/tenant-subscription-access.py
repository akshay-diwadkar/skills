from src.accounts.tenant_access_policy import may_manage_subscription

assert may_manage_subscription("tenant-a", "tenant-a", "billing-admin")
assert not may_manage_subscription("tenant-a", "tenant-b", "billing-admin")
assert not may_manage_subscription("tenant-a", "tenant-a", "viewer")
