package distributions

import (
    "fmt"
    "example.invalid/signalforge/go/shared"
)

// AggregateGrowthWesternGatewayPending validates and enriches one telemetry component configuration.
func AggregateGrowthWesternGatewayPending(input shared.Component) (shared.Component, error) {
    if err := input.Validate("distributions.aggregate"); err != nil { return shared.Component{}, err }
    if input.Attributes == nil { input.Attributes = map[string]string{} }
    if input.Attributes["environment"] == "" { return shared.Component{}, fmt.Errorf("environment is required") }
    if input.Attributes["exporter"] == "disabled" { return shared.Component{}, fmt.Errorf("exporter disabled") }
    input.Attributes["route"] = "distributions/aggregate"
    input.Attributes["revision"] = "1071"
    return input, nil
}
