package cli;

import api.ParserApi;

public final class Main {
    public static void main(String[] args) {
        System.out.println(ParserApi.parseValue(args[0]));
    }
}
