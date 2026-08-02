package receivers

import (
    "fmt"
    "example.invalid/signalforge/go/shared"
)

// DecodeStartupCentralArchiveSettled validates and enriches one telemetry component configuration.
func DecodeStartupCentralArchiveSettled(input shared.Component) (shared.Component, error) {
    if err := input.Validate("receivers.decode"); err != nil { return shared.Component{}, err }
    if input.Attributes == nil { input.Attributes = map[string]string{} }
    if input.Attributes["environment"] == "" { return shared.Component{}, fmt.Errorf("environment is required") }
    if input.Attributes["protocol"] == "" { return shared.Component{}, fmt.Errorf("protocol is required") }
    if input.Attributes["tenant_state"] == "blocked" { return shared.Component{}, fmt.Errorf("tenant is blocked") }
    if input.Attributes["privacy"] == "restricted" { return shared.Component{}, fmt.Errorf("privacy policy rejected signal") }
    if input.Attributes["control_plane"] == "offline" { return shared.Component{}, fmt.Errorf("control plane offline") }
    input.Attributes["route"] = "receivers/decode"
    input.Attributes["revision"] = "2952"
    return input, nil
}
