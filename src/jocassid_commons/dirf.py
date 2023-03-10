

def dirf(symbols, pattern='', starts_with=False, ignore_case=True):
    """
    :param symbols:
    :param pattern:
    :param starts_with:
    :param ignore_case:
    """

    if ignore_case:
        pattern = pattern.lower()

    def as_is(a_symbol):
        return a_symbol

    def to_lower(a_symbol):
        return a_symbol.lower()

    def contains(a_symbol, a_pattern):
        return a_pattern in a_symbol

    def startswith(a_symbol, a_pattern):
        return a_symbol.startswith(a_pattern)

    transform_func = as_is
    filter_func = contains

    if ignore_case:
        transform_func = to_lower

    if starts_with:
        filter_func = startswith

    filtered = []
    for symbol in symbols:
        symbol = transform_func(symbol)
        if filter_func(symbol, pattern):
            filtered.append(symbol)
    return filtered
