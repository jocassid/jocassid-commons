
from collections import namedtuple
from typing import List

from pytest import raises

from jocassid_commons.data_structures import (
    merge_queue_factory,
    MergeSourceContainer,
    min_value_and_index,
)


def test_min_value_and_index():
    assert min_value_and_index([1, 2, 3]) == (1, 0)
    assert min_value_and_index([3, 2, 1]) == (1, 2)
    assert min_value_and_index([4, 3, 5]) == (3, 1)


class TestMergeSourceContainer:

    def test_init(self):
        merge_source = MergeSourceContainer(range(3))
        assert list(merge_source.source) == [1, 2]
        assert merge_source.next_value == 0

    def test_init__1_element_in_source(self):
        merge_source = MergeSourceContainer(range(0, 1))
        assert list(merge_source.source) == []
        assert merge_source.next_value == 0

    def test_init__empty_source(self):
        with raises(StopIteration):
            MergeSourceContainer([])

    def test_next(self):
        merge_source = MergeSourceContainer(range(0, 2))
        assert next(merge_source) == 0
        assert next(merge_source) == 1
        with raises(StopIteration):
            next(merge_source)

    def test_lt(self):
        three_source = MergeSourceContainer([3, 4])
        four_source = MergeSourceContainer([4, 5])
        assert three_source < four_source
        assert not (four_source < three_source)
        assert not (four_source < four_source)

    def test_lt__with_key(self):
        Person = namedtuple(
            'Person',
            ['first_name', 'last_name'],
        )
        person_a = Person('Alice', 'Zebra')
        person_b = Person('Bob', 'Young')

        def first_name_key(person: Person):
            return person.first_name

        source_a = MergeSourceContainer([person_a, person_b], key=first_name_key)
        source_b = MergeSourceContainer([person_b, person_a], key=first_name_key)

        assert source_a < source_b
        assert not (source_b < source_a)
        assert not (source_a < source_a)

        def last_name_key(person: Person):
            return person.last_name

        source_c = MergeSourceContainer([person_a, person_b], key=last_name_key)
        source_d = MergeSourceContainer([person_b, person_a], key=last_name_key)

        assert not (source_c < source_d)
        assert not (source_c < source_c)
        assert source_d < source_c


class TestMergeQueue:

    def test_init__arg_not_iterable_or_iterator(self):
        with raises(TypeError):
            # noinspection PyTypeChecker
            merge_queue_factory([5])

    def test_init__not_sorted_but_key_funcs_provided(self):
        a = [3, 5]
        b = [2]

        def key_func(x):
            return str(x)

        with raises(ValueError):
            merge_queue_factory([a, b], is_sorted=False, key=key_func)

    def test__no_iterables_supplied(self):
        actual = merge_queue_factory([])
        assert list(actual) == []

    def test_not_sorted(self):
        a = [3, 5]
        b = [2]
        expected = [3, 2, 5]
        assert list(merge_queue_factory([a, b], is_sorted=False)) == expected

    def test_not_sorted__second_list_longer(self):
        a = [3]
        b = [1, 5]
        expected = [3, 1, 5]
        assert list(merge_queue_factory([a, b], is_sorted=False)) == expected

    def test_next__1_iterable_is_empty(self):
        a = [7, 11]
        b = []
        assert list(merge_queue_factory([a, b])) == [7, 11]

    def test_sorted(self):
        a = [2, 3, 5]
        b = [1, 1, 2]
        expected = [1, 1, 2, 2, 3, 5]

        assert list(merge_queue_factory([a, b])) == expected

    def test_sorted__different_length_iterables(self):
        a = [2, 3, 5]
        b = [1, 1, 2, 3]
        expected = [1, 1, 2, 2, 3, 3, 5]
        assert list(merge_queue_factory([a, b])) == expected

    def test_sort__empty_iterable(self):
        a = [7, 11]
        b = []
        assert list(merge_queue_factory([a, b])) == a

    def test_sort__with_key_function(self):
        a = [
            {'first_name': 'Bob'},
            {'first_name': 'Doug'},
            {'first_name': 'Edward'},
        ]
        b = [
            {'first_name': 'Alice'},
            {'first_name': 'Carol'},
        ]

        def key_func(d):
            return d.get('first_name') or ''

        expected = [
            {'first_name': 'Alice'},
            {'first_name': 'Bob'},
            {'first_name': 'Carol'},
            {'first_name': 'Doug'},
            {'first_name': 'Edward'}
        ]
        assert list(merge_queue_factory([a, b], key=key_func)) == expected

    def test_sort__with_key_function_handling_dissimilar_objects(self):
        a: List[dict] = [
            {'firstName': 'Bob'},
            {'firstName': 'Doug'},
            {'firstName': 'Edward'},
        ]
        b: List[dict] = [
            {'first_name': 'Alice'},
            {'first_name': 'Carol'},
        ]

        def key_func(t):
            key, value = t
            return key

        expected = [
            {'first_name': 'Alice'},
            {'firstName': 'Bob'},
            {'first_name': 'Carol'},
            {'firstName': 'Doug'},
            {'firstName': 'Edward'}
        ]
        merge_queue = merge_queue_factory(
            [
                map(lambda v: (v.get('firstName'), v), a),
                map(lambda v: (v.get('first_name'), v), b),
            ],
            key=key_func,
        )
        assert [t[1] for t in merge_queue] == expected
