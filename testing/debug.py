from typing import Iterable, Iterator
from itertools import islice, takewhile, groupby


class Enumerable(object):
    def __init__(self, data_source):
        assert isinstance(data_source, Iterable)

        if not isinstance(data_source, Iterator):
            self._data_source = iter(data_source)
        else:
            self._data_source = data_source

    def __iter__(self):
        return self

    def __next__(self):
        return next(self._data_source)

    def where(self, predicate):
        self._data_source = (element for element in self._data_source if predicate(element))
        return self

    def first_or_none(self):
        return next(self, None)

    def take(self, num):
        self._data_source = islice(self._data_source, num)
        return self

    def take_while(self, predicate):
        self._data_source = takewhile(predicate, self._data_source)
        return self

    def distinct(self, key=None):
        seen = set()
        if key is None:
            for element in (element for element in self._data_source if not seen.__contains__(element)):
                seen.add(element)
                yield element
        else:
            for element in self._data_source:
                k = key(element)
                if k not in seen:
                    seen.add(k)
                    yield element

    def sort_by(self, key=None):
        self._data_source = iter(sorted(self._data_source, key=key))
        return self

    def group_by(self, key=None):
        self.sort_by(key)
        for k, g in groupby(self._data_source, key):
            yield (k, Enumerable(g))


res = Enumerable([1,2,3,3,3,3,2,2,2,1,1,1,1,4,4,4,3,3,2,3,4,4,1,1])

t = res.where(lambda i: i == 8).first_or_none()
pass
