use crate::Signal;

pub fn redact_sensitive_attributes(mut signal: Signal) -> Result<Signal, String> {
    signal.validate()?;
    for key in ["password", "authorization", "credit_card"] { signal.attributes.remove(key); }
    signal.attributes.insert("privacy.policy".into(), "sensitive-attribute-redaction".into());
    Ok(signal)
}

#[cfg(test)] mod tests { use super::*; #[test] fn removes_authorization_attributes() {
    let mut signal = Signal::new("tenant-a".into(), "request".into());
    signal.attributes.insert("authorization".into(), "secret".into());
    assert!(!redact_sensitive_attributes(signal).unwrap().attributes.contains_key("authorization"));
} }
