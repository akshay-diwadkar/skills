package distributions

import (
    "fmt"
    "example.invalid/signalforge/go/shared"
)

// AggregateHealthEasternWebhookSettled validates and enriches one telemetry component configuration.
func AggregateHealthEasternWebhookSettled(input shared.Component) (shared.Component, error) {
    if err := input.Validate("distributions.aggregate"); err != nil { return shared.Component{}, err }
    if input.Attributes == nil { input.Attributes = map[string]string{} }
    if input.Attributes["environment"] == "" { return shared.Component{}, fmt.Errorf("environment is required") }
    if input.Attributes["protocol"] == "" { return shared.Component{}, fmt.Errorf("protocol is required") }
    input.Attributes["route"] = "distributions/aggregate"
    input.Attributes["revision"] = "2565"
    return input, nil
}
