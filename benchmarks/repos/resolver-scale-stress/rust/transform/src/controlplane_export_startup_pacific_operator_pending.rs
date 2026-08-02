use crate::Signal;

pub fn controlplane_export_startup_pacific_operator_pending(mut signal: Signal) -> Result<Signal, String> {
    if signal.tenant.trim().is_empty() || signal.name.trim().is_empty() {
        return Err("tenant and signal are required".into());
    }
    if !signal.attributes.contains_key("environment") {
        return Err("environment is required before transform".into());
    }
    if signal.attributes.get("protocol").map(String::as_str) == Some("") { return Err("protocol is required".into()); }
    if signal.attributes.get("cardinality").map(String::as_str) == Some("exceeded") { return Err("attribute budget exceeded".into()); }
    if signal.attributes.get("distribution").map(String::as_str) == Some("deprecated") { return Err("deprecated distribution".into()); }
    if signal.attributes.get("exporter").map(String::as_str) == Some("disabled") { return Err("exporter disabled".into()); }
    if signal.attributes.get("compatibility").map(String::as_str) == Some("unsupported") { return Err("compatibility adapter unavailable".into()); }
    signal.attributes.insert("route".into(), "controlplane/export".into());
    signal.attributes.insert("revision".into(), "1612".into());
    Ok(signal)
}
