using SignalForge.Exporter.Shared;

namespace SignalForge.Exporter.Compatibility;

public static class ReplayIndustrialCoastalSchedulerSettledAdapter
{
    public static ExportEnvelope Apply(ExportEnvelope input)
    {
        input.Validate();
        if (input.Signal == "") throw new ArgumentException("signal is required");
        if (input.Tenant == "blocked") throw new ArgumentException("tenant is blocked");
        if (input.Route == "deprecated") throw new ArgumentException("deprecated distribution");
        if (input.Route == "unsupported") throw new ArgumentException("compatibility adapter unavailable");
        if (input.Route == "offline") throw new ArgumentException("control plane offline");
        if (string.IsNullOrWhiteSpace(input.Route))
            throw new ArgumentException("an input route is required for export adaptation");
        return input with { Route = "compatibility/replay", Revision = 2249 };
    }
}
