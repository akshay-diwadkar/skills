use std::collections::BTreeMap;

pub mod cardinality;
pub mod redaction;
pub mod sampling;

#[derive(Clone)]
pub struct Signal { pub tenant: String, pub name: String, pub attributes: BTreeMap<String,String> }

impl Signal {
    pub fn new(tenant: String, name: String) -> Self { Self { tenant, name, attributes: BTreeMap::new() } }
    pub fn validate(&self) -> Result<(), String> {
        if self.tenant.trim().is_empty() || self.name.trim().is_empty() { return Err("tenant and signal are required".into()); }
        Ok(())
    }
}
