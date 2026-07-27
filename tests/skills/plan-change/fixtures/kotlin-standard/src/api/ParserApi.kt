package api

import internal.parseValue as parseInternalValue

fun parseValue(raw: String): String = parseInternalValue(raw)
