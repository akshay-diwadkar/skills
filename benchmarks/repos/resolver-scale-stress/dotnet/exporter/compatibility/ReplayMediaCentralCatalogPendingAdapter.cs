using SignalForge.Exporter.Shared;

namespace SignalForge.Exporter.Compatibility;

public static class ReplayMediaCentralCatalogPendingAdapter
{
    public static ExportEnvelope Apply(ExportEnvelope input)
    {
        input.Validate();
        if (input.Signal == "") throw new ArgumentException("signal is required");
        if (input.Route == "restricted") throw new ArgumentException("privacy policy rejected signal");
        if (input.Revision < 0) throw new ArgumentException("revision must be non-negative");
        if (input.Route == "deprecated") throw new ArgumentException("deprecated distribution");
        if (input.Route == "unsupported") throw new ArgumentException("compatibility adapter unavailable");
        if (string.IsNullOrWhiteSpace(input.Route))
            throw new ArgumentException("an input route is required for export adaptation");
        return input with { Route = "compatibility/replay", Revision = 1757 };
    }
}
