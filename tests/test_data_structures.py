
from pytest import raises

from jocassid_commons.data_structures import MergeQueue, min_value_and_index


def test_min_value_and_index():
    assert min_value_and_index([1, 2, 3]) == (1, 0)
    assert min_value_and_index([3, 2, 1]) == (1, 2)
    assert min_value_and_index([4, 3, 5]) == (3, 1)


class TestMergeQueue:

    def test_init__arg_not_iterable_or_iterator(self):
        with raises(TypeError):
            # noinspection PyTypeChecker
            MergeQueue([5])

    def test_init__not_sorted_but_key_funcs_provided(self):
        a = [3, 5]
        b = [2]
        key_functions = [lambda x: x(str), lambda y: f'{y}-foo']
        with raises(ValueError):
            MergeQueue([a, b], is_sorted=False, key_functions=key_functions)

    def test_init__wrong_number_of_key_functions_supplied(self):
        a = [3, 5]
        b = [2]
        key_functions = [
            lambda s: str(s),
            lambda f: float(f),
            lambda i: int(i),
        ]
        with raises(ValueError):
            MergeQueue([a, b], key_functions=key_functions)

    def test__no_iterables_supplied(self):
        assert list(MergeQueue([])) == []

    def test_not_sorted(self):
        a = [3, 5]
        b = [2]
        expected = [3, 2, 5]
        assert list(MergeQueue([a, b], is_sorted=False)) == expected

    def test_not_sorted__second_list_longer(self):
        a = [3]
        b = [1, 5]
        expected = [3, 1, 5]
        assert list(MergeQueue([a, b], is_sorted=False)) == expected

    def test_init_next_values__1_iterable_is_empty(self):
        a = [7, 11]
        b = []
        merge = MergeQueue([a, b])
        assert merge.next_values == [7]

    def test_sorted(self):
        a = [2, 3, 5]
        b = [1, 1, 2]
        expected = [1, 1, 2, 2, 3, 5]
        assert list(MergeQueue([a, b])) == expected

    def test_sorted__different_length_iterables(self):
        a = [2, 3, 5]
        b = [1, 1, 2, 3]
        expected = [1, 1, 2, 2, 3, 3, 5]
        assert list(MergeQueue([a, b])) == expected

    def test_sort__empty_iterable(self):
        a = [7, 11]
        b = []
        assert list(MergeQueue([a, b])) == a

    def test_sort__with_key_functions(self):
        a = [
            {'firstName': 'Bob'},
            {'firstName': 'Doug'},
            {'firstName': 'Edward'},
        ]
        b = [
            {'first_name': 'Alice'},
            {'first_name': 'Carol'},
        ]
        key_functions = [
            lambda d1: d1.get('firstName'),
            lambda d2: d2.get('first_name')
        ]
        expected = [
            {'first_name': 'Alice'},
            {'firstName': 'Bob'},
            {'first_name': 'Carol'},
            {'firstName': 'Doug'},
            {'firstName': 'Edward'}
        ]
        assert list(MergeQueue([a, b], key_functions=key_functions)) == expected

    def test_sort__one_key_function_for_both_iterables(self):
        a = [
            {'first_name': 'Bob'},
            {'first_name': 'Doug'},
            {'first_name': 'Edward'},
        ]
        b = [
            {'first_name': 'Alice'},
            {'first_name': 'Carol'},
        ]
        key_functions = [
            lambda d: d.get('first_name')
        ]
        expected = [
            {'first_name': 'Alice'},
            {'first_name': 'Bob'},
            {'first_name': 'Carol'},
            {'first_name': 'Doug'},
            {'first_name': 'Edward'}
        ]
        assert list(MergeQueue([a, b], key_functions=key_functions)) == expected
