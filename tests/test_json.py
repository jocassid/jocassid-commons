
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

    def test_diffs_only_false_values_short_strings(self):
        json1 = {'a': 'alpha', 'b': 'bravo', 'd': 'delta'}
        json2 = {'b': 'beta', 'c': 'charlie', 'd': 'delta'}

        expected_lines = [
            "'a'  'alpha'           ",
            "'b'  'bravo'  'beta'   ",
            "'c'           'charlie'",
            "'d'  'delta'  'delta'  ",
        ]
        actual_lines = list(
            json_diff(json1, json2, max_width=40)
        )
        assert expected_lines == actual_lines

    def test_diffs_only_true_values_short_strings(self):
        json1 = {'a': 'alpha', 'b': 'bravo', 'd': 'delta'}
        json2 = {'b': 'beta', 'c': 'charlie', 'd': 'delta'}

        expected_lines = [
            "'a'  'alpha'           ",
            "'b'  'bravo'  'beta'   ",
            "'c'           'charlie'",
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
            "'a ...  'alpha'                        ",
            "'b'     'The ...  'Just to make thi ...",
        ]
        actual_lines = list(
            json_diff(json1, json2, max_width=40)
        )
        assert expected_lines == actual_lines

    def test_value_width(self):
        diff = JsonDiff()
        assert 5 == diff.value_width('foo')
        assert 4 == diff.value_width(1234)
        assert 5 == diff.value_width([1, 2])
        assert 5 == diff.value_width({'foo': 'bar'})

    def test_adjust_column_widths(self):

        key_width_out, value1_width_out, value2_width_out = \
            JsonDiff.adjust_column_widths(
                key_width=20,
                value1_width=20,
                value2_width=20,
                column_separator='  ',
                max_width=80
            )

        assert 20 == key_width_out
        assert 20 == value1_width_out
        assert 20 == value2_width_out

        key_width_out, value1_width_out, value2_width_out = \
            JsonDiff.adjust_column_widths(
                key_width=30,
                value1_width=30,
                value2_width=30,
                column_separator='  ',
                max_width=80,
            )

        assert 25 == key_width_out
        assert 25 == value1_width_out
        assert 25 == value2_width_out

    def test_fit_value_in_column(self):
        value_out = JsonDiff.fit_value_in_column(
            'a_really_long_key_that_will_not_fit_in_column',
            6
        )
        assert value_out == "'a ..."

    def test_show_values__diffs_only_keys_on_both_sides_values_match(self):
        diff = JsonDiff(diff_only=True)
        actual = list(
            diff.show_values(
                'key1',
                'value1',
                'value1',
                JsonDiff.KeySide.BOTH,
                JsonDiff.ColumnFormat(
                    indent=2,
                    key_width=10,
                    value1_width=20,
                    value2_width=20,
                ),
            )
        )
        assert actual == []

    def test_json_diff__dict_within_dict(self):
        json1 = {
            'a': 'alpha',
            'c': {
                'a2': 'apple',
                'c2': 'carrot',
            }
        }
        json2 = {
            'b': 'bravo',
            'c': {
                'b2': 'bananas',
                'c2': 'celery',
            }
        }

        actual = list(json_diff(json1, json2, max_width=40))
        assert actual[0] == "'a'  'alpha'         "
        assert actual[1] == "'b'           'bravo'"
        assert actual[2] == "'c'  {        {      "
        assert actual[3] == "  'a2'  'apple'      "
        assert actual[4] == "  'b2'  'bananas'   "
