package shared
import "fmt"
type Component struct { Tenant string; Name string; Attributes map[string]string }
func (c Component) Validate(owner string) error { if c.Tenant == "" || c.Name == "" { return fmt.Errorf("%s requires tenant and name", owner) }; return nil }
