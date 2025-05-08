
from bisect import bisect_left
from collections import deque
from collections.abc import Iterator as ABCIterator
from typing import (
    Any, Callable, Deque,
    Iterable, Iterator, Sequence,
    Tuple, TypeVar, Union
)


T = TypeVar('T')

IterableOrIterator = Union[Iterable[T], Iterator[T]]

KeyFunction = Callable[[T], T]


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


class MergeSourceContainer(ABCIterator):
    """This might be moved inside the MergeQueue class"""

    def __init__(self, source: IterableOrIterator, key=None):
        self.source: Iterator[T] = iter(source)
        self.next_value: T = next(self.source)
        self.reached_end: bool = False
        self.key = key

    def __lt__(self, rhs):
        if not isinstance(rhs, MergeSourceContainer):
            raise ValueError(
                f"< between a {type(self)} and a {type(rhs)} not supported"
            )
        key = self.key
        if key:
            return key(self.next_value) < key(rhs.next_value)
        return self.next_value < rhs.next_value

    def __iter__(self):
        return self

    def __next__(self):
        output_value = self.next_value
        try:
            self.next_value = next(self.source)
        except StopIteration as error:
            if self.reached_end:
                raise error
            else:
                self.reached_end = True
        return output_value


class MergeQueue(ABCIterator):

    def __iter__(self):
        return self

    def __next__(self):
        raise NotImplementedError("Subclasses should Implement")


class UnsortedMergeQueue(MergeQueue):

    """This object is similar to itertools.chain in that it generates a
    sequence of values from multiple iterables (or iterators).  Unlike chain,
    which returns all items from an iterable before moving to the next
    iterable, MergeQueue cycles through the iterables until all the iterables
    are exhausted.

    If the iterables are sorted, and you wish to retain the sort order
    set is_sorted to True.  This will cause the MergeQueue to look at the
    next value for each iterable and return the lowest (unless the reverse
    flag is set).  There is also a key argument similar to that for the
    built-in sorted."""

    def __init__(self, sources: Sequence[IterableOrIterator]):
        self.source_containers: Deque[IterableOrIterator] = deque(
            MergeSourceContainer(s) for s in sources
        )
        print(f"In __init__ {type(self.source_containers)=}")

    def __next__(self):
        print(f"In __next__ {type(self.source_containers)=}")
        container = self.source_containers.popleft()
        try:
            value = next(container)
        except StopIteration as error:
            if len(self.source_containers) == 0:
                raise error
            return self.__next__()
        else:
            self.source_containers.append(container)
            return value


class SortedMergeQueue(MergeQueue):

    def __init__(
            self,
            sources: Sequence[IterableOrIterator],
            key=None,
    ):
        self.sources = []
        for source in sources:
            try:
                node = MergeSourceContainer(source, key)
            except StopIteration:
                continue
            else:
                self.sources.insert(
                    bisect_left(self.sources, node),
                    node
                )

    def __next__(self):
        while self.sources:
            node = self.sources.pop(0)

            try:
                next_value = next(node)
            except StopIteration:
                # This node is exhausted see if next node has a next value
                continue
            else:
                self.sources.insert(
                    bisect_left(self.sources, node),
                    node,
                )
                return next_value

        # All sources have been exhausted and removed from list
        raise StopIteration()


def merge_queue_factory(
        sources: Sequence[IterableOrIterator],
        is_sorted: bool = True,
        key=None,
):
    if is_sorted:
        return SortedMergeQueue(sources, key)
    if key:
        raise ValueError(
            "Key function provided but unsorted MegeQueue requested"
        )
    return UnsortedMergeQueue(sources)
