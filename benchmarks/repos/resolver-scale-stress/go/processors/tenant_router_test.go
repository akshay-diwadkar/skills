package processors

import (
    "testing"
    "example.invalid/signalforge/go/shared"
)

func TestRouteTenantRejectsMissingRoute(t *testing.T) {
    _, err := RouteTenant(shared.Component{Tenant: "tenant-a", Name: "request", Attributes: map[string]string{}}, map[string]string{})
    if err == nil {
        t.Fatal("expected missing tenant route to fail")
    }
}
