package portal.shared;
import java.util.Map;

public record PolicyDecision(boolean allowed, String reason, Map<String,String> audit) {
  public static PolicyDecision denied(String reason) {
    return new PolicyDecision(false, reason, Map.of());
  }
}
