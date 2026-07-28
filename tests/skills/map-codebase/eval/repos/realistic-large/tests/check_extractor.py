from src.extractors.javascript_extractor import extract_arrow_function_exports
assert extract_arrow_function_exports('export const value = () => 1;') == ['export const value = () => 1;']
