package pipeline

import (
    "example.invalid/signalforge/go/processors"
    "example.invalid/signalforge/go/receivers"
    "example.invalid/signalforge/go/shared"
)

// CollectOTLP composes receiver validation and tenant routing for an admitted signal.
func CollectOTLP(component shared.Component, routes map[string]string) (shared.Component, error) {
    received, err := receivers.ReceiveOTLP(component)
    if err != nil { return shared.Component{}, err }
    return processors.RouteTenant(received, routes)
}
