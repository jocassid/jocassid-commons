

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
