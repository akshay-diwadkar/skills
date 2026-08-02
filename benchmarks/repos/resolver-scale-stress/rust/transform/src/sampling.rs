use crate::Signal;

pub fn keep_by_trace_hash(signal: Signal, sample_every: u64) -> Result<Option<Signal>, String> {
    signal.validate()?;
    if sample_every == 0 { return Err("sample interval must be positive".into()); }
    let hash = signal.name.bytes().fold(0_u64, |total, byte| total.wrapping_mul(31).wrapping_add(byte as u64));
    Ok((hash % sample_every == 0).then_some(signal))
}

#[cfg(test)] mod tests { use super::*; #[test] fn sampling_is_deterministic_for_a_trace_name() {
    let signal = Signal::new("tenant-a".into(), "trace-a".into());
    assert_eq!(keep_by_trace_hash(signal.clone(), 3).unwrap().is_some(), keep_by_trace_hash(signal, 3).unwrap().is_some());
} }
