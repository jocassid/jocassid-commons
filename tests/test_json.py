
from itertools import zip_longest
from re import compile as re_compile

from pytest import raises

from jocassid_commons.json import (
    json_diff,
    json_get,
    JsonDiff,
    locate_key,
)


def test_json_get():
    assert json_get(None, 'default', None) == 'default'
    assert json_get({'a': 'alpha'}, 'default', None) == 'default'
    
    # Miss on 1st level of 1 level dictionary
    assert json_get({'a': 'alpha'}, None, 'b') is None
    
    # Hit on 1st level of 1 level dictionary
    assert json_get({'a': 'alpha'}, None, 'a') == 'alpha'
    
    section_i_b = {
        1: 'I-B-1',
        2: 'I-B-2'
    }
    
    section_i = {
        'A': {
            1: 'I-A-1',
            2: 'I-A-2'
        },
        'B': section_i_b
    }
    
    json_data = {
        'I': section_i,
        'II': {
            'A': {
                1: 'II-A-1',
                2: 'II-A-2'
            },
            'B': {
                1: 'II-B-1',
                2: 'II-B-2'
            }            
        }
    }
    
    # Miss on 1st level of multi-level dictionary
    assert json_get(json_data, 42, 'III') == 42
    
    # Hit on 1st level of multi-level dictionary
    assert json_get(json_data, 42, 'I') == section_i
    
    # Miss on 2nd level of multi-level dictionary
    assert json_get(json_data, 42, 'I', 'C') == 42
    
    # Hit on 2nd level of multi-level dictionary
    assert json_get(json_data, 42, 'I', 'B') == section_i_b

    # Miss on 3rd level of multi-level dictionary
    assert json_get(json_data, 42, 'I', 'A', 3) == 42

    # Hit on 3rd level of multi-level dictionary
    assert json_get(json_data, 42, 'I', 'A', 1) == 'I-A-1'
    
    # data is not dictionary
    assert json_get('something', 42, 'I') == 42
    
    # 2nd level is not dictionary
    assert json_get({'I': 'foo'}, 42, 'I', 'A') == 42
    
    # 3rd level is not dictionary
    assert json_get({'I': {'A': 'foo'}}, 42, 'I', 'A', 1) == 42
    

def test_json_get_with_lists():
    
    # Top level is list
    assert json_get([], 42, 0) == 42
    
    # index outside of list bounds
    assert json_get([2, 2], 42, 2) == 42
    
    # 2nd level is list
    assert json_get({'foo': [2, 4, 9]}, 42, 'foo', 1) == 4
    
    # 3 levels of lists
    data = [
        [
            [1, 1, 2, 3, 5],
            [1, 1, 4, 9, 25]
        ],
        [
            [2, 3, 5, 7],
            [4, 6, 10, 14],
            [6, 9, 15, 21]
        ],
    ]
    assert json_get(data, 42, 1, 2, 3) == 21


def test_locate_key():

    sample_list = [
        {
            'type': 'album',
            'title': 'Automatic for the People',
            'tracks': [
                {'title': 'Drive'},
                {'title': 'Everybody Hurts'},
            ]
        }
    ]

    sample_dict = {
        'music': sample_list,
        5: 'non-string key',
        6: {
            'half-dozen': 'quantity',
            'hexagon': 'polygon',
            'type': None,
        },
        'audiobooks': {
            'fiction': None,
        },
        'video': {
            'movies': [
                {'title': 'This Film Is On'},
            ],
            'tv_series': [],
        }
    }

    actual = list(locate_key(sample_dict, re_compile('music')))
    assert ['/music'] == actual

    with raises(ValueError) as exec_info:
        list(locate_key(5, re_compile('foo')))
    expected = "<class 'int'> 5 is invalid type for locate key.  It should be dict or list"
    assert expected == str(exec_info.value)

    actual = list(locate_key(sample_dict, re_compile('movies')))
    assert ['/video/movies'] == actual

    actual = list(locate_key([], re_compile('music')))
    assert [] == actual

    actual = list(locate_key(sample_list, re_compile('type')))
    assert ['/0/type'] == actual

    expected = [
        '/0/title',
        '/0/tracks/0/title',
        '/0/tracks/1/title',
    ]
    actual = list(locate_key(sample_list, re_compile('title')))
    assert expected == actual

    expected = [
        '/music/0/title',
        '/music/0/tracks/0/title',
        '/music/0/tracks/1/title',
        '/video/movies/0/title',
    ]
    actual = list(locate_key(sample_dict, re_compile('title')))
    assert expected == actual


class TestJsonDiff:

    # def test_get_repr_dict(self):
    #     dict_in = {
    #         'a': 'alpha',
    #         'bravo': 5,
    #         'c': '2025-05-10',
    #         'delta': 2.5,
    #     }
    #
    #     max_key_len, max_value_len, dict_out = JsonDiff.get_repr_dict(dict_in)
    #
    #     assert 7 == max_key_len
    #     assert 12 == max_value_len
    #
    #     expected = {
    #         "'a'": "'alpha'",
    #         "'bravo'": '5',
    #         "'c'": "'2025-05-10'",
    #         "'delta'": '2.5',
    #     }
    #     assert expected == dict_out

    def test_diffs_only_false_values_short_strings(self):
        json1 = {'a': 'alpha', 'b': 'bravo', 'd': 'delta'}
        json2 = {'b': 'beta', 'c': 'charlie', 'd': 'delta'}

        expected_lines = [
            "{",
            "<  'a'  'alpha'           ",
            "X  'b'  'bravo'  'beta'   ",
            ">  'c'           'charlie'",
            "   'd'  'delta'  'delta'  ",
            "}",
        ]
        actual_lines = list(
            json_diff(json1, json2, max_width=40)
        )
        for i, actual_and_expected_lines in enumerate(
                zip_longest(expected_lines, actual_lines, fillvalue=''),
                1,
        ):
            expected_line, actual_line = actual_and_expected_lines
            message = f"{i:>3}.\n  {expected_line}\n  {actual_line}"
            try:
                assert expected_line == actual_line
            except AssertionError as error:
                print(message)
                raise error


    def test_diffs_only_true_values_short_strings(self):
        json1 = {'a': 'alpha', 'b': 'bravo', 'd': 'delta'}
        json2 = {'b': 'beta', 'c': 'charlie', 'd': 'delta'}

        expected_lines = [
            "{",
            " <  'a'  'alpha'           ",
            " X  'b'  'bravo'  'beta'   ",
            " >  'c'           'charlie'",
            "}",
        ]
        actual_lines = list(
            json_diff(json1, json2, max_width=40, diff_only=True)
        )
        assert expected_lines == actual_lines

    @staticmethod
    def build_json_with_long_keys_and_values():
        json1 = {
            'a_really_long_key_that_will_not_fit_in_column': 'alpha',
            'b': 'The first value is also quite long in this item',
        }
        json2 = {
            'b': "Just to make things interesting, the second value is lengthy"
        }
        return json1, json2

    def test_value_does_not_fit_column_width(self):

        json1, json2 = self.build_json_with_long_keys_and_values()

        expected_lines = [
            "{",
            " <  'a_rea ...  'alpha'                  ",
            " X  'b'         'The f ...  'Just to  ...",
            "}",
        ]
        actual_lines = list(
            json_diff(json1, json2, max_width=40)
        )
        assert expected_lines == actual_lines

    def test_compare_lists(self):

        list1 = [{'a': 'alpha'}]
        list2 = [{'b': 'bravo'}, {'c': 'charlie'}]

        expected_lines = [
            '[',
            " X  0  {'a': 'alpha'}    {'b': 'bravo'}",
            " >  1  {'c': 'charlie'}"
            ']',
        ]
        actual_lines = list(
            json_diff(list1, list2)
        )
        assert expected_lines == actual_lines










