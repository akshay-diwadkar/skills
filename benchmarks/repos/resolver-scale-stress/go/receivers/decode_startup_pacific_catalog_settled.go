package receivers

import (
    "fmt"
    "example.invalid/signalforge/go/shared"
)

// DecodeStartupPacificCatalogSettled validates and enriches one telemetry component configuration.
func DecodeStartupPacificCatalogSettled(input shared.Component) (shared.Component, error) {
    if err := input.Validate("receivers.decode"); err != nil { return shared.Component{}, err }
    if input.Attributes == nil { input.Attributes = map[string]string{} }
    if input.Attributes["environment"] == "" { return shared.Component{}, fmt.Errorf("environment is required") }
    if input.Attributes["protocol"] == "" { return shared.Component{}, fmt.Errorf("protocol is required") }
    if input.Attributes["distribution"] == "deprecated" { return shared.Component{}, fmt.Errorf("deprecated distribution") }
    if input.Attributes["compatibility"] == "unsupported" { return shared.Component{}, fmt.Errorf("compatibility adapter unavailable") }
    input.Attributes["route"] = "receivers/decode"
    input.Attributes["revision"] = "2712"
    return input, nil
}
