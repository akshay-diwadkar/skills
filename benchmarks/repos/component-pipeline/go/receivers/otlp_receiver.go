package receivers

import (
    "fmt"
    "example.invalid/signalforge/go/shared"
)

// ReceiveOTLP validates the tenant boundary before admitting an OTLP signal.
func ReceiveOTLP(component shared.Component) (shared.Component, error) {
    if err := component.Validate("receivers.otlp"); err != nil { return shared.Component{}, err }
    if component.Attributes["protocol"] != "otlp" { return shared.Component{}, fmt.Errorf("OTLP protocol attribute is required") }
    component.Attributes["receiver"] = "otlp"
    return component, nil
}
