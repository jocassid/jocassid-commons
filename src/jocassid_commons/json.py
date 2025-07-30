
from collections import namedtuple
from dataclasses import dataclass
from enum import Enum
from itertools import chain
from math import ceil, log10
from typing import Any, Iterator, List, Optional, Tuple, Union

from jocassid_commons.itertools import merge_queue_factory


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


JsonType = Union[dict, list]

FormatParams = namedtuple(
    'FormatParams',
    ['key_length', 'value_length']
)

MISSING_VALUE = 'MISSING_VALUE'


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
            max_key_length = max(
                format_params1.key_length,
                format_params2.key_length
            )

            default_column_width = remaining_width // 3

            if max_key_length < default_column_width:
                key_column_width = max_key_length
            else:
                pass


            # total_width = sum()



            for diff_row in self.get_row_data(json1, json2):

                # SEND diff_row AND AN OBJECT ENCAPSULATING THE COLUMN WIDTHS
                yield self.render_same_container_type_item(
                    diff_row,
                    # format_params1,
                    # format_params2,
                    # max_width,
                )

            yield end1

    def render_same_container_type_item(
            self,
            diff_row: DiffRow,
            left_format_params,
            right_format_params,
            max_width,
    ) -> str:
        """
        :param: diff_row
        :return: Returns string w/ formatted row
        """
        print(f"diff_row={str(diff_row)}")

        max_key_length = max(
            left_format_params.key_length, right_format_params.key_length)

        return "{} ".format(
            diff_row.diff_value,
        )

    def get_list_format_params(self, json_list: list) -> FormatParams:
        """
        Computes maximum length of indexes and values
        :param json_list:  List from JSON structure
        """
        key_length = int(
            log10(
                len(json_list)
            )
        ) + 1

        value_length = max(
            self.repr_length(i) for i in json_list
        )

        return FormatParams(key_length, value_length)

    def get_dict_format_params(self, json_dict: JsonType) -> FormatParams:
        key_length = 0
        value_length = 0
        for key, value in json_dict.items():
            key_length = max(key_length, self.repr_length(key))
            value_length = max(value_length, self.repr_length(value))
        return FormatParams(key_length, value_length)

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















        # if index is MISSING_VALUE:
        #     if isinstance(value, list): or isinstance(value, dict):
        #         node = ReprTreeContainerNode(list)
        # pass



    # class ColumnFormat:
    #     def __init__(self):
    #         self.key_width = 10
    #         self.value1_width = 10
    #         self.value2_width = 10
    #
    # COLUMN_SEPARATOR = '  '
    #
    #
    # def __init__(
    #         self,
    #         max_width: int = 80,
    #         diff_only=False,
    #         keys=None,
    # ):
    #     self.max_width = max_width
    #     """"""
    #
    #     self.diff_only = diff_only
    #     """"""
    #
    #     self.keys = keys
    #     """"""
    #
    # def run(self, json1, json2):

    #         terminate = False
    #
    #         if json1 is self.MISSING_VALUE:
    #             terminate = True
    #             yield f"No value found for keys {self.keys} in first JSON object"
    #         if json2 is self.MISSING_VALUE:
    #             terminate = True
    #             yield f"No value found for keys {self.keys} in second JSON object"
    #
    #         if terminate:
    #             return
    #
    #     if isinstance(json1, dict) and isinstance(json2, dict):
    #         yield from self.compare_dicts(json1, json2)
    #         return
    #
    #     if isinstance(json1, list) and isinstance(json2, list):
    #         yield from self.compare_lists(json1, json2)
    #         return
    #
    #     yield f"Diff between {type(json1)} and {type(json2)} not supported"
    #
    # def compare_dicts(self, json_dict1, json_dict2):
    #
    #     max_key_len1, max_value_len1, repr_json1 = self.get_repr_dict(json_dict1)
    #     max_key_len2, max_value_len2, repr_json2 = self.get_repr_dict(json_dict2)
    #
    #     max_key_len = max(max_key_len1, max_key_len2)
    #
    #     line_width = sum([
    #         2,
    #         max_key_len,
    #         2 * len(self.COLUMN_SEPARATOR),
    #         max_value_len1,
    #         max_value_len2,
    #     ])
    #
    #     if line_width > self.max_width:
    #         overflow = line_width - self.max_width
    #         column_widths = [max_key_len, max_value_len1, max_value_len2]
    #         total_column_width = sum(column_widths)
    #         percentages = [width / total_column_width for width in column_widths]
    #         trim_amounts = [int(ceil(overflow * percent)) for percent in percentages]
    #         max_key_len = max(max_key_len - trim_amounts[0], 5)
    #         max_value_len1 = max(max_value_len1 - trim_amounts[1], 5)
    #         max_value_len2 = max(max_value_len2 - trim_amounts[2], 5)
    #
    #     yield '{'
    #
    #     for key, side, value1, value2 in self.get_key_side_and_values(
    #             repr_json1,
    #             repr_json2
    #     ):
    #         if self.diff_only and side == ' ':
    #             continue
    #
    #         line = self.COLUMN_SEPARATOR.join([
    #             f" {side}",
    #             self.adjust_width(key, max_key_len),
    #             self.adjust_width(value1, max_value_len1),
    #             self.adjust_width(value2, max_value_len2),
    #         ])
    #         yield line
    #
    #     yield '}'
    #
    # def compare_lists(self, json_list1, json_list2):
    #     list1_len = len(json_list1)
    #     list2_len = len(json_list2)
    #     max_len = max(list1_len, list2_len)
    #     max_index_digits = ceil(log10(max_len))
    #
    #     overhead_width = sum([
    #         2,
    #         max_index_digits,
    #         2 * len(self.COLUMN_SEPARATOR)
    #     ])
    #     estimated_value_width = int((self.max_width - overhead_width) / 2)
    #
    #     max_value_length, repr_json1 = self.get_repr_list(
    #         json_list1,
    #         estimated_value_width,
    #     )
    #
    #
    #     yield '['
    #
    #     for index, side, value1, value2 in self.get_index_side_and_values(
    #         json_list1,
    #         json_list2,
    #         list1_len,
    #         list2_len,
    #         max_len,
    #     ):
    #         if self.diff_only and side == ' ':
    #             continue
    #
    #         line = self.COLUMN_SEPARATOR.join([
    #             f" {side}",
    #             str(index).rjust(max_index_digits),
    #             value1,
    #             value2,
    #         ])
    #         yield line
    #
    #
    #     yield ']'
    #
    # @staticmethod
    # def get_repr_list(json_list, estimated_width):
    #     max_value_len = 0
    #     list_out = []
    #
    #     for value in json_list:
    #         if isinstance(value, dict):
    #             if len(value) <=5:
    #                 value_repr = repr(value)
    #                 value_len = len(value_repr)
    #                 if value_len <= estimated_width:
    #                     max_value_len = max(max_value_len, value_len)
    #
    #     return max_value_len, list_out

    # def get_index_side_and_values(
    #         self,
    #         json_list1,
    #         json_list2,
    #         list1_len,
    #         list2_len,
    #         max_len,
    # ):
    #     for i in range(max_len):
    #         in_list1 = i < list1_len
    #         in_list2 = i < list2_len
    #
    #         if in_list1 and in_list2:
    #             value1 = json_list1[i]
    #             value2 = json_list2[i]
    #             side = ' ' if value1 == value2 else 'X'
    #             yield i, side, repr(value1), repr(value2)
    #             continue
    #
    #         if in_list1 and not in_list2:
    #             yield i, '<', repr(json_list1[i]), ''
    #             continue
    #
    #         if not in_list1 and in_list2:
    #             yield i, '>', '', repr(json_list2[i])
    #             continue
    #
    #         raise RuntimeError("This line should be un-reachable")
    #
    # @staticmethod
    # def adjust_width(text: str, width):
    #     text_len = len(text)
    #     if text_len < width:
    #         return text.ljust(width)
    #     if text_len > width:
    #         return f"{text[:width - 4]} ..."
    #     return text
    #
    # def get_key_side_and_values(self, repr_dict1, repr_dict2) -> Tuple[str, str, str, str]:
    #     """
    #     :param repr_dict1:
    #     :param repr_dict2
    #     """
    #     items1 = self.items_by_key(repr_dict1)
    #     items2 = self.items_by_key(repr_dict2)
    #
    #     more_items1 = True
    #     more_items2 = True
    #
    #     key1, key2, value1, value2 = '', '', '', ''
    #
    #     try:
    #         key1, value1 = next(items1)
    #     except StopIteration:
    #         more_items1 = False
    #
    #     try:
    #         key2, value2 = next(items2)
    #     except StopIteration:
    #         more_items2 = False
    #
    #     while more_items1 and more_items2:
    #
    #         if key1 < key2:
    #             yield key1, '<', value1, ''
    #             try:
    #                 key1, value1 = next(items1)
    #             except StopIteration:
    #                 more_items1 = False
    #             continue
    #
    #         if key1 > key2:
    #             yield key2, '>', '', value2
    #             try:
    #                 key2, value2 = next(items2)
    #             except StopIteration:
    #                 more_items2 = False
    #             continue
    #
    #         side = ' ' if value1 == value2 else 'X'
    #         yield key1, side, value1, value2
    #
    #         try:
    #             key1, value1 = next(items1)
    #         except StopIteration:
    #             more_items1 = False
    #
    #         try:
    #             key2, value2 = next(items2)
    #         except StopIteration:
    #             more_items2 = False

    # @staticmethod
    # def items_by_key(a_dict):
    #     for key in sorted(a_dict.keys()):
    #         yield key, a_dict[key]
    #
    # @staticmethod
    # def get_repr_dict(json_dict):
    #     max_key_len = 0
    #     max_value_len = 0
    #     dict_out = {}
    #
    #     for key, value in json_dict.items():
    #         key_repr = repr(key)
    #         value_repr = repr(value)
    #         max_key_len = max(max_key_len, len(key_repr))
    #         max_value_len = max(max_value_len, len(value_repr))
    #         dict_out[key_repr] = value_repr
    #
    #     return max_key_len, max_value_len, dict_out


def json_diff(json1, json2, max_width=80, diff_only=False, keys=None):
    yield from JsonDiff().run(
        json1,
        json2,
        max_width,
        diff_only,
        keys,
    )



