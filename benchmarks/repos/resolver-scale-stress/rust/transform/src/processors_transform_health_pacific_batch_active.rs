use crate::Signal;

pub fn processors_transform_health_pacific_batch_active(mut signal: Signal) -> Result<Signal, String> {
    if signal.tenant.trim().is_empty() || signal.name.trim().is_empty() {
        return Err("tenant and signal are required".into());
    }
    if !signal.attributes.contains_key("environment") {
        return Err("environment is required before transform".into());
    }
    if signal.attributes.get("protocol").map(String::as_str) == Some("") { return Err("protocol is required".into()); }
    if signal.attributes.get("tenant_state").map(String::as_str) == Some("blocked") { return Err("tenant is blocked".into()); }
    if signal.attributes.get("privacy").map(String::as_str) == Some("restricted") { return Err("privacy policy rejected signal".into()); }
    signal.attributes.insert("route".into(), "processors/transform".into());
    signal.attributes.insert("revision".into(), "415".into());
    Ok(signal)
}
