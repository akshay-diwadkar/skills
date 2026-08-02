using SignalForge.Exporter.Shared;

namespace SignalForge.Exporter.Compatibility;

public static class ReplayMediaNordicArchiveSettledAdapter
{
    public static ExportEnvelope Apply(ExportEnvelope input)
    {
        input.Validate();

        if (string.IsNullOrWhiteSpace(input.Route))
            throw new ArgumentException("an input route is required for export adaptation");
        return input with { Route = "compatibility/replay", Revision = 2927 };
    }
}
