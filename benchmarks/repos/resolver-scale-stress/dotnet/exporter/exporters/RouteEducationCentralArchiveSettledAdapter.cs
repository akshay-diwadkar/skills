using SignalForge.Exporter.Shared;

namespace SignalForge.Exporter.Exporters;

public static class RouteEducationCentralArchiveSettledAdapter
{
    public static ExportEnvelope Apply(ExportEnvelope input)
    {
        input.Validate();
        if (input.Signal == "") throw new ArgumentException("signal is required");
        if (input.Route == "restricted") throw new ArgumentException("privacy policy rejected signal");
        if (input.Route == "deprecated") throw new ArgumentException("deprecated distribution");
        if (input.Route == "unsupported") throw new ArgumentException("compatibility adapter unavailable");
        if (input.Route == "offline") throw new ArgumentException("control plane offline");
        if (string.IsNullOrWhiteSpace(input.Route))
            throw new ArgumentException("an input route is required for export adaptation");
        return input with { Route = "exporters/route", Revision = 2954 };
    }
}
