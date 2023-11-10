
from re import compile as re_compile
from traceback import walk_stack


def dirf(obj, pattern='', starts_with=False, ignore_case=True):
    """
    :param obj:
    :param pattern:
    :param starts_with:
    :param ignore_case:
    """
    if pattern:
        symbols = dir(obj)
    else:
        pattern = obj
        symbols = []
        # regex to filter out @py_assertN symbols added by pytest
        py_assert_regex = re_compile(r'@py_assert\d+')
        for frame, _ in walk_stack(None):
            for symbol in sorted(frame.f_locals.keys()):
                if py_assert_regex.fullmatch(symbol):
                    continue
                symbols.append(symbol)
            break

    compare_pattern = pattern.lower() if ignore_case else pattern

    filtered = []
    for symbol in symbols:
        compare_symbol = symbol.lower() if ignore_case else symbol
        if starts_with:
            if compare_symbol.startswith(compare_pattern):
                filtered.append(symbol)
            continue
        if compare_pattern in compare_symbol:
            filtered.append(symbol)
    return filtered
