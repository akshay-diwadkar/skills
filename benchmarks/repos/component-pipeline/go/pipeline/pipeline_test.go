package pipeline

import (
    "testing"
    "example.invalid/signalforge/go/shared"
)

func TestCollectOTLPValidatesAndRoutesTheSignal(t *testing.T) {
    input := shared.Component{Tenant: "tenant-a", Name: "request", Attributes: map[string]string{"protocol": "otlp"}}
    output, err := CollectOTLP(input, map[string]string{"tenant-a": "primary"})
    if err != nil { t.Fatal(err) }
    if output.Attributes["receiver"] != "otlp" || output.Attributes["route"] != "primary" {
        t.Fatalf("unexpected pipeline attributes: %#v", output.Attributes)
    }
}
