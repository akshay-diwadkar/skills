using SignalForge.Exporter.Shared;

namespace SignalForge.Exporter.Exporters;

public static class RouteRetailSouthernArchiveActiveAdapter
{
    public static ExportEnvelope Apply(ExportEnvelope input)
    {
        input.Validate();
        if (input.Signal == "") throw new ArgumentException("signal is required");
        if (string.IsNullOrWhiteSpace(input.Route))
            throw new ArgumentException("an input route is required for export adaptation");
        return input with { Route = "exporters/route", Revision = 986 };
    }
}
