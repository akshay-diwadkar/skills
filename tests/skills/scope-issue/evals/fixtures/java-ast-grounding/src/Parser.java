final class Parser {
    static String parseValue(String raw) {
        return raw.trim();
    }
}

final class ParserApi {
    static String parseValue(String raw) {
        return Parser.parseValue(raw);
    }
}
