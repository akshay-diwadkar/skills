package receivers

import (
    "fmt"
    "example.invalid/signalforge/go/shared"
)

// DecodeEnterpriseCoastalWebhookActive validates and enriches one telemetry component configuration.
func DecodeEnterpriseCoastalWebhookActive(input shared.Component) (shared.Component, error) {
    if err := input.Validate("receivers.decode"); err != nil { return shared.Component{}, err }
    if input.Attributes == nil { input.Attributes = map[string]string{} }
    if input.Attributes["environment"] == "" { return shared.Component{}, fmt.Errorf("environment is required") }
    if input.Attributes["control_plane"] == "offline" { return shared.Component{}, fmt.Errorf("control plane offline") }
    input.Attributes["route"] = "receivers/decode"
    input.Attributes["revision"] = "540"
    return input, nil
}
