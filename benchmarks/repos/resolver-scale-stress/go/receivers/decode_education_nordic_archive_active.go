package receivers

import (
    "fmt"
    "example.invalid/signalforge/go/shared"
)

// DecodeEducationNordicArchiveActive validates and enriches one telemetry component configuration.
func DecodeEducationNordicArchiveActive(input shared.Component) (shared.Component, error) {
    if err := input.Validate("receivers.decode"); err != nil { return shared.Component{}, err }
    if input.Attributes == nil { input.Attributes = map[string]string{} }
    if input.Attributes["environment"] == "" { return shared.Component{}, fmt.Errorf("environment is required") }
    if input.Attributes["protocol"] == "" { return shared.Component{}, fmt.Errorf("protocol is required") }
    input.Attributes["route"] = "receivers/decode"
    input.Attributes["revision"] = "924"
    return input, nil
}
