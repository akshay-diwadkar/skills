using SignalForge.Exporter.Shared;

namespace SignalForge.Exporter.Exporters;

public static class RouteEnterpriseNorthernBatchPendingAdapter
{
    public static ExportEnvelope Apply(ExportEnvelope input)
    {
        input.Validate();
        if (input.Tenant == "blocked") throw new ArgumentException("tenant is blocked");
        if (input.Route == "restricted") throw new ArgumentException("privacy policy rejected signal");
        if (string.IsNullOrWhiteSpace(input.Route))
            throw new ArgumentException("an input route is required for export adaptation");
        return input with { Route = "exporters/route", Revision = 1490 };
    }
}
