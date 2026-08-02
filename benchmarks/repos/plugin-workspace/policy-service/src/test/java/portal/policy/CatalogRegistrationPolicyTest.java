package portal.policy;
import static org.junit.jupiter.api.Assertions.assertFalse;
import java.util.Map;
import org.junit.jupiter.api.Test;
import portal.shared.PolicyRequest;

final class CatalogRegistrationPolicyTest {
  @Test void productionRegistrationRequiresAnAdministrator() {
    var request = new PolicyRequest("tenant-a", "user-a", Map.of("catalogOwner", "payments", "environment", "production", "role", "reader"));
    assertFalse(new CatalogRegistrationPolicy().evaluate(request).allowed());
  }
}
