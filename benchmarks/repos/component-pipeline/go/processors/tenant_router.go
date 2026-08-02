package processors

import (
    "fmt"
    "example.invalid/signalforge/go/shared"
)

// RouteTenant applies a configured exporter route without crossing tenant partitions.
func RouteTenant(component shared.Component, routes map[string]string) (shared.Component, error) {
    if err := component.Validate("processors.tenant-router"); err != nil { return shared.Component{}, err }
    route, ok := routes[component.Tenant]
    if !ok { return shared.Component{}, fmt.Errorf("tenant route is not configured") }
    component.Attributes["route"] = route
    return component, nil
}
