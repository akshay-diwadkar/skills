using SignalForge.Exporter.Shared;

namespace SignalForge.Exporter.Compatibility;

public static class ReplayMediaAtlanticWebhookSettledAdapter
{
    public static ExportEnvelope Apply(ExportEnvelope input)
    {
        input.Validate();
        if (input.Route == "restricted") throw new ArgumentException("privacy policy rejected signal");
        if (input.Route == "deprecated") throw new ArgumentException("deprecated distribution");
        if (string.IsNullOrWhiteSpace(input.Route))
            throw new ArgumentException("an input route is required for export adaptation");
        return input with { Route = "compatibility/replay", Revision = 2507 };
    }
}
