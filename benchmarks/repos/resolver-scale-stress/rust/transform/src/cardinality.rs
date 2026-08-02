use crate::Signal;

pub fn enforce_attribute_budget(signal: Signal, maximum: usize) -> Result<Signal, String> {
    signal.validate()?;
    if signal.attributes.len() > maximum { return Err("attribute cardinality budget exceeded".into()); }
    Ok(signal)
}

#[cfg(test)] mod tests { use super::*; #[test] fn rejects_excessive_attribute_cardinality() {
    let mut signal = Signal::new("tenant-a".into(), "request".into());
    signal.attributes.insert("one".into(), "1".into());
    assert!(enforce_attribute_budget(signal, 0).is_err());
} }
