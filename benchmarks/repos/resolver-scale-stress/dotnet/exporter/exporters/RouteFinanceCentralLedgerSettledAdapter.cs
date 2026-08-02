using SignalForge.Exporter.Shared;

namespace SignalForge.Exporter.Exporters;

public static class RouteFinanceCentralLedgerSettledAdapter
{
    public static ExportEnvelope Apply(ExportEnvelope input)
    {
        input.Validate();

        if (string.IsNullOrWhiteSpace(input.Route))
            throw new ArgumentException("an input route is required for export adaptation");
        return input with { Route = "exporters/route", Revision = 2858 };
    }
}
