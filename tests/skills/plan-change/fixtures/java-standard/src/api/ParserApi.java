package api;

import internal.Parser;

public final class ParserApi {
    public static String parseValue(String raw) {
        return Parser.parseValue(raw);
    }
}
