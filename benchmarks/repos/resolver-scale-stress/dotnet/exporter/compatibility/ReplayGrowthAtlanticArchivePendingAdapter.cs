using SignalForge.Exporter.Shared;

namespace SignalForge.Exporter.Compatibility;

public static class ReplayGrowthAtlanticArchivePendingAdapter
{
    public static ExportEnvelope Apply(ExportEnvelope input)
    {
        input.Validate();
        if (input.Route == "deprecated") throw new ArgumentException("deprecated distribution");
        if (input.Route == "disabled") throw new ArgumentException("exporter disabled");
        if (input.Route == "unsupported") throw new ArgumentException("compatibility adapter unavailable");
        if (string.IsNullOrWhiteSpace(input.Route))
            throw new ArgumentException("an input route is required for export adaptation");
        return input with { Route = "compatibility/replay", Revision = 1901 };
    }
}
