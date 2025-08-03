
from collections import namedtuple
from dataclasses import dataclass
from enum import Enum
from itertools import chain
from math import ceil, log10
from typing import Any, Iterator, List, Optional, Tuple, Union

from jocassid_commons.itertools import merge_queue_factory


MISSING_VALUE = 'MISSING_VALUE'


JsonType = Union[dict, list]

KeyValueWidths = namedtuple(
    'FormatParams',
    ['key_width', 'value_length']
)


@dataclass
class ColumnWidths:
    left_key_width: int = 0
    left_value_width: int = 0
    right_value_width: int = 0
    right_key_width: int = 0

    @property
    def total_width(self):
        return sum([
            self.left_key_width,
            self.left_value_width,
            self.right_value_width,
            self.right_key_width,
        ])


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





class DiffKeyValue:

    def __init__(self, key=MISSING_VALUE, value=MISSING_VALUE):
        self.has_data = any(t is not MISSING_VALUE for t in (key, value))
        self.key = key
        self.value = value


class DiffRow:

    def __init__(
            self,
            diff_value: str,
            key1=MISSING_VALUE,
            value1=MISSING_VALUE,
            key2=MISSING_VALUE,
            value2=MISSING_VALUE,
    ):
        self.validate_params(key1, value1)
        self.validate_params(key2, value2)

        self.diff_value = diff_value
        self.key1 = key1
        self.value1 = value1
        self.key2 = key2
        self.value2 = value2

    @staticmethod
    def validate_params(key, value):
        total = sum([
            1 if key is MISSING_VALUE else 0,
            1 if value is MISSING_VALUE else 0,
        ])
        if total != 1:
            return
        raise ValueError(
            "key and value must be both missing value or "
            "neither missing value"
        )

    @staticmethod
    def unpack(left_key_value: DiffKeyValue, right_key_value: DiffKeyValue):
        return (
            left_key_value.key,
            left_key_value.value,
            right_key_value.key,
            right_key_value.value
        )

    def __str__(self):
        return "diff_value={} key1={} value1={} key2={} value2={}".format(
            self.diff_value,
            self.key1,
            self.value1,
            self.key2,
            self.value2,
        )


class JsonDiff:
    """
    Columns outermost level and keys (type same)
    --------------------------------------------
    A       Indent
    B       Diff value or container1/container2 start/end
                ' ' same
                '<' only in left
                '>' only in right
                'X' values don't match
    C       COLUMN_SPACING
    D       key/index
    E       COLUMN_SPACING
    F       left value
    G       COLUMN_SPACING
    H       right value

    Columns outermost level and keys (type different)
    -------------------------------------------------
    A       Indent
    B       Diff value or container1/container2 start/end
            ' ' same
            '<' only in left (it's possible for dicts to have int keys)
            '>' only in right
            'X' values don't match
    C       COLUMN_SPACING
    D       left key/index
    E       COLUMN_SPACING
    F       left value
    G       COLUMN_SPACING
    H       right key/index
    I       COLUMN_SPACING
    J       right value


    """

    INDENT_WIDTH = 2
    COLUMN_SPACING = 2

    def run(
            self,
            json1: JsonType,
            json2: JsonType,
            max_width: int = 80,
            diff_only: bool = False,
            keys: Optional[Tuple[Any]] = None,
    ) -> Iterator[str]:
        """
        :param json1:
        :param json2:
        :param max_width:   Total width of string output, essentially the
                            number of columns in the terminal
        :param diff_only:   Flag controlling whether the entire JSON structure
                            is shown or just those areas that are different
        :param keys:        A tuple of keys which will be used with json_get
                            to extract values from within the two JSON objects
        """

        if keys:
            json1 = json_get(json1, MISSING_VALUE, *keys)
            json2 = json_get(json2, MISSING_VALUE, *keys)

        yield from self.render_container_diff(json1, json2, max_width)

    def render_container_diff(
            self,
            json1: JsonType,
            json2: JsonType,
            max_width: int,
            indent_level: int = 0,
    ):
        type1 = self.get_container_type(json1)
        type2 = self.get_container_type(json2)

        if not all([type1, type2]):
            raise ValueError()

        if type1 == type2:
            same_type = True
            start1, end1 = '[]' if type1 == list else '{}'
            start2, end2 = start1, end1
        else:
            same_type = False
            start1, end1 = '[]' if type1 == list else '{}'
            start2, end2 = '[]' if type2 == list else '{}'

        if same_type:
            yield start1

            if type1 == list:
                format_params1 = self.get_list_format_params(json1)
                format_params2 = self.get_list_format_params(json2)
            else:
                format_params1 = self.get_dict_format_params(json1)
                format_params2 = self.get_dict_format_params(json2)

            # COMPUTE COLUMN WIDTHS HERE
            remaining_width = max_width \
                - indent_level * self.INDENT_WIDTH \
                - 3 * self.COLUMN_SPACING

            column_widths = ColumnWidths(
                left_key_width=max(
                    format_params1.key_width,
                    format_params2.key_width
                ),
                left_value_width=format_params1.value_length,
                right_value_width=format_params2.value_length,
            )

            if column_widths.total_width > remaining_width:
                raise NotImplementedError(
                    "width of keys & values exceeds remaining width after indents and column spacing")

            for diff_row in self.get_row_data(json1, json2):

                # SEND diff_row AND AN OBJECT ENCAPSULATING THE COLUMN WIDTHS
                yield self.render_same_container_type_item(
                    diff_row,
                    column_widths,
                )

            yield end1

    def render_same_container_type_item(
            self,
            diff_row: DiffRow,
            column_widths: ColumnWidths
    ) -> str:
        """
        :param: diff_row
        :return: Returns string w/ formatted row
        """
        print(f"diff_row={str(diff_row)}")

        indent = " "

        return "  ".join([
            f"{indent}{diff_row.diff_value}",
            self.get_repr(diff_row.key1, column_widths.left_key_width),
        ])

    def get_list_format_params(self, json_list: list) -> KeyValueWidths:
        """
        Computes maximum length of indexes and values
        :param json_list:  List from JSON structure
        """
        key_width = int(
            log10(
                len(json_list)
            )
        ) + 1

        value_length = max(
            self.repr_length(i) for i in json_list
        )

        return KeyValueWidths(key_width, value_length)

    def get_dict_format_params(self, json_dict: JsonType) -> KeyValueWidths:
        key_width = 0
        value_length = 0
        for key, value in json_dict.items():
            key_width = max(key_width, self.repr_length(key))
            value_length = max(value_length, self.repr_length(value))
        return KeyValueWidths(key_width, value_length)

    @staticmethod
    def repr_length(item) -> int:
        if item is MISSING_VALUE:
            return 0
        # list or dict length is 1 for opening/closing [ or }
        if isinstance(item, list) or isinstance(item, dict):
            return 1
        return len(repr(item))

    def get_row_data(self, json1, json2) -> Iterator[DiffRow]:
        keys_and_values1 = self.get_keys_and_values_from_container(json1)
        keys_and_values2 = self.get_keys_and_values_from_container(json2)

        next_key_value1 = self.get_next_key_and_value(keys_and_values1)
        next_key_value2 = self.get_next_key_and_value(keys_and_values2)

        while next_key_value1.has_data and next_key_value2.has_data:
            key1, value1, key2, value2 = DiffRow.unpack(
                next_key_value1,
                next_key_value2,
            )
            if key1 < key2:
                yield DiffRow('<', key1, value1)
                next_key_value1 = self.get_next_key_and_value(
                    keys_and_values1,
                )
                continue

            if key1 > key2:
                yield DiffRow('>', key2=key2, value2=value2)
                next_key_value2 = self.get_next_key_and_value(
                    keys_and_values2
                )
                continue

            if value1 == value2:
                yield DiffRow(' ', key1, value1, key2, value2)
            else:
                yield DiffRow('X', key1, value1, key2, value2)

            next_key_value1 = self.get_next_key_and_value(
                keys_and_values1,
            )
            next_key_value2 = self.get_next_key_and_value(
                keys_and_values2
            )

    @staticmethod
    def get_next_key_and_value(key_value_generator):
        try:
            key, value = next(key_value_generator)
        except StopIteration:
            return DiffKeyValue()
        else:
            return DiffKeyValue(key, value)

    @staticmethod
    def get_keys_and_values_from_container(
            container: Union[list, dict],
    ) -> Iterator[Tuple[Any, Any]]:
        """
        Generator that returns index-value (for lists) or key-value (for dicts)
        pairs.  Pairs are sorted by index/key.
        :param container: list or dict to process
        :yields:  index/key - value pairs
        """
        if isinstance(container, list):
            for i, value in enumerate(container):
                yield i, value
            return
        for key in sorted(container.keys()):
            value = container[key]
            yield key, value

    @staticmethod
    def get_container_type(json_obj):
        if isinstance(json_obj, list):
            return list
        if isinstance(json_obj, dict):
            return dict
        return None

    def get_repr(self, value: Any, column_width: int) -> str:
        if isinstance(value, int):
            return str(value).rjust(column_width)
        if isinstance(value, dict):
            return self.get_dict_repr(value, column_width)

        return f'{type(value)} NOT IMPLEMENTED'

    def get_dict_repr(self, value: dict, column_width: int):
        pieces = ['{']
        total_length = 1

        for key in sorted(value.keys()):
            repr_value = self.get_repr()



        raise NotImplementedError()


def json_diff(json1, json2, max_width=80, diff_only=False, keys=None):
    yield from JsonDiff().run(
        json1,
        json2,
        max_width,
        diff_only,
        keys,
    )



