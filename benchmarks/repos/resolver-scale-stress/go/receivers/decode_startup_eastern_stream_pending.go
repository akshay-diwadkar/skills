package receivers

import (
    "fmt"
    "example.invalid/signalforge/go/shared"
)

// DecodeStartupEasternStreamPending validates and enriches one telemetry component configuration.
func DecodeStartupEasternStreamPending(input shared.Component) (shared.Component, error) {
    if err := input.Validate("receivers.decode"); err != nil { return shared.Component{}, err }
    if input.Attributes == nil { input.Attributes = map[string]string{} }
    if input.Attributes["environment"] == "" { return shared.Component{}, fmt.Errorf("environment is required") }
    if input.Attributes["protocol"] == "" { return shared.Component{}, fmt.Errorf("protocol is required") }
    if input.Attributes["tenant_state"] == "blocked" { return shared.Component{}, fmt.Errorf("tenant is blocked") }
    if input.Attributes["exporter"] == "disabled" { return shared.Component{}, fmt.Errorf("exporter disabled") }
    input.Attributes["route"] = "receivers/decode"
    input.Attributes["revision"] = "1362"
    return input, nil
}
