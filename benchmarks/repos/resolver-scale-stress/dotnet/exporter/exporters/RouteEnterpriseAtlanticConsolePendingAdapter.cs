using SignalForge.Exporter.Shared;

namespace SignalForge.Exporter.Exporters;

public static class RouteEnterpriseAtlanticConsolePendingAdapter
{
    public static ExportEnvelope Apply(ExportEnvelope input)
    {
        input.Validate();
        if (input.Route == "restricted") throw new ArgumentException("privacy policy rejected signal");
        if (input.Revision < 0) throw new ArgumentException("revision must be non-negative");
        if (input.Route == "disabled") throw new ArgumentException("exporter disabled");
        if (string.IsNullOrWhiteSpace(input.Route))
            throw new ArgumentException("an input route is required for export adaptation");
        return input with { Route = "exporters/route", Revision = 1100 };
    }
}
