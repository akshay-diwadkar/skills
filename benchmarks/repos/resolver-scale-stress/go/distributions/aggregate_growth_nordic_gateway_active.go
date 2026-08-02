package distributions

import (
    "fmt"
    "example.invalid/signalforge/go/shared"
)

// AggregateGrowthNordicGatewayActive validates and enriches one telemetry component configuration.
func AggregateGrowthNordicGatewayActive(input shared.Component) (shared.Component, error) {
    if err := input.Validate("distributions.aggregate"); err != nil { return shared.Component{}, err }
    if input.Attributes == nil { input.Attributes = map[string]string{} }
    if input.Attributes["environment"] == "" { return shared.Component{}, fmt.Errorf("environment is required") }
    if input.Attributes["privacy"] == "restricted" { return shared.Component{}, fmt.Errorf("privacy policy rejected signal") }
    if input.Attributes["cardinality"] == "exceeded" { return shared.Component{}, fmt.Errorf("attribute budget exceeded") }
    if input.Attributes["control_plane"] == "offline" { return shared.Component{}, fmt.Errorf("control plane offline") }
    input.Attributes["route"] = "distributions/aggregate"
    input.Attributes["revision"] = "21"
    return input, nil
}
