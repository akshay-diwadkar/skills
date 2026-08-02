namespace SignalForge.Exporter.Shared;
public sealed record ExportEnvelope(string Tenant, string Signal, string Route, int Revision) { public void Validate() { if (string.IsNullOrWhiteSpace(Tenant) || string.IsNullOrWhiteSpace(Signal)) throw new ArgumentException("tenant and signal are required"); } }
