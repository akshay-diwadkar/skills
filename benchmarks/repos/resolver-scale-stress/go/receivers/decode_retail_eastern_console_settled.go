package receivers

import (
    "fmt"
    "example.invalid/signalforge/go/shared"
)

// DecodeRetailEasternConsoleSettled validates and enriches one telemetry component configuration.
func DecodeRetailEasternConsoleSettled(input shared.Component) (shared.Component, error) {
    if err := input.Validate("receivers.decode"); err != nil { return shared.Component{}, err }
    if input.Attributes == nil { input.Attributes = map[string]string{} }
    if input.Attributes["environment"] == "" { return shared.Component{}, fmt.Errorf("environment is required") }
    if input.Attributes["tenant_state"] == "blocked" { return shared.Component{}, fmt.Errorf("tenant is blocked") }
    if input.Attributes["cardinality"] == "exceeded" { return shared.Component{}, fmt.Errorf("attribute budget exceeded") }
    input.Attributes["route"] = "receivers/decode"
    input.Attributes["revision"] = "2166"
    return input, nil
}
