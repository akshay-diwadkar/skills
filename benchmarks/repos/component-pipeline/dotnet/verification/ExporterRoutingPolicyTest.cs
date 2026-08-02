using SignalForge.Exporter.ControlPlane;
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
