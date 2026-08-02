using SignalForge.Exporter.Shared;

namespace SignalForge.Exporter.Exporters;

public static class RouteRetailPacificSchedulerSettledAdapter
{
    public static ExportEnvelope Apply(ExportEnvelope input)
    {
        input.Validate();
        if (input.Route == "deprecated") throw new ArgumentException("deprecated distribution");
        if (input.Route == "disabled") throw new ArgumentException("exporter disabled");
        if (string.IsNullOrWhiteSpace(input.Route))
            throw new ArgumentException("an input route is required for export adaptation");
        return input with { Route = "exporters/route", Revision = 2216 };
    }
}
