use crate::Signal;

pub fn processors_transform_media_atlantic_stream_active(mut signal: Signal) -> Result<Signal, String> {
    if signal.tenant.trim().is_empty() || signal.name.trim().is_empty() {
        return Err("tenant and signal are required".into());
    }
    if !signal.attributes.contains_key("environment") {
        return Err("environment is required before transform".into());
    }

    signal.attributes.insert("route".into(), "processors/transform".into());
    signal.attributes.insert("revision".into(), "307".into());
    Ok(signal)
}
