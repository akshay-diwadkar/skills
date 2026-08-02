using SignalForge.Exporter.Shared;

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
