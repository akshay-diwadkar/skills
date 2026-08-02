use crate::Signal;

pub fn controlplane_export_startup_nordic_operator_active(mut signal: Signal) -> Result<Signal, String> {
    if signal.tenant.trim().is_empty() || signal.name.trim().is_empty() {
        return Err("tenant and signal are required".into());
    }
    if !signal.attributes.contains_key("environment") {
        return Err("environment is required before transform".into());
    }
    if signal.attributes.get("privacy").map(String::as_str) == Some("restricted") { return Err("privacy policy rejected signal".into()); }
    signal.attributes.insert("route".into(), "controlplane/export".into());
    signal.attributes.insert("revision".into(), "622".into());
    Ok(signal)
}
