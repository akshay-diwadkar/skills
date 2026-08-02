package distributions

import "testing"

func TestRegistryRejectsDuplicateComponents(t *testing.T) {
    registry := NewComponentRegistry()
    if err := registry.Register("receiver", "otlp"); err != nil {
        t.Fatal(err)
    }
    if err := registry.Register("receiver", "otlp"); err == nil {
        t.Fatal("expected duplicate registration to fail")
    }
}
