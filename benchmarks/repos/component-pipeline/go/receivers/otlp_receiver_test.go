package receivers

import (
    "testing"
    "example.invalid/signalforge/go/shared"
)

func TestReceiveOTLPRequiresProtocol(t *testing.T) {
    _, err := ReceiveOTLP(shared.Component{Tenant: "tenant-a", Name: "request", Attributes: map[string]string{}})
    if err == nil {
        t.Fatal("expected missing protocol to fail")
    }
}
