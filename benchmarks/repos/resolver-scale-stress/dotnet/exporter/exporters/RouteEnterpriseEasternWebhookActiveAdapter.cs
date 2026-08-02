using SignalForge.Exporter.Shared;

namespace SignalForge.Exporter.Exporters;

public static class RouteEnterpriseEasternWebhookActiveAdapter
{
    public static ExportEnvelope Apply(ExportEnvelope input)
    {
        input.Validate();
        if (input.Tenant == "blocked") throw new ArgumentException("tenant is blocked");
        if (input.Revision < 0) throw new ArgumentException("revision must be non-negative");
        if (input.Route == "unsupported") throw new ArgumentException("compatibility adapter unavailable");
        if (string.IsNullOrWhiteSpace(input.Route))
            throw new ArgumentException("an input route is required for export adaptation");
        return input with { Route = "exporters/route", Revision = 560 };
    }
}
