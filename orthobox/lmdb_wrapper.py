# -*- coding: utf-8 -*-
"""
Dict-like wrapper for simple lmdb access.
"""
from __future__ import division, absolute_import, print_function, unicode_literals

import lmdb

from tempfile import mkdtemp
from collections import MutableMapping


class LMDB_Dict(MutableMapping):
    """
    A naïve abstraction for lmdb.
    """
    def __init__(self, environment=None, db_name=None, encoding='utf-8'):
        self.env = environment if isinstance(environment, lmdb.Environment) else lmdb.open(mkdtemp())
        self.encoding = encoding
        self.db = environment.open_db(self._encode(db_name) if db_name else None)

    def _encode(self, text):
        try:
            return text.encode(self.encoding)
        except AttributeError:
            raise TypeError("Unable to encode", text)

    def _decode(self, binary):
        try:
            return binary.decode(self.encoding)
        except AttributeError:
            raise TypeError("Unable to decode", binary)

    def txn(self, write=False):
        # TODO: prevent multiple write transactions
        return self.env.begin(db=self.db, write=write)

    def __len__(self):
        with self.txn() as txn:
            return txn.stat()['entries']

    def __iter__(self):
        with self.txn() as txn:
            for key in txn.cursor().iternext(values=False):
                yield self._decode(key)

    def __contains__(self, key):
        with self.txn() as txn:
            return txn.get(self._encode(key)) is not None

    def __getitem__(self, key):
        with self.txn() as txn:
            value = txn.get(self._encode(key))
        if value is None:
            raise KeyError(key)
        return self._decode(value)

    def __setitem__(self, key, value):
        with self.txn(True) as txn:
            txn.put(self._encode(key), self._encode(value))

    def __delitem__(self, key):
        with self.txn(True) as txn:
            if not txn.delete(self._encode(key)):   # Returns False if no key found
                raise KeyError(key)

    def keys(self):
        with self.txn() as txn:
            return [self._decode(key) for key in txn.cursor().iternext(values=False)]

    def values(self):
        with self.txn() as txn:
            return [self._decode(value) for value in txn.cursor().iternext(keys=False)]

    def items(self):
        with self.txn() as txn:
            return [(map(self._decode, item)) for item in txn.cursor().iternext()]

    def get(self, key, default=None):
        with self.txn() as txn:
            result = txn.get(self._encode(key), default)
            if result is not default:
                return self._decode(result)
            return default

    def pop(self, key, default=None):
        with self.txn(True) as txn:
            result = txn.pop(self._encode(key))
        if result is not None:
            return self._decode(result)
        if default is not None:
            return default
        # Nothing removed, no default
        raise KeyError(key)

    def popitem(self):
        with self.txn(True) as txn:
            cursor = txn.cursor()
            result = cursor.first()
            if not result:
                raise KeyError("Empty database")
            key, value = cursor.item()
            cursor.delete()
            return tuple(map(self._decode, (key, value)))

    def clear(self):
        with self.txn(True) as txn:
            txn.drop(self.db, delete=False)

    def setdefault(self, key, default=None):
        with self.txn(True) as txn:
            result = txn.get(self._encode(key))
            if result is not None:
                return self._decode(result)
            txn.put(self._encode(key), self._encode(default or ''))
            return default
