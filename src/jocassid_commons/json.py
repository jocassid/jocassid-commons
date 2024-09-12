
from collections import namedtuple
from enum import Enum
from itertools import chain
from math import ceil


def json_get(collection, default, *keys):
    """function to extract values from a dict of dicts like what is returned
    by json.load

    collection can be either a mapping or a list.
    keys can be keys (if collection is a mapping)
    or indexes (if collection is a list)"""

    for key in keys:
        if isinstance(collection, str):
            return default
        try:
            collection = collection[key]
        except (KeyError, IndexError, TypeError):
            return default
    return collection


def locate_key(collection, pattern, path_prefix='/'):

    regex_compatible = (str, bytes)
    dict_or_list = (dict, list)

    def of_types(obj, types):
        return any(isinstance(obj, t) for t in types)

    if isinstance(collection, dict):
        search_key = True
        key_value_generator = collection.items()
    elif isinstance(collection, list):
        search_key = False
        key_value_generator = enumerate(collection)
    else:
        raise ValueError(
            f"{type(collection)} {collection!r} is invalid type for locate "
            f"key.  It should be dict or list",
        )

    for key, value in key_value_generator:
        if search_key and of_types(key, regex_compatible):
            if pattern.search(key):
                yield f"{path_prefix}{key}"
        if not of_types(value, dict_or_list):
            continue
        for json_path in locate_key(value, pattern, f"{path_prefix}{key}/"):
            yield json_path


class JsonDiff:

    class KeySide(Enum):
        LEFT = 1
        RIGHT = 2
        BOTH = 3

    ColumnFormat = namedtuple(
        'ColumnFormat',
        [
            'indent',
            'key_width',
            'value1_width',
            'value2_width',
        ],
    )

    COLUMN_SEPARATOR = '  '

    def __init__(
            self,
            max_width: int = 80,
            diff_only=False,
            indent_size=2,
    ):
        self.max_width = max_width
        """total width of string output, essentially the number of columns 
        in the terminal"""

        self.diff_only = diff_only
        """flag controlling whether the entire JSON structure is shown or 
        just those areas that are different"""

        self.indent_size = indent_size
        """number of spaces to use for indentation"""

    def run(self, json1, json2):
        if isinstance(json1, dict) and isinstance(json2, dict):
            yield from self.compare_dicts(json1, json2)
        else:
            raise ValueError("Only comparison between dicts is supported")

    def compare_dicts(self, json1, json2, depth=0):
        column_format = self.get_column_format(json1, json2, depth)

        keys1 = sorted(json1.keys())
        keys2 = sorted(json2.keys())
        for i in range(len(keys1) + len(keys2)):

            if keys1 and keys2:
                key1 = keys1[0]
                key2 = keys2[0]
                if key1 < key2:
                    yield from self.show_values(
                        key1,
                        json1[key1],
                        None,
                        self.KeySide.LEFT,
                        column_format
                    )
                    keys1.pop(0)
                elif key1 == key2:
                    yield from self.show_values(
                        key1,
                        json1[key1],
                        json2[key2],
                        self.KeySide.BOTH,
                        column_format,
                    )
                    keys1.pop(0)
                    keys2.pop(0)
                else:
                    yield from self.show_values(
                        key2,
                        None,
                        json2[key2],
                        self.KeySide.RIGHT,
                        column_format
                    )
                    keys2.pop(0)
                continue

            for key1 in keys1:
                yield from self.show_values(
                    key1,
                    json1[key1],
                    None,
                    self.KeySide.LEFT,
                    column_format,
                )

            for key2 in keys2:
                yield from self.show_values(
                    key2,
                    None,
                    json2[key2],
                    self.KeySide.RIGHT,
                    column_format,
                )

            break

    @staticmethod
    def is_composite_type(value):
        if isinstance(value, list):
            return True
        if isinstance(value, dict):
            return True
        return False

    def value_width(self, value):
        """
        Determines length of value's repr.  For values which are lists or
        dicts, the behavior of this method hasn't been defined.
        :param value:  Value to check repr length of
        """
        if self.is_composite_type(value):
            return 5
        return len(repr(value))

    @staticmethod
    def adjust_column_widths(
            key_width,
            value1_width,
            value2_width,
            column_separator,
            max_width,
    ):
        total_width = sum([
            key_width,
            value1_width,
            value2_width,
            len(column_separator) * 2,
        ])

        overflow = total_width - max_width
        if overflow <= 0:
            return key_width, value1_width, value2_width

        overflow = int(ceil(overflow / 3))

        key_width -= overflow
        value1_width -= overflow
        value2_width -= overflow
        return key_width, value1_width, value2_width

    def get_column_format(self, json1, json2, depth):
        key_width = max(
            len(repr(k)) for k in chain(
                json1.keys(),
                json2.keys(),
            )
        )

        value1_width = max(
            map(self.value_width, json1.values())
        )
        value2_width = max(
            map(self.value_width, json2.values())
        )

        print(f"before {key_width=}, {value1_width=}, {value2_width=}")
        key_width, value1_width, value2_width = self.adjust_column_widths(
            key_width,
            value1_width,
            value2_width,
            self.COLUMN_SEPARATOR,
            self.max_width,
        )
        print(f"after {key_width=}, {value1_width=}, {value2_width=}")

        return self.ColumnFormat(
            indent=' ' * self.indent_size * depth,
            key_width=key_width,
            value1_width=value1_width,
            value2_width=value2_width,
        )

    @staticmethod
    def fit_value_in_column(value, column_width, use_repr_of_value=True):
        if use_repr_of_value:
            value = repr(value)
        value_length = len(value)
        if value_length < column_width:
            return value.ljust(column_width)
        if value_length == column_width:
            return value
        value = value[:column_width]
        if value_length > 4:
            return value[:-4] + ' ...'
        return value

    @staticmethod
    def get_start_char(value):
        if isinstance(value, dict):
            return '{'
        if isinstance(value, list):
            return '['
        return ''

    def show_values(self, key, value1, value2, key_side, column_format):

        if all([
                self.diff_only,
                key_side == self.KeySide.BOTH,
                value1 == value2,
        ]):
            return

        pieces = [
            column_format.indent,
            self.fit_value_in_column(key, column_format.key_width),
            self.COLUMN_SEPARATOR
        ]

        left_start = self.get_start_char(value1)
        right_start = self.get_start_char(value2)

        value1_width = column_format.value1_width
        if key_side in (self.KeySide.LEFT, self.KeySide.BOTH):
            if left_start:
                piece = self.fit_value_in_column(
                    left_start,
                    value1_width,
                    use_repr_of_value=False
                )
            else:
                piece = self.fit_value_in_column(value1, value1_width)
            pieces.append(piece)
        else:
            pieces.append(' ' * value1_width)

        pieces.append(self.COLUMN_SEPARATOR)

        value2_width = column_format.value2_width
        if key_side in (self.KeySide.RIGHT, self.KeySide.BOTH):
            if right_start:
                piece = self.fit_value_in_column(
                    right_start,
                    value2_width,
                    use_repr_of_value=False,
                )
            else:
                piece = self.fit_value_in_column(value2, value2_width)
            pieces.append(piece)
        else:
            pieces.append(' ' * value2_width)

        yield "".join(pieces)


def json_diff(json1, json2, max_width=80, diff_only=False, indent_size=2, path=''):
    yield from JsonDiff(
        max_width,
        diff_only,
        indent_size,
    ).run(
        json1,
        json2,
    )



