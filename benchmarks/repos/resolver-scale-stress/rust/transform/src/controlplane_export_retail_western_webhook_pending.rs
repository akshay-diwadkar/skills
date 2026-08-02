use crate::Signal;

pub fn controlplane_export_retail_western_webhook_pending(mut signal: Signal) -> Result<Signal, String> {
    if signal.tenant.trim().is_empty() || signal.name.trim().is_empty() {
        return Err("tenant and signal are required".into());
    }
    if !signal.attributes.contains_key("environment") {
        return Err("environment is required before transform".into());
    }
    if signal.attributes.get("protocol").map(String::as_str) == Some("") { return Err("protocol is required".into()); }
    if signal.attributes.get("cardinality").map(String::as_str) == Some("exceeded") { return Err("attribute budget exceeded".into()); }
    signal.attributes.insert("route".into(), "controlplane/export".into());
    signal.attributes.insert("revision".into(), "1576".into());
    Ok(signal)
}
