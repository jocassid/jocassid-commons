
from collections import namedtuple
from dataclasses import dataclass
from enum import Enum
from itertools import chain, count, zip_longest
from math import ceil, log10
from uuid import uuid4
from typing import Any, Iterator, List, Optional, Tuple, Union

from jocassid_commons.exceptions import NoSubclassImplementationError
from jocassid_commons.itertools import merge_queue_factory


MISSING_VALUE = uuid4()


MINIMUM_COLUMN_WIDTH = 5


class RowType(Enum):
    START = 1
    ITEM = 2
    END = 3
    PLACEHOLDER = 4


class Side(Enum):
    LEFT = 5
    RIGHT = 6


# PY3.11: Adds StrEnum
class DiffType(Enum):
    MATCH = ' '
    LEFT_ONLY = '<'
    RIGHT_ONLY = '>'
    MISMATCH = 'X'


# type of entire JSON object or list
JsonType = Union[dict, list]

JsonItemType = Union[JsonType, int, float, bool, str]

KeyValueWidths = namedtuple(
    'FormatParams',
    ['key_width', 'value_length']
)


class ColumnWidths:

    def __init__(
            self,
            left_key_width: int = MINIMUM_COLUMN_WIDTH,
            left_value_width: int = MINIMUM_COLUMN_WIDTH,
            right_value_width: int = MINIMUM_COLUMN_WIDTH,
            right_key_width: int = 0,
    ):
        def enforce_min_width(width: int) -> int:
            return max(width, MINIMUM_COLUMN_WIDTH)

        self.left_key_width: int = enforce_min_width(left_value_width)
        self.left_value_width: int = enforce_min_width(left_value_width)
        self.right_value_width: int = enforce_min_width(right_value_width)

        if right_key_width == 0:
            self.right_key_width: int = 0
        else:
            self.right_key_width: int = enforce_min_width(right_key_width)

    @property
    def total_width(self):
        return sum([
            self.left_key_width,
            self.left_value_width,
            self.right_value_width,
            self.right_key_width,
        ])

    def __repr__(self):
        return (
            f"left_key_width={self.left_key_width} "
            f"left_value_width={self.left_value_width} "
            f"right_key_width={self.right_key_width} "
            f"right_value_width={self.right_value_width}"
        )


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

    def __repr__(self):
        return (
            f"{self.has_data=} {self.key=} {self.value=}"
        )


class ItemDiff:

    def __init__(
            self,
            diff_type: DiffType,
            key1=MISSING_VALUE,
            value1=MISSING_VALUE,
            key2=MISSING_VALUE,
            value2=MISSING_VALUE,
    ):
        self.validate_params(key1, value1)
        self.validate_params(key2, value2)

        self.diff_type = diff_type
        self.key1 = key1
        self.value1 = value1
        self.key2 = key2
        self.value2 = value2

    @property
    def has_key1(self):
        return self.key1 is not MISSING_VALUE

    @property
    def has_key2(self):
        return self.key2 is not MISSING_VALUE

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
            self.diff_type,
            self.key1,
            self.value1,
            self.key2,
            self.value2,
        )

    def __repr__(self):
        return self.__str__()


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
    SPACER = ' ' * COLUMN_SPACING

    def run(
            self,
            json1: JsonType,
            json2: JsonType,
            max_width: int = 80,
            keys: Optional[Tuple[Any]] = None,
    ) -> Iterator[str]:
        """
        :param json1:
        :param json2:
        :param max_width:   Total width of string output, essentially the
                            number of columns in the terminal
        :param keys:        A tuple of keys which will be used with json_get
                            to extract values from within the two JSON objects
        """

        if keys:
            json1 = json_get(json1, MISSING_VALUE, *keys)
            json2 = json_get(json2, MISSING_VALUE, *keys)

        yield from self.render_diff(json1, json2, max_width)

    def render_diff(
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

            for item_diff in self.get_item_data(json1, json2):

                # SEND item_diff AND AN OBJECT ENCAPSULATING THE COLUMN WIDTHS
                yield from self.render_item_same_container_type(
                    item_diff,
                    column_widths,
                )

            yield end1

    def render_item_same_container_type(
            self,
            item_diff: ItemDiff,
            column_widths: ColumnWidths
    ) -> Iterator[str]:
        """
        If the two items are same container type then there is 1 column for
        key/index.  If the column types are different, there will be two
        columns for indexes/keys.
        :param: diff_row
        :return: Returns string w/ formatted row
        """
        print(f"diff_row={str(item_diff)}")

        indent = " "

        if item_diff.diff_type == DiffType.LEFT_ONLY:
            key = item_diff.key1
            key_width = column_widths.left_key_width
        else:
            key = item_diff.key2
            key_width = column_widths.right_key_width

        first_time_through_loop = True
        for left_row, right_row in zip_longest(
                self.get_item_rows(item_diff.value1),
                self.get_item_rows(item_diff.value2),
        ):
            if first_time_through_loop:
                yield self.SPACER.join([
                    "{}{}".format(
                        indent,
                        item_diff.diff_type.value,
                    ),
                    self.get_repr(item_diff.key1, key_width),
                    self.get_repr(left_row, column_widths.left_value_width),
                    self.get_repr(right_row, column_widths.right_value_width)
                ])
                first_time_through_loop = False
                continue

        #
        #
        # return "  ".join([
        #     f"{indent}{item_diff.diff_value}",
        #     # self.get_repr(item_diff.key1, column_widths.left_key_width),
        # ])

    def get_item_rows(self, value: JsonItemType):
        if type(value) in (list, dict):
            raise NotImplementedError()
        yield value

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
            length = 0
        elif isinstance(item, list) or isinstance(item, dict):
            # list or dict length is 1 for opening/closing [ or }
            length = 1
        elif isinstance(item, str):
            # add 2 for opening and closing quote
            length = len(item) + 2
        else:
            length = len(repr(item))
        return max(length, MINIMUM_COLUMN_WIDTH)

    def get_item_data(self, json1, json2) -> Iterator[ItemDiff]:
        keys_and_values1 = self.get_keys_and_values_from_container(json1)
        keys_and_values2 = self.get_keys_and_values_from_container(json2)

        next_key_value1 = self.get_next_key_and_value(keys_and_values1)
        next_key_value2 = self.get_next_key_and_value(keys_and_values2)

        while next_key_value1.has_data and next_key_value2.has_data:
            key1, value1, key2, value2 = ItemDiff.unpack(
                next_key_value1,
                next_key_value2,
            )
            if key1 < key2:
                yield ItemDiff(DiffType.LEFT_ONLY, key1, value1)
                next_key_value1 = self.get_next_key_and_value(
                    keys_and_values1,
                )
                continue

            if key1 > key2:
                yield ItemDiff(DiffType.RIGHT_ONLY, key2=key2, value2=value2)
                next_key_value2 = self.get_next_key_and_value(
                    keys_and_values2
                )
                continue

            if value1 == value2:
                yield ItemDiff(DiffType.MATCH, key1, value1, key2, value2)
            else:
                yield ItemDiff(DiffType.MISMATCH, key1, value1, key2, value2)

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

    @staticmethod
    def truncate_repr(repr_str, column_width):
        if len(repr_str) > column_width:
            trim_length = column_width - 4
            if trim_length < 0:
                breakpoint()
            print(f"{trim_length=} for {repr_str}")
            return repr_str[:trim_length] + ' ...'
        return repr_str

    def get_repr(self, value: Any, column_width: int) -> str:
        if value is MISSING_VALUE:
            return ' ' * column_width
        if isinstance(value, int):
            return self.truncate_repr(
                str(value).rjust(column_width),
                column_width,
            )
        if isinstance(value, dict):
            raise NotImplementedError(
                "Caller should sort out whether value is list or dict and "
                "not use this method on it."
            )
        if isinstance(value, str):
            return self.truncate_repr(repr(value), column_width)

        return f'{type(value)} NOT IMPLEMENTED'

    def get_dict_repr(self, value: dict, column_width: int):
        pieces = ['{']
        total_length = 1

        for key in sorted(value.keys()):
            # repr_value = self.get_repr()
            break

        raise NotImplementedError()


def json_diff(json1, json2, max_width=80, diff_only=False, keys=None):
    yield from JsonDiff().run(
        json1,
        json2,
        max_width,
        diff_only,
        keys,
    )


def is_json_type(value: Any) -> Optional[type]:
    if isinstance(value, list):
        return list
    if isinstance(value, dict):
        return dict
    return None


@dataclass
class DataRow:
    row_type: RowType
    key: Union[str, int]  # empty string or -1 indicates no key
    value: Any
    depth: 0

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        key = self.key

        value = self.value
        if value == MISSING_VALUE:
            value = 'MISSING_VALUE'

        return (
            f"DataRow({self.row_type}, {key!r}, {value!r}, {self.depth})"
        )

    def __eq__(self, other):
        if not isinstance(other, DataRow):
            return False
        return (
            self.row_type == other.row_type
            and self.key == other.key
            and self.value == other.value
            and self.depth == other.depth
        )


class JsonIterator:

    NO_KEY_VALUE = None

    def __init__(self, container_value: JsonType, depth: int = 0):
        self.container = container_value
        self._generator: Iterator[DataRow] = self.generator(container_value)
        self.depth = depth

    def __iter__(self):
        return self

    def __next__(self) -> DataRow:
        return next(self._generator)

    def generator(self, container_value: JsonType) -> Iterator[DataRow]:
        raise NotImplementedError("subclass should implement")

    def placeholder(self, next_level_down: bool = False):
        depth = self.depth + 1
        if next_level_down:
            depth += 1
        return DataRow(
            RowType.PLACEHOLDER,
            self.NO_KEY_VALUE,
            MISSING_VALUE,
            depth,
        )


class ListIterator(JsonIterator):

    NO_KEY_VALUE = -1

    def generator(
            self,
            container_value: JsonType,
    ) -> Iterator[DataRow]:
        yield DataRow(RowType.START, self.NO_KEY_VALUE, '[', self.depth)
        for i, item in enumerate(container_value):
            yield DataRow(RowType.ITEM, i, item, self.depth + 1)
        yield DataRow(RowType.END, self.NO_KEY_VALUE, ']', self.depth)


class DictIterator(JsonIterator):
    """We can safely assume that the keys are non-empty strings.  I'm
    going to build a json_check cam identify invalid key types"""

    NO_KEY_VALUE = ''

    def generator(
            self,
            container_value: JsonType,
    ) -> Iterator[DataRow]:
        yield DataRow(RowType.START, self.NO_KEY_VALUE, '{', self.depth)
        for key in sorted(container_value.keys()):
            yield DataRow(RowType.ITEM, key, container_value[key], self.depth + 1)
        yield DataRow(RowType.END, self.NO_KEY_VALUE, '}', self.depth)


def get_iterator(container_value: JsonType, depth: int = 0) -> JsonIterator:
    if isinstance(container_value, list):
        return ListIterator(container_value, depth)
    if isinstance(container_value, dict):
        return DictIterator(container_value, depth)
    raise TypeError(
        f"Received {type(container_value)} {container_value!r} "
        f"instead of list or dict"
    )


class JsonDiff3:

    def run(
            self,
            json1: JsonType,
            json2: JsonType,
            max_width: int = 80,
            keys: Optional[Tuple[Any]] = None,
    ) -> Iterator[str]:

        json1_type = is_json_type(json1)
        json2_type = is_json_type(json2)

        if not json1_type or not json2_type:
            raise NotImplementedError("something isn't a list or dict")

        json1_itr = ListIterator(json1)
        json2_itr = ListIterator(json2)

        for right_side, left_side in self.run_iterators(json1_itr, json2_itr):
            yield f"{right_side}  {left_side}"

    def run_iterators(
            self,
            left_itr: JsonIterator,
            right_itr: JsonIterator,
            depth: int = 0,
    ) -> Iterator[Tuple[DataRow, DataRow]]:

        get_next_left = True
        get_next_right = True

        left_row = None
        right_row = None

        is_outer_left: bool = True
        is_outer_right: bool = True

        c = count(0)  # this is to prevent infinite loop during development
        while get_next_left or get_next_right or next(c) < 20:

            if get_next_left:
                left_row = next(left_itr)

            if get_next_right:
                right_row = next(right_itr)

            print()
            print(f"{left_row=}")
            print(f"{right_row=}")

            if left_row.row_type == RowType.START:
                if right_row.row_type == RowType.START:
                    yield left_row, right_row
                    get_next_left, get_next_right = True, True

                    if is_outer_right:
                        is_outer_right = False
                else:
                    raise NotImplementedError()

                if is_outer_left:
                    is_outer_left = False
                continue

            if left_row.row_type == RowType.ITEM:
                if right_row.row_type == RowType.ITEM:
                    left_key = left_row.key
                    right_key = right_row.key

                    left_json_type = is_json_type(left_row.value)
                    right_json_type = is_json_type(right_row.value)

                    if left_key < right_key:
                        if left_json_type:
                            raise NotImplementedError()
                        else:
                            yield left_row, right_itr.placeholder()
                            get_next_left, get_next_right = True, False
                    elif left_key == right_key:
                        if not left_json_type and not right_json_type:
                            yield left_row, right_row
                            get_next_left, get_next_right = True, True
                        elif not left_json_type and right_json_type:
                            raise NotImplementedError()
                        elif left_json_type and not right_json_type:
                            depth_new = depth + 1
                            yield from self.run_iterator(
                                get_iterator(left_row.value, depth=depth_new),
                                itr_side=Side.LEFT,
                                other_side_row=right_row,
                                placeholder_row=right_itr.placeholder(
                                    next_level_down=True,
                                ),
                                depth=depth_new,
                            )
                        else:
                            raise NotImplementedError()
                    else:
                        if right_json_type:
                            raise NotImplementedError()
                        else:
                            yield left_itr.placeholder(), right_row
                            get_next_left, get_next_right = False, True
                    continue
                if right_row.row_type == RowType.END:
                    yield left_row, right_itr.placeholder()
                    get_next_left, get_next_right = True, False
                    continue
                else:
                    raise NotImplementedError()

            if left_row.row_type == RowType.PLACEHOLDER:
                raise NotImplementedError()

            # left_row.row_type == RowType.END
            if right_row.row_type == RowType.START:
                raise NotImplementedError()
            if right_row.row_type == RowType.ITEM:
                yield left_itr.placeholder(), right_row
                get_next_left, get_next_right = False, True
                continue
            elif right_row.row_type == RowType.PLACEHOLDER:
                raise NotImplementedError()
            else:
                # right_row.row_type == RowType.END
                # no point in setting get_next_left and get_next_right since
                # we're exiting the loop
                yield left_row, right_row
                break

    def run_iterator(
            self,
            itr: JsonIterator,
            itr_side: Side,
            other_side_row: DataRow,
            placeholder_row: DataRow,
            depth: int
    ):
        for i, itr_row in enumerate(itr):
            print()
            print(f"{itr_row=} {itr_side=}")
            if i == 0:
                if itr_side == Side.LEFT:
                    yield itr_row, other_side_row
                else:
                    yield other_side_row, itr_row
                continue

            if itr_side == Side.LEFT:
                yield itr_row, placeholder_row
            else:
                yield placeholder_row, itr_row

    @staticmethod
    def build_placeholder_row(itr):
        return DataRow(
            RowType.PLACEHOLDER,
            itr.NO_KEY_VALUE,
            MISSING_VALUE,
            itr.depth + 1,
        )
