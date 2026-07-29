use parser_fixture::parseValue;

#[test]
fn trims_values() {
    assert_eq!(parseValue(" value "), "value");
}
