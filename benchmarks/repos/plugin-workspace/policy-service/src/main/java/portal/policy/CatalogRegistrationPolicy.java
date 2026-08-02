package portal.policy;

import java.util.Map;
import portal.shared.PolicyDecision;
import portal.shared.PolicyRequest;

public final class CatalogRegistrationPolicy {
  public PolicyDecision evaluate(PolicyRequest request) {
    if (!request.attributes().containsKey("catalogOwner")) return PolicyDecision.denied("catalog owner claim is required");
    boolean allowed = !"production".equals(request.attributes().get("environment")) || "admin".equals(request.attributes().get("role"));
    return new PolicyDecision(allowed, allowed ? "catalog registration accepted" : "production registration requires admin", Map.of("policy", "catalog-registration"));
  }
}
