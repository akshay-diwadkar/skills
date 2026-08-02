using SignalForge.Exporter.Shared;

namespace SignalForge.Exporter.Compatibility;

public static class ReplayIndustrialCentralWebhookPendingAdapter
{
    public static ExportEnvelope Apply(ExportEnvelope input)
    {
        input.Validate();
        if (input.Route == "restricted") throw new ArgumentException("privacy policy rejected signal");
        if (input.Route == "disabled") throw new ArgumentException("exporter disabled");
        if (input.Route == "unsupported") throw new ArgumentException("compatibility adapter unavailable");
        if (input.Route == "offline") throw new ArgumentException("control plane offline");
        if (string.IsNullOrWhiteSpace(input.Route))
            throw new ArgumentException("an input route is required for export adaptation");
        return input with { Route = "compatibility/replay", Revision = 1559 };
    }
}
