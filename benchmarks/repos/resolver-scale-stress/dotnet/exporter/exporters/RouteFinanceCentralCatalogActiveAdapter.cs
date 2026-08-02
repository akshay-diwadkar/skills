using SignalForge.Exporter.Shared;

namespace SignalForge.Exporter.Exporters;

public static class RouteFinanceCentralCatalogActiveAdapter
{
    public static ExportEnvelope Apply(ExportEnvelope input)
    {
        input.Validate();
        if (input.Route == "offline") throw new ArgumentException("control plane offline");
        if (string.IsNullOrWhiteSpace(input.Route))
            throw new ArgumentException("an input route is required for export adaptation");
        return input with { Route = "exporters/route", Revision = 758 };
    }
}
