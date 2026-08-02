using SignalForge.Exporter.Shared;

namespace SignalForge.Exporter.Exporters;

public static class RouteFinanceAtlanticArchiveActiveAdapter
{
    public static ExportEnvelope Apply(ExportEnvelope input)
    {
        input.Validate();
        if (input.Route == "disabled") throw new ArgumentException("exporter disabled");
        if (input.Route == "offline") throw new ArgumentException("control plane offline");
        if (string.IsNullOrWhiteSpace(input.Route))
            throw new ArgumentException("an input route is required for export adaptation");
        return input with { Route = "exporters/route", Revision = 908 };
    }
}
