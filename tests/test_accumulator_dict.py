
from pytest import raises

from jocassid_commons.accumulator_dict import AccumulatorDict


def test_constructor():

    message = "{} is not a valid accumulator type".format(
        type(tuple)
    )
    with raises(ValueError, match=message):
        AccumulatorDict(tuple)

    list_dict = AccumulatorDict(list)
    assert list_dict == {}

    list_dict = AccumulatorDict(
        list,
        [
            ('a', 1),
            ('a', 1),
            ('a', 2),
            ('b', 3),
        ],
        b=4,
        c=5,
    )
    assert list_dict == {
        'a': [1, 1, 2],
        'b': [3, 4],
        'c': [5],
    }

    set_dict = AccumulatorDict(set)
    assert set_dict == {}

    set_dict = AccumulatorDict(
        set,
        [
            ('a', 1),
            ('a', 1),
            ('a', 2),
            ('b', 3),
        ],
        b=4,
        c=5,
    )
    assert set_dict == {
        'a': {1, 2},
        'b': {3, 4},
        'c': {5},
    }


def test_setitem():

    d1 = AccumulatorDict(list)

    d1['a'] = 1
    assert d1 == {'a': [1]}

    d1['a'] = 2
    assert d1 == {'a': [1, 2]}
    assert d1['a'] == [1, 2]

    d1['b'] = 3
    assert d1 == {
        'a': [1, 2],
        'b': [3],
    }

    d1['c'] = [4, 5]
    assert d1 == {
        'a': [1, 2],
        'b': [3],
        'c': [4, 5]
    }

    d2 = AccumulatorDict(set)

    d2['a'] = 1
    assert d2 == {'a': {1}}

    d2['a'] = 1
    assert d2 == {'a': {1}}

    d2['a'] = 2
    assert d2 == {'a': {1, 2}}
    assert d2['a'] == {1, 2}

    d2['b'] = 3
    assert d2 == {
        'a': {1, 2},
        'b': {3},
    }

    d2['b'] = {4, 5}
    assert d2 == {
        'a': {1, 2},
        'b': {4, 5},
    }


def test_update():

    d1 = AccumulatorDict(list)
    d1['a'] = 1
    d1['b'] = 2

    d1.update({
        'b': 4,
        'c': 5,
    })

    assert d1 == {
        'a': [1],
        'b': [2, 4],
        'c': [5]
    }

    d2 = AccumulatorDict(list)
    d2['c'] = 6
    d2['d'] = 7

    d1.update(d2)
    assert d1 == {
        'a': [1],
        'b': [2, 4],
        'c': [5, 6],
        'd': [7],
    }

    d1.update(a=8, e=9)
    assert d1 == {
        'a': [1, 8],
        'b': [2, 4],
        'c': [5, 6],
        'd': [7],
        'e': [9],
    }



