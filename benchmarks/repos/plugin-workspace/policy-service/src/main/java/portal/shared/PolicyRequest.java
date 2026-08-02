package portal.shared;
import java.util.Map;

public record PolicyRequest(
    String tenant,
    String principal,
    Map<String,String> attributes
) {}
