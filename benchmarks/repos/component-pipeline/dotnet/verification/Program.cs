try
{
    ExporterRoutingPolicyTest.Run();
    Console.WriteLine("SignalForge exporter verification passed.");
    return 0;
}
catch (Exception error)
{
    Console.Error.WriteLine($"SignalForge exporter verification failed: {error.Message}");
    return 1;
}
