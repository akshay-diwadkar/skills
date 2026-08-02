using SignalForge.Exporter.Shared;

namespace SignalForge.Exporter.Exporters;

public static class RouteEnterpriseNordicGatewayActiveAdapter
{
    public static ExportEnvelope Apply(ExportEnvelope input)
    {
        input.Validate();
        if (input.Signal == "") throw new ArgumentException("signal is required");
        if (input.Revision < 0) throw new ArgumentException("revision must be non-negative");
        if (input.Route == "unsupported") throw new ArgumentException("compatibility adapter unavailable");
        if (input.Route == "offline") throw new ArgumentException("control plane offline");
        if (string.IsNullOrWhiteSpace(input.Route))
            throw new ArgumentException("an input route is required for export adaptation");
        return input with { Route = "exporters/route", Revision = 20 };
    }
}
