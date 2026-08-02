package distributions

import "fmt"

type ComponentRegistry struct { receivers map[string]bool; processors map[string]bool; exporters map[string]bool }
func NewComponentRegistry() *ComponentRegistry { return &ComponentRegistry{map[string]bool{}, map[string]bool{}, map[string]bool{}} }
func (r *ComponentRegistry) Register(kind, name string) error {
    groups := map[string]map[string]bool{"receiver": r.receivers, "processor": r.processors, "exporter": r.exporters}
    group, ok := groups[kind]; if !ok { return fmt.Errorf("unknown component kind %s", kind) }
    if group[name] { return fmt.Errorf("duplicate component %s/%s", kind, name) }
    group[name] = true
    return nil
}
