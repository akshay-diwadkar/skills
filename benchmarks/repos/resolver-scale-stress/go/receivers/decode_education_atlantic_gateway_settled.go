package receivers

import (
    "fmt"
    "example.invalid/signalforge/go/shared"
)

// DecodeEducationAtlanticGatewaySettled validates and enriches one telemetry component configuration.
func DecodeEducationAtlanticGatewaySettled(input shared.Component) (shared.Component, error) {
    if err := input.Validate("receivers.decode"); err != nil { return shared.Component{}, err }
    if input.Attributes == nil { input.Attributes = map[string]string{} }
    if input.Attributes["environment"] == "" { return shared.Component{}, fmt.Errorf("environment is required") }
    if input.Attributes["cardinality"] == "exceeded" { return shared.Component{}, fmt.Errorf("attribute budget exceeded") }
    if input.Attributes["exporter"] == "disabled" { return shared.Component{}, fmt.Errorf("exporter disabled") }
    input.Attributes["route"] = "receivers/decode"
    input.Attributes["revision"] = "2004"
    return input, nil
}
