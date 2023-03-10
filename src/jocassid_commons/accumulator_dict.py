# This file is part of https://github.com/jocassid/JohnsUsefulPythonCode
# This file is in the public domain, be excellent to one another,
# party on dudes.


from itertools import chain


class AccumulatorDict(dict):

    ALLOWED_ACCUMULATOR_TYPES = (set, list)

    def __init__(self, accumulator_type, mapping_or_iterable=None, **kwargs):

        def type_matches(ref_type):
            if accumulator_type == ref_type:
                return True
            if issubclass(accumulator_type, ref_type):
                return True
            return False

        if not any(map(type_matches, self.ALLOWED_ACCUMULATOR_TYPES)):
            raise ValueError(
                "{} is not a valid accumulator type".format(
                    type(accumulator_type)
                )
            )

        self.accumulator_type = accumulator_type

        if hasattr(accumulator_type, 'add'):
            self.append_method = getattr(accumulator_type, 'add')
        else:
            self.append_method = getattr(accumulator_type, 'append')

        mapping_or_iterable = mapping_or_iterable or []
        super().__init__()

        for key, value in chain(mapping_or_iterable, kwargs.items()):
            self[key] = value

    def __setitem__(self, key, value):
        if isinstance(value, self.accumulator_type):
            super().__setitem__(key, value)
            return
        if key not in self:
            super().__setitem__(key, self.accumulator_type())
        self.append_method(self[key], value)

    def update(self, other_dict=None, **kwargs):
        if other_dict:
            if isinstance(other_dict, AccumulatorDict):
                if self.accumulator_type != other_dict.accumulator_type:
                    raise ValueError(
                        "Cannot update an AccumulatorDict of {} values with "
                        "one of {} values".format(
                            self.accumulator_type,
                            other_dict.accumulator_type
                        )
                    )

                for key, values in other_dict.items():
                    for value in values:
                        self[key] = value
            else:
                if hasattr(other_dict, 'keys'):
                    for key in other_dict.keys():
                        value = other_dict[key]
                        self[key] = value
                else:
                    for key, value in other_dict:
                        self[key] = value

        for key, value in kwargs.items():
            self[key] = value



