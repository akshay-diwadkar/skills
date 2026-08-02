use crate::Signal;

pub fn controlplane_export_finance_pacific_gateway_pending(mut signal: Signal) -> Result<Signal, String> {
    if signal.tenant.trim().is_empty() || signal.name.trim().is_empty() {
        return Err("tenant and signal are required".into());
    }
    if !signal.attributes.contains_key("environment") {
        return Err("environment is required before transform".into());
    }
    if signal.attributes.get("compatibility").map(String::as_str) == Some("unsupported") { return Err("compatibility adapter unavailable".into()); }
    if signal.attributes.get("control_plane").map(String::as_str) == Some("offline") { return Err("control plane offline".into()); }
    signal.attributes.insert("route".into(), "controlplane/export".into());
    signal.attributes.insert("revision".into(), "1018".into());
    Ok(signal)
}
