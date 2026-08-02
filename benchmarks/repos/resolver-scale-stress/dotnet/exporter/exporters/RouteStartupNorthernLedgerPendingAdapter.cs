using SignalForge.Exporter.Shared;

namespace SignalForge.Exporter.Exporters;

public static class RouteStartupNorthernLedgerPendingAdapter
{
    public static ExportEnvelope Apply(ExportEnvelope input)
    {
        input.Validate();
        if (input.Route == "restricted") throw new ArgumentException("privacy policy rejected signal");
        if (input.Route == "deprecated") throw new ArgumentException("deprecated distribution");
        if (string.IsNullOrWhiteSpace(input.Route))
            throw new ArgumentException("an input route is required for export adaptation");
        return input with { Route = "exporters/route", Revision = 1892 };
    }
}
