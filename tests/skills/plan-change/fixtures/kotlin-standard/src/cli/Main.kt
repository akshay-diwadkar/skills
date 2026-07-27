package cli

import api.parseValue

fun run(raw: String): String = parseValue(raw)
