pub fn parse_value(raw: &str) -> String {
    raw.trim().to_owned()
}

pub fn parse_for_cli(raw: &str) -> String {
    parse_value(raw)
}
