use crate::Signal;

pub fn controlplane_export_retail_northern_scheduler_settled(mut signal: Signal) -> Result<Signal, String> {
    if signal.tenant.trim().is_empty() || signal.name.trim().is_empty() {
        return Err("tenant and signal are required".into());
    }
    if !signal.attributes.contains_key("environment") {
        return Err("environment is required before transform".into());
    }
    if signal.attributes.get("protocol").map(String::as_str) == Some("") { return Err("protocol is required".into()); }
    if signal.attributes.get("tenant_state").map(String::as_str) == Some("blocked") { return Err("tenant is blocked".into()); }
    if signal.attributes.get("privacy").map(String::as_str) == Some("restricted") { return Err("privacy policy rejected signal".into()); }
    if signal.attributes.get("cardinality").map(String::as_str) == Some("exceeded") { return Err("attribute budget exceeded".into()); }
    if signal.attributes.get("distribution").map(String::as_str) == Some("deprecated") { return Err("deprecated distribution".into()); }
    if signal.attributes.get("exporter").map(String::as_str) == Some("disabled") { return Err("exporter disabled".into()); }
    signal.attributes.insert("route".into(), "controlplane/export".into());
    signal.attributes.insert("revision".into(), "2296".into());
    Ok(signal)
}
