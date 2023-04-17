
from typing import \
    Any, Callable, Iterable, \
    Iterator, List, Sequence, Tuple, \
    TypeVar, Union


T = TypeVar('T')


def min_value_and_index(
        sequence: Sequence[T],
        key_functions: Sequence[Callable[[Any], Any]] = None
) -> Tuple[T, int]:
    min_value = None  # holds min value before applying key function
    min_index = None

    key_min_value = None
    for i, value in enumerate(sequence):
        if not key_functions:
            key_value = value
        elif len(key_functions) == 1:
            key_value = key_functions[0](value)
        else:
            key_value = key_functions[i](value)

        if i == 0:
            min_value = value
            key_min_value = key_value
            min_index = 0
            continue

        if key_value >= key_min_value:
            continue

        min_value = value
        key_min_value = key_value
        min_index = i

    return min_value, min_index


class MergeQueue:

    def __init__(
            self,
            iterables_or_iterators: Sequence[Union[Iterable, Iterator]],
            is_sorted: bool = True,
            key_functions: List[Callable[[Any], Any]] = None,
    ):
        self.iterators: List[Iterator] = []
        for item in iterables_or_iterators:
            if hasattr(item, '__next__'):
                self.iterators.append(item)
            else:
                # This will raise a TypeError if item isn't Iterable
                self.iterators.append(iter(item))

        self.iterator_index = 0
        self.sorted = is_sorted
        self.next_values = None

        if not is_sorted:
            if key_functions:
                raise ValueError(
                    f'Key functions may only be used when the '
                    f'{self.__class__.__name__} is sorted'
                )
            self.key_functions = None
            return

        self.next_values = self.init_next_values(self.iterators)

        if not key_functions:
            self.key_functions = None
            return

        if len(key_functions) not in (1, len(iterables_or_iterators)):
            raise ValueError(
                f"Invalid number of key functions.  There should be 1 or "
                f"{len(iterables_or_iterators)} key functions",
            )
        self.key_functions = key_functions

    @staticmethod
    def init_next_values(iterators: List[Iterator]) -> List[Any]:
        next_values = []
        i = 0
        while i < len(iterators):
            iterator = iterators[i]
            try:
                value = next(iterator)
            except StopIteration:
                iterators.pop(i)
            else:
                i += 1
                next_values.append(value)
        return next_values

    def __iter__(self):
        return self

    def __next__(self):
        if not self.iterators:
            raise StopIteration
        if self.sorted:
            return self.sorted_next()
        return self.unsorted_next()

    def sorted_next(self):
        if not self.iterators:
            raise StopIteration

        min_value, min_index = min_value_and_index(
            self.next_values,
            self.key_functions,
        )
        iterator = self.iterators[min_index]
        try:
            self.next_values[min_index] = next(iterator)
        except StopIteration:
            self.next_values.pop(min_index)
            self.iterators.pop(min_index)
            if len(self.key_functions) > 1:
                self.key_functions.pop(min_index)
        finally:
            return min_value

    def unsorted_next(self):
        if not self.iterators:
            raise StopIteration
        if self.iterator_index >= len(self.iterators):
            self.iterator_index = 0
        iterator = self.iterators[self.iterator_index]
        try:
            next_value = next(iterator)
        except StopIteration:
            self.iterators.pop(self.iterator_index)
            return self.unsorted_next()
        else:
            self.iterator_index += 1
            return next_value
