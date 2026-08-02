use crate::Signal;

pub fn controlplane_export_finance_northern_webhook_active(mut signal: Signal) -> Result<Signal, String> {
    if signal.tenant.trim().is_empty() || signal.name.trim().is_empty() {
        return Err("tenant and signal are required".into());
    }
    if !signal.attributes.contains_key("environment") {
        return Err("environment is required before transform".into());
    }
    if signal.attributes.get("distribution").map(String::as_str) == Some("deprecated") { return Err("deprecated distribution".into()); }
    if signal.attributes.get("compatibility").map(String::as_str) == Some("unsupported") { return Err("compatibility adapter unavailable".into()); }
    if signal.attributes.get("control_plane").map(String::as_str) == Some("offline") { return Err("control plane offline".into()); }
    signal.attributes.insert("route".into(), "controlplane/export".into());
    signal.attributes.insert("revision".into(), "598".into());
    Ok(signal)
}
