import internal.Parser;

final class ParserTest {
    void trimsValues() {
        assert Parser.parseValue(" value ").equals("value");
    }
}
