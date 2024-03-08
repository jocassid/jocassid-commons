
from typing import Any, Iterator, Union


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


def json_format(
        json: Union[list, dict],
        indent_spaces: int = 1,
        width: int = 80, depth=None):
    formatter = JsonFormatter(
        indent_spaces,
    )
    for line in formatter.format(json):
        yield line


class JsonFormatter:

    def __init__(self, indent_spaces: int = 1):
        self.indent_spaces = indent_spaces

    def format(self, parent: Any, depth: int = 0) -> Iterator[str]:
        indent = ' ' * (self.indent_spaces * depth)
        if isinstance(parent, dict):
            if not parent:
                yield f'{indent}{{}}'
            else:
                for key, value in parent.item():
                    yield f"{indent}{key!r}: {value!r},"

        elif isinstance(parent, list):
            if not parent:
                yield f'{indent}[]'
            else:
                yield f'{indent}['

                for child in parent:
                    for line in self.format(child, depth+1):
                        yield line

                yield f'{indent}]'

        else:
            yield f"{indent}{parent!r},"


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


