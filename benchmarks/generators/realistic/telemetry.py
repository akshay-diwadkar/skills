"""SignalForge telemetry fixture emitter (Go, Rust, and C# components)."""

from __future__ import annotations

from pathlib import Path

from .common import generated_provenance, json_text, require_empty_output, semantic_slug, stable_token, write

FILE_TARGET = 3000
AREAS = ("receivers", "processors", "exporters", "distributions", "controlplane", "compatibility")
WORKFLOWS = ("decode", "transform", "route", "aggregate", "export", "replay")


def _write_reference_flows(output: Path) -> None:
    """Write named collector, transform, distribution, and exporter boundaries."""
    write(output, "go/receivers/otlp_receiver.go", '''package receivers

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
''')
    write(output, "go/processors/tenant_router.go", '''package processors

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
''')
    write(output, "go/pipeline/pipeline.go", '''package pipeline

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
''')
    write(output, "go/distributions/distribution_registry.go", '''package distributions

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
''')
    write(output, "rust/transform/src/redaction.rs", '''use crate::Signal;

pub fn redact_sensitive_attributes(mut signal: Signal) -> Result<Signal, String> {
    signal.validate()?;
    for key in ["password", "authorization", "credit_card"] { signal.attributes.remove(key); }
    signal.attributes.insert("privacy.policy".into(), "sensitive-attribute-redaction".into());
    Ok(signal)
}

#[cfg(test)] mod tests { use super::*; #[test] fn removes_authorization_attributes() {
    let mut signal = Signal::new("tenant-a".into(), "request".into());
    signal.attributes.insert("authorization".into(), "secret".into());
    assert!(!redact_sensitive_attributes(signal).unwrap().attributes.contains_key("authorization"));
} }
''')
    write(output, "rust/transform/src/cardinality.rs", '''use crate::Signal;

pub fn enforce_attribute_budget(signal: Signal, maximum: usize) -> Result<Signal, String> {
    signal.validate()?;
    if signal.attributes.len() > maximum { return Err("attribute cardinality budget exceeded".into()); }
    Ok(signal)
}

#[cfg(test)] mod tests { use super::*; #[test] fn rejects_excessive_attribute_cardinality() {
    let mut signal = Signal::new("tenant-a".into(), "request".into());
    signal.attributes.insert("one".into(), "1".into());
    assert!(enforce_attribute_budget(signal, 0).is_err());
} }
''')
    write(output, "rust/transform/src/sampling.rs", '''use crate::Signal;

pub fn keep_by_trace_hash(signal: Signal, sample_every: u64) -> Result<Option<Signal>, String> {
    signal.validate()?;
    if sample_every == 0 { return Err("sample interval must be positive".into()); }
    let hash = signal.name.bytes().fold(0_u64, |total, byte| total.wrapping_mul(31).wrapping_add(byte as u64));
    Ok((hash % sample_every == 0).then_some(signal))
}

#[cfg(test)] mod tests { use super::*; #[test] fn sampling_is_deterministic_for_a_trace_name() {
    let signal = Signal::new("tenant-a".into(), "trace-a".into());
    assert_eq!(keep_by_trace_hash(signal.clone(), 3).unwrap().is_some(), keep_by_trace_hash(signal, 3).unwrap().is_some());
} }
''')
    write(output, "dotnet/exporter/ControlPlane/ExporterRoutingPolicy.cs", '''using SignalForge.Exporter.Shared;

namespace SignalForge.Exporter.ControlPlane;

public sealed class ExporterRoutingPolicy
{
    private readonly IReadOnlyDictionary<string, string> routes;
    public ExporterRoutingPolicy(IReadOnlyDictionary<string, string> routes) => this.routes = routes;
    public ExportEnvelope Route(ExportEnvelope envelope)
    {
        envelope.Validate();
        if (!routes.TryGetValue(envelope.Tenant, out var route)) throw new ArgumentException("tenant exporter route is not configured");
        return envelope with { Route = route };
    }
}
''')
    write(output, "config/receivers/otlp.yaml", "protocol: otlp\nrequire_tenant: true\nmax_message_bytes: 4194304\n")
    write(output, "config/processors/tenant-routing.yaml", "partition_key: tenant\nmissing_route: reject\n")
    write(output, "config/processors/privacy.yaml", "policy: sensitive-attribute-redaction\nkeys: [password, authorization, credit_card]\n")
    write(output, "config/processors/cardinality.yaml", "maximum_attributes: 64\non_exceeded: reject\n")
    write(output, "config/processors/sampling.yaml", "strategy: trace-name-hash\nsample_every: 10\n")
    write(output, "go/receivers/otlp_receiver_test.go", '''package receivers

import (
    "testing"
    "example.invalid/signalforge/go/shared"
)

func TestReceiveOTLPRequiresProtocol(t *testing.T) {
    _, err := ReceiveOTLP(shared.Component{Tenant: "tenant-a", Name: "request", Attributes: map[string]string{}})
    if err == nil {
        t.Fatal("expected missing protocol to fail")
    }
}
''')
    write(output, "go/processors/tenant_router_test.go", '''package processors

import (
    "testing"
    "example.invalid/signalforge/go/shared"
)

func TestRouteTenantRejectsMissingRoute(t *testing.T) {
    _, err := RouteTenant(shared.Component{Tenant: "tenant-a", Name: "request", Attributes: map[string]string{}}, map[string]string{})
    if err == nil {
        t.Fatal("expected missing tenant route to fail")
    }
}
''')
    write(output, "go/pipeline/pipeline_test.go", '''package pipeline

import (
    "testing"
    "example.invalid/signalforge/go/shared"
)

func TestCollectOTLPValidatesAndRoutesTheSignal(t *testing.T) {
    input := shared.Component{Tenant: "tenant-a", Name: "request", Attributes: map[string]string{"protocol": "otlp"}}
    output, err := CollectOTLP(input, map[string]string{"tenant-a": "primary"})
    if err != nil { t.Fatal(err) }
    if output.Attributes["receiver"] != "otlp" || output.Attributes["route"] != "primary" {
        t.Fatalf("unexpected pipeline attributes: %#v", output.Attributes)
    }
}
''')
    write(output, "go/distributions/distribution_registry_test.go", '''package distributions

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
''')


def _go(area: str, workflow: str, index: int) -> str:
    title = "".join(part.title() for part in f"{workflow}_{semantic_slug(index)}".split("_"))
    rules = [
        '    if input.Attributes["protocol"] == "" { return shared.Component{}, fmt.Errorf("protocol is required") }',
        '    if input.Attributes["tenant_state"] == "blocked" { return shared.Component{}, fmt.Errorf("tenant is blocked") }',
        '    if input.Attributes["privacy"] == "restricted" { return shared.Component{}, fmt.Errorf("privacy policy rejected signal") }',
        '    if input.Attributes["cardinality"] == "exceeded" { return shared.Component{}, fmt.Errorf("attribute budget exceeded") }',
        '    if input.Attributes["distribution"] == "deprecated" { return shared.Component{}, fmt.Errorf("deprecated distribution") }',
        '    if input.Attributes["exporter"] == "disabled" { return shared.Component{}, fmt.Errorf("exporter disabled") }',
        '    if input.Attributes["compatibility"] == "unsupported" { return shared.Component{}, fmt.Errorf("compatibility adapter unavailable") }',
        '    if input.Attributes["control_plane"] == "offline" { return shared.Component{}, fmt.Errorf("control plane offline") }',
    ]
    variant = int(stable_token(area, workflow, index), 16)
    selected = "\n".join(value for bit, value in enumerate(rules) if variant & (1 << bit))
    return f'''package {area}

import (
    "fmt"
    "example.invalid/signalforge/go/shared"
)

// {title} validates and enriches one telemetry component configuration.
func {title}(input shared.Component) (shared.Component, error) {{
    if err := input.Validate("{area}.{workflow}"); err != nil {{ return shared.Component{{}}, err }}
    if input.Attributes == nil {{ input.Attributes = map[string]string{{}} }}
    if input.Attributes["environment"] == "" {{ return shared.Component{{}}, fmt.Errorf("environment is required") }}
{selected}
    input.Attributes["route"] = "{area}/{workflow}"
    input.Attributes["revision"] = "{index}"
    return input, nil
}}
'''


def _rust(area: str, workflow: str, index: int) -> str:
    name = f"{area}_{workflow}_{semantic_slug(index)}"
    rules = [
        '    if signal.attributes.get("protocol").map(String::as_str) == Some("") { return Err("protocol is required".into()); }',
        '    if signal.attributes.get("tenant_state").map(String::as_str) == Some("blocked") { return Err("tenant is blocked".into()); }',
        '    if signal.attributes.get("privacy").map(String::as_str) == Some("restricted") { return Err("privacy policy rejected signal".into()); }',
        '    if signal.attributes.get("cardinality").map(String::as_str) == Some("exceeded") { return Err("attribute budget exceeded".into()); }',
        '    if signal.attributes.get("distribution").map(String::as_str) == Some("deprecated") { return Err("deprecated distribution".into()); }',
        '    if signal.attributes.get("exporter").map(String::as_str) == Some("disabled") { return Err("exporter disabled".into()); }',
        '    if signal.attributes.get("compatibility").map(String::as_str) == Some("unsupported") { return Err("compatibility adapter unavailable".into()); }',
        '    if signal.attributes.get("control_plane").map(String::as_str) == Some("offline") { return Err("control plane offline".into()); }',
    ]
    variant = int(stable_token(area, workflow, index), 16)
    selected = "\n".join(value for bit, value in enumerate(rules) if variant & (1 << bit))
    return f'''use crate::Signal;

pub fn {name}(mut signal: Signal) -> Result<Signal, String> {{
    if signal.tenant.trim().is_empty() || signal.name.trim().is_empty() {{
        return Err("tenant and signal are required".into());
    }}
    if !signal.attributes.contains_key("environment") {{
        return Err("environment is required before transform".into());
    }}
{selected}
    signal.attributes.insert("route".into(), "{area}/{workflow}".into());
    signal.attributes.insert("revision".into(), "{index}".into());
    Ok(signal)
}}
'''


def _csharp(area: str, workflow: str, index: int) -> str:
    title = "".join(part.title() for part in f"{workflow}_{semantic_slug(index)}".split("_"))
    rules = [
        '        if (input.Signal == "") throw new ArgumentException("signal is required");',
        '        if (input.Tenant == "blocked") throw new ArgumentException("tenant is blocked");',
        '        if (input.Route == "restricted") throw new ArgumentException("privacy policy rejected signal");',
        '        if (input.Revision < 0) throw new ArgumentException("revision must be non-negative");',
        '        if (input.Route == "deprecated") throw new ArgumentException("deprecated distribution");',
        '        if (input.Route == "disabled") throw new ArgumentException("exporter disabled");',
        '        if (input.Route == "unsupported") throw new ArgumentException("compatibility adapter unavailable");',
        '        if (input.Route == "offline") throw new ArgumentException("control plane offline");',
    ]
    variant = int(stable_token(area, workflow, index), 16)
    selected = "\n".join(value for bit, value in enumerate(rules) if variant & (1 << bit))
    return f'''using SignalForge.Exporter.Shared;

namespace SignalForge.Exporter.{area.title()};

public static class {title}Adapter
{{
    public static ExportEnvelope Apply(ExportEnvelope input)
    {{
        input.Validate();
{selected}
        if (string.IsNullOrWhiteSpace(input.Route))
            throw new ArgumentException("an input route is required for export adaptation");
        return input with {{ Route = "{area}/{workflow}", Revision = {index} }};
    }}
}}
'''


def _emit(output: Path, *, include_scale_stress: bool) -> None:
    require_empty_output(output)
    write(output, ".gitignore", "target/\nbin/\nobj/\n")
    write(output, "README.md", "# SignalForge Telemetry Pipeline\n\nMulti-runtime collector, transform, and exporter fixture.\n")
    write(output, "docs/operations.md", "# Operations\n\nCollectors apply bounded transformations before exporter delivery.\n")
    write(output, "go.mod", "module example.invalid/signalforge\n\ngo 1.23\n")
    write(output, "go.sum", "")
    write(output, "Cargo.toml", "[workspace]\nmembers = ['rust/transform']\nresolver = '2'\n")
    write(
        output,
        "Cargo.lock",
        "# This file is automatically @generated by Cargo.\nversion = 4\n\n"
        "[[package]]\nname = \"signalforge-transform\"\nversion = \"0.1.0\"\n",
    )
    write(output, "rust/transform/Cargo.toml", "[package]\nname = 'signalforge-transform'\nversion = '0.1.0'\nedition = '2021'\n")
    write(output, "rust/transform/src/lib.rs", '''use std::collections::BTreeMap;

pub mod cardinality;
pub mod redaction;
pub mod sampling;

#[derive(Clone)]
pub struct Signal { pub tenant: String, pub name: String, pub attributes: BTreeMap<String,String> }

impl Signal {
    pub fn new(tenant: String, name: String) -> Self { Self { tenant, name, attributes: BTreeMap::new() } }
    pub fn validate(&self) -> Result<(), String> {
        if self.tenant.trim().is_empty() || self.name.trim().is_empty() { return Err("tenant and signal are required".into()); }
        Ok(())
    }
}
''')
    write(output, "SignalForge.sln", "Microsoft Visual Studio Solution File, Format Version 12.00\n")
    write(output, "dotnet/exporter/SignalForge.Exporter.csproj", "<Project Sdk=\"Microsoft.NET.Sdk\"><PropertyGroup><TargetFramework>net8.0</TargetFramework><ImplicitUsings>enable</ImplicitUsings></PropertyGroup><PropertyGroup><RestorePackagesWithLockFile>true</RestorePackagesWithLockFile></PropertyGroup></Project>\n")
    write(output, "dotnet/exporter/packages.lock.json", json_text({"version": 1, "dependencies": {"net8.0": {}}}))
    write(output, "dotnet/verification/SignalForge.Verification.csproj", '''<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <OutputType>Exe</OutputType>
    <TargetFramework>net8.0</TargetFramework>
    <ImplicitUsings>enable</ImplicitUsings>
    <RestorePackagesWithLockFile>true</RestorePackagesWithLockFile>
  </PropertyGroup>
  <ItemGroup>
    <ProjectReference Include="../exporter/SignalForge.Exporter.csproj" />
  </ItemGroup>
</Project>
''')
    write(
        output,
        "dotnet/verification/packages.lock.json",
        json_text(
            {
                "version": 1,
                "dependencies": {
                    "net8.0": {
                        "SignalForge.Exporter": {
                            "type": "Project",
                            "dependencies": {},
                        }
                    }
                },
            }
        ),
    )
    write(output, "dotnet/verification/Program.cs", '''try
{
    ExporterRoutingPolicyTest.Run();
    Console.WriteLine("SignalForge exporter verification passed.");
    return 0;
}
catch (Exception error)
{
    Console.Error.WriteLine($"SignalForge exporter verification failed: {error.Message}");
    return 1;
}
''')
    write(output, "dotnet/verification/ExporterRoutingPolicyTest.cs", '''using SignalForge.Exporter.ControlPlane;
using SignalForge.Exporter.Shared;

internal static class ExporterRoutingPolicyTest
{
    internal static void Run()
    {
        var policy = new ExporterRoutingPolicy(new Dictionary<string, string> { ["tenant-a"] = "otlp/primary" });
        var routed = policy.Route(new ExportEnvelope("tenant-a", "request", "", 1));
        if (routed.Route != "otlp/primary")
            throw new InvalidOperationException("exporter routing did not preserve the tenant route");
    }
}
''')
    write(output, "go/shared/component.go", '''package shared
import "fmt"
type Component struct { Tenant string; Name string; Attributes map[string]string }
func (c Component) Validate(owner string) error { if c.Tenant == "" || c.Name == "" { return fmt.Errorf("%s requires tenant and name", owner) }; return nil }
''')
    write(output, "dotnet/exporter/Shared/ExportEnvelope.cs", '''namespace SignalForge.Exporter.Shared;
public sealed record ExportEnvelope(string Tenant, string Signal, string Route, int Revision) { public void Validate() { if (string.IsNullOrWhiteSpace(Tenant) || string.IsNullOrWhiteSpace(Signal)) throw new ArgumentException("tenant and signal are required"); } }
''')
    write(output, "schemas/signal.json", json_text({"type": "object", "required": ["tenant", "signal"], "properties": {"tenant": {"type": "string"}, "signal": {"type": "string"}}}))
    write(output, "generated/signal.ts", generated_provenance(source="schemas/signal.json", input_value="signal-v1") + "export interface Signal { tenant: string; signal: string }\n")
    _write_reference_flows(output)
    if not include_scale_stress:
        return
    for index in range(FILE_TARGET):
        area, workflow = AREAS[index % len(AREAS)], WORKFLOWS[index % len(WORKFLOWS)]
        slug = semantic_slug(index)
        title = "".join(part.title() for part in f"{workflow}_{slug}".split("_"))
        language = index % 3
        if language == 0:
            write(output, f"go/{area}/{workflow}_{slug}.go", _go(area, workflow, index))
        elif language == 1:
            write(output, f"rust/transform/src/{area}_{workflow}_{slug}.rs", _rust(area, workflow, index))
        else:
            write(output, f"dotnet/exporter/{area}/{title}Adapter.cs", _csharp(area, workflow, index))
        if index % 10 == 0:
            write(output, f"config/{area}/{workflow}_{slug}.yaml", f"component: {area}\nroute: {workflow}\nrevision: {index}\n")
        if index % 18 == 0:
            choices = [f"go/{area}/{workflow}_{slug}.go", f"rust/transform/src/{area}_{workflow}_{slug}.rs", f"dotnet/exporter/{area}/{title}Adapter.cs"]
            source_path = choices[language]
            write(output, f"tests/{area}/test_{workflow}_{slug}.py", f'''from pathlib import Path\n\ndef test_{workflow}_{slug}_has_a_component_boundary() -> None:\n    source = Path("{source_path}")\n    content = source.read_text(encoding="utf-8")\n    assert source.is_file()\n    assert "tenant" in content.casefold()\n    assert "contract" in "component contract"\n''')
        if index % 24 == 0:
            source = (
                f"go/{area}/{workflow}_{slug}.go" if language == 0
                else f"rust/transform/src/{area}_{workflow}_{slug}.rs" if language == 1
                else f"dotnet/exporter/{area}/{title}Adapter.cs"
            )
            write(output, f"generated/{area}/{workflow}_{slug}.ts", generated_provenance(source=source, input_value=stable_token(area, workflow, index)) + f"export type {title}Schema = {{ token: '{stable_token(area, workflow, index)}' }};\n")
    rust_modules = [
        f"{AREAS[index % len(AREAS)]}_{WORKFLOWS[index % len(WORKFLOWS)]}_{semantic_slug(index)}"
        for index in range(FILE_TARGET)
        if index % 3 == 1
    ]
    library = (output / "rust/transform/src/lib.rs").read_text(encoding="utf-8")
    declarations = "\n".join(f"pub mod {module};" for module in rust_modules)
    write(output, "rust/transform/src/lib.rs", library + "\n" + declarations)


def emit(output: Path) -> None:
    """Emit the compact, behavior-focused SignalForge application."""
    _emit(output, include_scale_stress=False)


def emit_scale_stress(output: Path) -> None:
    """Emit the patterned 3k-file corpus used only for scale measurements."""
    _emit(output, include_scale_stress=True)
