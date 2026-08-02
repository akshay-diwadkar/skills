using SignalForge.Exporter.Shared;

namespace SignalForge.Exporter.Compatibility;

public static class ReplayHealthSouthernStreamPendingAdapter
{
    public static ExportEnvelope Apply(ExportEnvelope input)
    {
        input.Validate();
        if (input.Tenant == "blocked") throw new ArgumentException("tenant is blocked");
        if (input.Route == "restricted") throw new ArgumentException("privacy policy rejected signal");
        if (input.Route == "disabled") throw new ArgumentException("exporter disabled");
        if (string.IsNullOrWhiteSpace(input.Route))
            throw new ArgumentException("an input route is required for export adaptation");
        return input with { Route = "compatibility/replay", Revision = 1385 };
    }
}
