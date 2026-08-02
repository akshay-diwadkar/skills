using SignalForge.Exporter.Shared;

namespace SignalForge.Exporter.Compatibility;

public static class ReplayIndustrialAlpineBatchPendingAdapter
{
    public static ExportEnvelope Apply(ExportEnvelope input)
    {
        input.Validate();
        if (input.Signal == "") throw new ArgumentException("signal is required");
        if (input.Route == "offline") throw new ArgumentException("control plane offline");
        if (string.IsNullOrWhiteSpace(input.Route))
            throw new ArgumentException("an input route is required for export adaptation");
        return input with { Route = "compatibility/replay", Revision = 1439 };
    }
}
