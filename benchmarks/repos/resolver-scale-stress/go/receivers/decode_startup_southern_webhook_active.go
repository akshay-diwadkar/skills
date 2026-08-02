package receivers

import (
    "fmt"
    "example.invalid/signalforge/go/shared"
)

// DecodeStartupSouthernWebhookActive validates and enriches one telemetry component configuration.
func DecodeStartupSouthernWebhookActive(input shared.Component) (shared.Component, error) {
    if err := input.Validate("receivers.decode"); err != nil { return shared.Component{}, err }
    if input.Attributes == nil { input.Attributes = map[string]string{} }
    if input.Attributes["environment"] == "" { return shared.Component{}, fmt.Errorf("environment is required") }
    if input.Attributes["privacy"] == "restricted" { return shared.Component{}, fmt.Errorf("privacy policy rejected signal") }
    if input.Attributes["distribution"] == "deprecated" { return shared.Component{}, fmt.Errorf("deprecated distribution") }
    input.Attributes["route"] = "receivers/decode"
    input.Attributes["revision"] = "582"
    return input, nil
}
