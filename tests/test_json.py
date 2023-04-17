

from jocassid_commons.json import json_get


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

