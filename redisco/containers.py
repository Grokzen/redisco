# -*- coding: utf-8 -*-
# doctest: +ELLIPSIS

import collections
from . import default_expire_time


def _parse_values(values):
    (_values,) = values if len(values) == 1 else (None,)
    if _values and type(_values) == type([]):
        return _values
    return values


class Container(object):
    """
    Base class for all containers. This class should not
    be used and does not provide anything except the ``db``
    member.
    :members:
    """

    def __init__(self, key, db=None, pipeline=None):
        self._db = db
        self.key = key
        self.pipeline = pipeline

    def clear(self):
        """
        Remove the container from the redis storage

        >>> s = Set('test')
        >>> s.add('1')
        1
        >>> s.clear()
        >>> s.members
        set()


        """
        del self.db[self.key]

    def set_expire(self, time=None):
        """
        Allow the key to expire after ``time`` seconds.

        >>> s = Set("test")
        >>> s.add("1")
        1
        >>> s.set_expire(1)
        >>> # from time import sleep
        >>> # sleep(1)
        >>> # s.members
        # set([])
        >>> s.clear()


        :param time: time expressed in seconds. If time is not specified, then ``default_expire_time`` will be used.
        :rtype: None
        """
        if time is None:
            time = default_expire_time
        self.db.expire(self.key, time)

    @property
    def db(self):
        if self.pipeline is not None:
            return self.pipeline
        if self._db is not None:
            return self._db
        if hasattr(self, 'db_cache') and self.db_cache:
            return self.db_cache
        else:
            from redisco import connection
            self.db_cache = connection
            return self.db_cache


class Set(Container):
    """
    .. default-domain:: set

    This class represent a Set in redis.
    """

    def __repr__(self):
        return "<%s '%s' %s>" % (self.__class__.__name__, self.key,
                                 self.members)

    def sadd(self, *values):
        """
        Add the specified members to the Set.

        :param values: a list of values or a simple value.
        :rtype: integer representing the number of value added to the set.

        >>> s = Set("test")
        >>> s.clear()
        >>> s.add(["1", "2", "3"])
        3
        >>> s.add(["4"])
        1
        >>> import testfixtures
        >>> testfixtures.compare(s.members, {'4', '3', '2', '1'})
        <identity>
        >>> s.clear()

        """
        return self.db.sadd(self.key, *_parse_values(values))

    def srem(self, *values):
        """
        Remove the values from the Set if they are present.

        :param values: a list of values or a simple value.
        :rtype: boolean indicating if the values have been removed.

        >>> s = Set("test")
        >>> s.add(["1", "2", "3"])
        3
        >>> s.srem(["1", "3"])
        2
        >>> s.clear()

        """
        return self.db.srem(self.key, *_parse_values(values))

    def spop(self):
        """
        Remove and return (pop) a random element from the Set.

        :rtype: String representing the value poped.

        >>> s = Set("test")
        >>> s.add("1")
        1
        >>> s.spop()
        '1'
        >>> s.members
        set()

        """
        return self.db.spop(self.key)

    #def __repr__(self):
    #    return "<%s '%s' %s>" % (self.__class__.__name__, self.key,
    #            self.members)

    def isdisjoint(self, other):
        """
        Return True if the set has no elements in common with other.

        :param other: another ``Set``
        :rtype: boolean

        >>> s1 = Set("key1")
        >>> s2 = Set("key2")
        >>> s1.add(['a', 'b', 'c'])
        3
        >>> s2.add(['c', 'd', 'e'])
        3
        >>> s1.isdisjoint(s2)
        False
        >>> s1.clear()
        >>> s2.clear()
        """
        return not bool(self.db.sinter([self.key, other.key]))

    def issubset(self, other_set):
        """
        Test whether every element in the set is in other.

        :param other_set: another ``Set`` to compare to.

        >>> s1 = Set("key1")
        >>> s2 = Set("key2")
        >>> s1.add(['a', 'b', 'c'])
        3
        >>> s2.add('b')
        1
        >>> s2.issubset(s1)
        True
        >>> s1.clear()
        >>> s2.clear()

        """
        return self <= other_set

    def __le__(self, other_set):
        return self.db.sinter([self.key, other_set.key]) == self.all()

    def __lt__(self, other_set):
        """Test whether the set is a true subset of other."""
        return self <= other_set and self != other_set

    def __eq__(self, other_set):
        """
        Test equality of:
        1. keys
        2. members
        """
        if other_set.key == self.key:
            return True
        slen, olen = len(self), len(other_set)
        if olen == slen:
            return self.members == other_set.members
        else:
            return False

    def __ne__(self, other_set):
        return not self.__eq__(other_set)

    def issuperset(self, other_set):
        """
        Test whether every element in other is in the set.

        :param other_set: another ``Set`` to compare to.

        >>> s1 = Set("key1")
        >>> s2 = Set("key2")
        >>> s1.add(['a', 'b', 'c'])
        3
        >>> s2.add('b')
        1
        >>> s1.issuperset(s2)
        True
        >>> s1.clear()
        >>> s2.clear()

        """
        return self >= other_set

    def __ge__(self, other_set):
        """Test whether every element in other is in the set."""
        return self.db.sinter([self.key, other_set.key]) == other_set.all()

    def __gt__(self, other_set):
        """Test whether the set is a true superset of other."""
        return self >= other_set and self != other_set

    # SET Operations
    def union(self, key, *other_sets):
        """
        Return a new ``Set`` representing the union of *n* sets.

        :param key: String representing the key where to store the result (the union)
        :param other_sets: list of other ``Set``.
        :rtype: ``Set``

        >>> s1 = Set('key1')
        >>> s2 = Set('key2')
        >>> s1.add(['a', 'b', 'c'])
        3
        >>> s2.add(['d', 'e'])
        2
        >>> s3 = s1.union('key3', s2)
        >>> s3.key
        'key3'
        >>> import testfixtures
        >>> testfixtures.compare(s3.members, {'a', 'c', 'b', 'e', 'd'})
        <identity>
        >>> s1.clear()
        >>> s2.clear()
        >>> s3.clear()

        """
        if not isinstance(key, str):
            raise ValueError("Expect a string as key")
        key = str(key)

        self.db.sunionstore(key, [self.key] + [o.key for o in other_sets])
        return Set(key)

    def intersection(self, key, *other_sets):
        """
        Return a new ``Set`` representing the intersection of *n* sets.

        :param key: String representing the key where to store the result (the union)
        :param other_sets: list of other ``Set``.
        :rtype: Set

        >>> s1 = Set('key1')
        >>> s2 = Set('key2')
        >>> s1.add(['a', 'b', 'c'])
        3
        >>> s2.add(['c', 'e'])
        2
        >>> s3 = s1.intersection('key3', s2)
        >>> s3.key
        'key3'
        >>> s3.members
        {'c'}
        >>> s1.clear()
        >>> s2.clear()
        >>> s3.clear()
        """
        if not isinstance(key, str):
            raise ValueError("Expect a string as key")
        key = str(key)

        self.db.sinterstore(key, [self.key] + [o.key for o in other_sets])
        return Set(key)

    def difference(self, key, *other_sets):
        """
        Return a new ``Set`` representing the difference of *n* sets.

        :param key: String representing the key where to store the result (the union)
        :param other_sets: list of other ``Set``.
        :rtype: Set

        >>> s1 = Set('key1')
        >>> s2 = Set('key2')
        >>> s1.add(['a', 'b', 'c'])
        3
        >>> s2.add(['c', 'e'])
        2
        >>> s3 = s1.difference('key3', s2)
        >>> s3.key
        'key3'
        >>> import testfixtures
        >>> testfixtures.compare(s3.members, {'a', 'b'})
        <identity>
        >>> s1.clear()
        >>> s2.clear()
        >>> s3.clear()
        """
        if not isinstance(key, str):
            raise ValueError("Expect a string as key")
        key = str(key)

        self.db.sdiffstore(key, [self.key] + [o.key for o in other_sets])
        return Set(key)

    def update(self, *other_sets):
        """Update the set, adding elements from all other_sets.

        :param other_sets: list of ``Set``
        :rtype: None
        """
        self.db.sunionstore(self.key, [self.key] + [o.key for o in other_sets])

    def __ior__(self, other_set):
        self.db.sunionstore(self.key, [self.key, other_set.key])
        return self

    def intersection_update(self, *other_sets):
        """
        Update the set, keeping only elements found in it and all other_sets.

        :param other_sets: list of ``Set``
        :rtype: None
        """
        self.db.sinterstore(self.key, [o.key for o in [self.key] + other_sets])

    def __iand__(self, other_set):
        self.db.sinterstore(self.key, [self.key, other_set.key])
        return self

    def difference_update(self, *other_sets):
        """
        Update the set, removing elements found in others.

        :param other_sets: list of ``Set``
        :rtype: None
        """
        self.db.sdiffstore(self.key, [o.key for o in [self.key] + other_sets])

    def __isub__(self, other_set):
        self.db.sdiffstore(self.key, [self.key, other_set.key])
        return self

    def all(self):
        return self.db.smembers(self.key)

    members = property(all)
    """
    return the real content of the Set.
    """

    def copy(self, key):
        """
        Copy the set to another key and return the new Set.

        .. WARNING::
            If the new key already contains a value, it will be overwritten.
        """
        copy = Set(key=key, db=self.db)
        copy.clear()
        copy |= self
        return copy

    def __iter__(self):
        return self.members.__iter__()

    def sinter(self, *other_sets):
        """
        Performs an intersection between Sets and return the *RAW* result.

        .. NOTE::
            This function return an actual ``set`` object (from python) and not a ``Set``. See func:``intersection``.
        """
        return self.db.sinter([self.key] + [s.key for s in other_sets])

    def sunion(self, *other_sets):
        """
        Performs a union between two sets and returns the *RAW* result.

        .. NOTE::
            This function return an actual ``set`` object (from python) and not a ``Set``.
        """
        return self.db.sunion([self.key] + [s.key for s in other_sets])

    def sdiff(self, *other_sets):
        """
        Performs a difference between two sets and returns the *RAW* result.

        .. NOTE::
            This function return an actual ``set`` object (from python) and not a ``Set``.
            See function difference.

        """
        return self.db.sdiff([self.key] + [s.key for s in other_sets])

    def scard(self):
        """
        Returns the cardinality of the Set.

        :rtype: String containing the cardinality.

        """
        return self.db.scard(self.key)

    def sismember(self, value):
        """
        Return ``True`` if the provided value is in the ``Set``.

        """
        return self.db.sismember(self.key, value)

    def srandmember(self):
        """
        Return a random member of the set.

        >>> s = Set("test")
        >>> s.add(['a', 'b', 'c'])
        3
        >>> s.srandmember() # doctest: +ELLIPSIS
        '...'
        >>> # 'a', 'b' or 'c'
        """
        return self.db.srandmember(self.key)

    add = sadd
    """see sadd"""
    pop = spop
    """see spop"""
    remove = srem
    """see srem"""
    __contains__ = sismember
    __len__ = scard


class List(Container):
    """
    This class represent a list object as seen in redis.
    """

    def all(self):
        """
        Returns all items in the list.
        """
        return self.lrange(0, -1)
    members = property(all)
    """Return all items in the list."""

    def llen(self):
        """
        Returns the length of the list.
        """
        return self.db.llen(self.key)

    __len__ = llen

    def __getitem__(self, index):
        if isinstance(index, int):
            return self.lindex(index)
        elif isinstance(index, slice):
            indices = index.indices(len(self))
            return self.lrange(indices[0], indices[1] - 1)
        else:
            raise TypeError

    def __setitem__(self, index, value):
        self.lset(index, value)

    def lrange(self, start, stop):
        """
        Returns a range of items.

        :param start: integer representing the start index of the range
        :param stop: integer representing the size of the list.

        >>> l = List("test")
        >>> l.push(['a', 'b', 'c', 'd'])
        4
        >>> l.lrange(1, 2)
        ['b', 'c']
        >>> l.clear()

        """
        return self.db.lrange(self.key, start, stop)

    def lpush(self, *values):
        """
        Push the value into the list from the *left* side

        :param values: a list of values or single value to push
        :rtype: long representing the number of values pushed.

        >>> l = List("test")
        >>> l.lpush(['a', 'b'])
        2
        >>> l.clear()
        """
        return self.db.lpush(self.key, *_parse_values(values))

    def rpush(self, *values):
        """
        Push the value into the list from the *right* side

        :param values: a list of values or single value to push
        :rtype: long representing the size of the list.

        >>> l = List("test")
        >>> l.lpush(['a', 'b'])
        2
        >>> l.rpush(['c', 'd'])
        4
        >>> l.members
        ['b', 'a', 'c', 'd']
        >>> l.clear()
        """

        return self.db.rpush(self.key, *_parse_values(values))

    def extend(self, iterable):
        """
        Extend list by appending elements from the iterable.

        :param iterable: an iterable objects.
        """
        self.rpush(*[e for e in iterable])

    def count(self, value):
        """
        Return number of occurrences of value.

        :param value: a value tha *may* be contained in the list
        """
        return self.members.count(value)

    def lpop(self):
        """
        Pop the first object from the left.

        :return: the popped value.

        """
        return self.db.lpop(self.key)

    def rpop(self):
        """
        Pop the first object from the right.

        :return: the popped value.
        """
        return self.db.rpop(self.key)

    def rpoplpush(self, key):
        """
        Remove an element from the list,
        atomically add it to the head of the list indicated by key

        :param key: the key of the list receiving the popped value.
        :return: the popped (and pushed) value

        >>> l = List('list1')
        >>> l.push(['a', 'b', 'c'])
        3
        >>> l.rpoplpush('list2')
        'c'
        >>> l2 = List('list2')
        >>> l2.members
        ['c']
        >>> l.clear()
        >>> l2.clear()

        """
        return self.db.rpoplpush(self.key, key)

    def lrem(self, value, num=1):
        """
        Remove first occurrence of value.

        :return: 1 if the value has been removed, 0 otherwise
        """
        return self.db.lrem(self.key, value, num)

    def reverse(self):
        """
        Reverse the list in place.

        :return: None
        """
        r = self[:]
        r.reverse()
        self.clear()
        self.extend(r)

    def copy(self, key):
        """Copy the list to a new list.

        ..WARNING:
            If destination key already contains a value, it clears it before copying.
        """
        copy = List(key, self.db)
        copy.clear()
        copy.extend(self)
        return copy

    def ltrim(self, start, end):
        """
        Trim the list from start to end.

        :return: None
        """
        return self.db.ltrim(self.key, start, end)

    def lindex(self, idx):
        """
        Return the value at the index *idx*

        :param idx: the index to fetch the value.
        :return: the value or None if out of range.
        """
        return self.db.lindex(self.key, idx)

    def lset(self, idx, value=0):
        """
        Set the value in the list at index *idx*

        :return: True is the operation succeed.

        >>> l = List('test')
        >>> l.push(['a', 'b', 'c'])
        3
        >>> l.lset(0, 'e')
        True
        >>> l.members
        ['e', 'b', 'c']
        >>> l.clear()

        """
        return self.db.lset(self.key, idx, value)

    def __iter__(self):
        return self.members.__iter__()

    def __repr__(self):
        return "<%s '%s' %s>" % (self.__class__.__name__, self.key, self.members)

    __len__ = llen
    remove = lrem
    trim = ltrim
    shift = lpop
    unshift = lpush
    pop = rpop
    pop_onto = rpoplpush
    push = rpush
    append = rpush


class TypedList(object):
    """Create a container to store a list of objects in Redis.

    Arguments:
        key -- the Redis key this container is stored at
        target_type -- can be a Python object or a redisco model class.

    Optional Arguments:
        type_args -- additional args to pass to type constructor (tuple)
        type_kwargs -- additional kwargs to pass to type constructor (dict)

    If target_type is not a redisco model class, the target_type should
    also a callable that casts the (string) value of a list element into
    target_type. E.g. str, int, float -- using this format:

        target_type(string_val_of_list_elem, *type_args, **type_kwargs)

    target_type also accepts a string that refers to a redisco model.
    """

    def __init__(self, key, target_type, type_args=[], type_kwargs={}, **kwargs):
        self.list = List(key, **kwargs)
        self.klass = self.value_type(target_type)
        self._klass_args = type_args
        self._klass_kwargs = type_kwargs
        from .models.base import Model
        self._redisco_model = issubclass(self.klass, Model)

    def value_type(self, target_type):
        if isinstance(target_type, str):
            t = target_type
            from .models.base import get_model_from_key
            target_type = get_model_from_key(target_type)
            if target_type is None:
                raise ValueError("Unknown Redisco class %s" % t)
        return target_type

    def typecast_item(self, value):
        if self._redisco_model:
            return self.klass.objects.get_by_id(value)
        else:
            return self.klass(value, *self._klass_args, **self._klass_kwargs)

    def typecast_iter(self, values):
        if self._redisco_model:
            return [o for o in [self.klass.objects.get_by_id(v) for v in values] if o is not None]
        else:
            return [self.klass(v, *self._klass_args, **self._klass_kwargs) for v in values]

    def all(self):
        """Returns all items in the list."""
        return self.typecast_iter(self.list.all())

    def __len__(self):
        return len(self.list)

    def __getitem__(self, index):
        val = self.list[index]
        if isinstance(index, slice):
            return self.typecast_iter(val)
        else:
            return self.typecast_item(val)

    def typecast_stor(self, value):
        if self._redisco_model:
            return value.id
        else:
            return value

    def append(self, value):
        self.list.append(self.typecast_stor(value))

    def extend(self, iter):
        self.list.extend(map(lambda i: self.typecast_stor(i), iter))

    def __setitem__(self, index, value):
        self.list[index] = self.typecast_stor(value)

    def __iter__(self):
        for i in range(len(self.list)):
            yield self[i]

    def __repr__(self):
        return repr(self.typecast_iter(self.list))


class SortedSet(Container):
    """
    This class represents a SortedSet in redis.
    Use it if you want to arrange your set in any order.

    """

    def __getitem__(self, index):
        if isinstance(index, slice):
            return self.zrange(index.start, index.stop)
        else:
            return self.zrange(index, index)[0]

    def score(self, member):
        """
        Returns the score of member.
        """
        return self.zscore(member)

    def __contains__(self, val):
        return self.zscore(val) is not None

    @property
    def members(self):
        """
        Returns the members of the set.
        """
        return self.zrange(0, -1)

    @property
    def revmembers(self):
        """
        Returns the members of the set in reverse.
        """
        return self.zrevrange(0, -1)

    def __iter__(self):
        return self.members.__iter__()

    def __reversed__(self):
        return self.revmembers.__iter__()

    # def __repr__(self):
    #     return "<%s '%s' %s>" % (self.__class__.__name__, self.key,
    #                              self.members)

    @property
    def _min_score(self):
        """
        Returns the minimum score in the SortedSet.
        """
        try:
            return self.zscore(self.__getitem__(0))
        except IndexError:
            return None

    @property
    def _max_score(self):
        """
        Returns the maximum score in the SortedSet.
        """
        try:
            self.zscore(self.__getitem__(-1))
        except IndexError:
            return None

    def lt(self, v, limit=None, offset=None):
        """
        Returns the list of the members of the set that have scores
        less than v.

        :param v: the score to compare to.
        :param limit: limit the result to *n* elements
        :param offset: Skip the first *n* elements
        """
        if limit is not None and offset is None:
            offset = 0
        return self.zrangebyscore("-inf", "(%f" % v,
                                  start=offset, num=limit)

    def le(self, v, limit=None, offset=None):
        """
        Returns the list of the members of the set that have scores
        less than or equal to v.

        :param v: the score to compare to.
        :param limit: limit the result to *n* elements
        :param offset: Skip the first *n* elements

        """
        if limit is not None and offset is None:
            offset = 0
        return self.zrangebyscore("-inf", v,
                                  start=offset, num=limit)

    def gt(self, v, limit=None, offset=None, withscores=False):
        """Returns the list of the members of the set that have scores
        greater than v.
        """
        if limit is not None and offset is None:
            offset = 0
        return self.zrangebyscore("(%f" % v, "+inf",
                                  start=offset, num=limit, withscores=withscores)

    def ge(self, v, limit=None, offset=None, withscores=False):
        """Returns the list of the members of the set that have scores
        greater than or equal to v.

        :param v: the score to compare to.
        :param limit: limit the result to *n* elements
        :param offset: Skip the first *n* elements

        """
        if limit is not None and offset is None:
            offset = 0
        return self.zrangebyscore("%f" % v, "+inf",
                                  start=offset, num=limit, withscores=withscores)

    def between(self, min, max, limit=None, offset=None):
        """
        Returns the list of the members of the set that have scores
        between min and max.

        .. Note::
            The min and max are inclusive when comparing the values.

        :param min: the minimum score to compare to.
        :param max: the maximum score to compare to.
        :param limit: limit the result to *n* elements
        :param offset: Skip the first *n* elements

        >>> s = SortedSet("foo")
        >>> s.add('a', 10)
        1
        >>> s.add('b', 20)
        1
        >>> s.add('c', 30)
        1
        >>> s.between(20, 30)
        ['b', 'c']
        >>> s.clear()
        """
        if limit is not None and offset is None:
            offset = 0
        return self.zrangebyscore(min, max,
                                  start=offset, num=limit)

    def zadd(self, members, score=1):
        """
        Add members in the set and assign them the score.

        :param members: a list of item or a single item
        :param score: the score the assign to the item(s)

        >>> s = SortedSet("foo")
        >>> s.add('a', 10)
        1
        >>> s.add('b', 20)
        1
        >>> s.clear()
        """
        _members = []
        if not isinstance(members, dict):
            _members = [score, members]
        else:
            for member, score in members.items():
                _members += [score, member]

        return self.db.zadd(self.key, *_members)

    def zrem(self, *values):
        """
        Remove the values from the SortedSet

        :return: True if **at least one** value is successfully
                 removed, False otherwise

        >>> s = SortedSet('foo')
        >>> s.add('a', 10)
        1
        >>> s.zrem('a')
        1
        >>> s.members
        []
        >>> s.clear()
        """
        return self.db.zrem(self.key, *_parse_values(values))

    def zincrby(self, att, value=1):
        """
        Increment the score of the item by ``value``

        :param att: the member to increment
        :param value: the value to add to the current score
        :returns: the new score of the member

        >>> s = SortedSet("foo")
        >>> s.add('a', 10)
        1
        >>> s.zincrby("a", 10)
        20.0
        >>> s.clear()
        """
        return self.db.zincrby(self.key, att, value)

    def zrevrank(self, member):
        """
        Returns the ranking in reverse order for the member

        >>> s = SortedSet("foo")
        >>> s.add('a', 10)
        1
        >>> s.add('b', 20)
        1
        >>> s.revrank('a')
        1
        >>> s.clear()
        """
        return self.db.zrevrank(self.key, member)

    def zrange(self, start, stop, withscores=False):
        """
        Returns all the elements including between ``start`` (non included) and
        ``stop`` (included).

        :param withscore: True if the score of the elements should
                          also be returned

        >>> s = SortedSet("foo")
        >>> s.add('a', 10)
        1
        >>> s.add('b', 20)
        1
        >>> s.add('c', 30)
        1
        >>> s.zrange(1, 3)
        ['b', 'c']
        >>> s.zrange(1, 3, withscores=True)
        [('b', 20.0), ('c', 30.0)]
        >>> s.clear()
        """
        return self.db.zrange(self.key, start, stop, withscores=withscores)

    def zrevrange(self, start, end, **kwargs):
        """
        Returns the range of items included between ``start`` and ``stop``
        in reverse order (from high to low)

        >>> s = SortedSet("foo")
        >>> s.add('a', 10)
        1
        >>> s.add('b', 20)
        1
        >>> s.add('c', 30)
        1
        >>> s.zrevrange(1, 2)
        ['b', 'a']
        >>> s.clear()
        """
        return self.db.zrevrange(self.key, start, end, **kwargs)

    def zrangebyscore(self, min, max, **kwargs):
        """
        Returns the range of elements included between the scores (min and max)

        >>> s = SortedSet("foo")
        >>> s.add('a', 10)
        1
        >>> s.add('b', 20)
        1
        >>> s.add('c', 30)
        1
        >>> s.zrangebyscore(20, 30)
        ['b', 'c']
        >>> s.clear()
        """
        return self.db.zrangebyscore(self.key, min, max, **kwargs)

    def zrevrangebyscore(self, max, min, **kwargs):
        """
        Returns the range of elements included between the scores (min and max)

        >>> s = SortedSet("foo")
        >>> s.add('a', 10)
        1
        >>> s.add('b', 20)
        1
        >>> s.add('c', 30)
        1
        >>> s.zrangebyscore(20, 20)
        ['b']
        >>> s.clear()
        """
        return self.db.zrevrangebyscore(self.key, max, min, **kwargs)

    def zcard(self):
        """
        Returns the cardinality of the SortedSet.

        >>> s = SortedSet("foo")
        >>> s.add("a", 1)
        1
        >>> s.add("b", 2)
        1
        >>> s.add("c", 3)
        1
        >>> s.zcard()
        3
        >>> s.clear()
        """
        return self.db.zcard(self.key)

    def zscore(self, elem):
        """
        Return the score of an element

        >>> s = SortedSet("foo")
        >>> s.add("a", 10)
        1
        >>> s.score("a")
        10.0
        >>> s.clear()
        """
        return self.db.zscore(self.key, elem)

    def zremrangebyrank(self, start, stop):
        """
        Remove a range of element between the rank ``start`` and
        ``stop`` both included.

        :return: the number of item deleted

        >>> s = SortedSet("foo")
        >>> s.add("a", 10)
        1
        >>> s.add("b", 20)
        1
        >>> s.add("c", 30)
        1
        >>> s.zremrangebyrank(1, 2)
        2
        >>> s.members
        ['a']
        >>> s.clear()
        """
        return self.db.zremrangebyrank(self.key, start, stop)

    def zremrangebyscore(self, min_value, max_value):
        """
        Remove a range of element by between score ``min_value`` and
        ``max_value`` both included.

        :returns: the number of items deleted.

        >>> s = SortedSet("foo")
        >>> s.add("a", 10)
        1
        >>> s.add("b", 20)
        1
        >>> s.add("c", 30)
        1
        >>> s.zremrangebyscore(10, 20)
        2
        >>> s.members
        ['c']
        >>> s.clear()
        """

        return self.db.zremrangebyscore(self.key, min_value, max_value)

    def zrank(self, elem):
        """
        Returns the rank of the element.

        >>> s = SortedSet("foo")
        >>> s.add("a", 10)
        1
        >>> s.zrank("a")
        0
        >>> s.clear()
        """
        return self.db.zrank(self.key, elem)

    def eq(self, value):
        """
        Returns the elements that have ``value`` for score.
        """
        return self.zrangebyscore(value, value)

    __len__ = zcard
    revrank = zrevrank
    score = zscore
    rank = zrank
    incr_by = zincrby
    add = zadd
    remove = zrem


class NonPersistentList(object):
    def __init__(self, l):
        self._list = l

    @property
    def members(self):
        return self._list

    def __iter__(self):
        return iter(self.members)

    def __len__(self):
        return len(self._list)


class Hash(Container, collections.MutableMapping):

    def __iter__(self):
        return self.hgetall().__iter__()

    def __repr__(self):
        return "<%s '%s' %s>" % (self.__class__.__name__,
                                 self.key, self.hgetall())

    def _set_dict(self, new_dict):
        self.clear()
        self.update(new_dict)

    def hlen(self):
        """
        Returns the number of elements in the Hash.
        """
        return self.db.hlen(self.key)

    def hset(self, member, value):
        """
        Set ``member`` in the Hash at ``value``.

        :returns: 1 if member is a new field and the value has been
                  stored, 0 if the field existed and the value has been
                  updated.

        >>> h = Hash("foo")
        >>> h.hset("bar", "value")
        1
        >>> h.clear()
        """
        return self.db.hset(self.key, member, value)

    def hdel(self, *members):
        """
        Delete one or more hash field.

        :param members: on or more fields to remove.
        :return: the number of fields that were removed

        >>> h = Hash("foo")
        >>> h.hset("bar", "value")
        1
        >>> h.hdel("bar")
        1
        >>> h.clear()
        """
        return self.db.hdel(self.key, *_parse_values(members))

    def hkeys(self):
        """
        Returns all fields name in the Hash
        """
        return self.db.hkeys(self.key)

    def hgetall(self):
        """
        Returns all the fields and values in the Hash.

        :rtype: dict
        """
        return self.db.hgetall(self.key)

    def hvals(self):
        """
        Returns all the values in the Hash

        :rtype: list
        """
        return self.db.hvals(self.key)

    def hget(self, field):
        """
        Returns the value stored in the field, None if the field doesn't exist.
        """
        return self.db.hget(self.key, field)

    def hexists(self, field):
        """
        Returns ``True`` if the field exists, ``False`` otherwise.
        """
        return self.db.hexists(self.key, field)

    def hincrby(self, field, increment=1):
        """
        Increment the value of the field.
        :returns: the value of the field after incrementation

        >>> h = Hash("foo")
        >>> h.hincrby("bar", 10)
        10
        >>> h.hincrby("bar", 2)
        12
        >>> h.clear()
        """
        return self.db.hincrby(self.key, field, increment)

    def hmget(self, fields):
        """
        Returns the values stored in the fields.
        """
        return self.db.hmget(self.key, fields)

    def hmset(self, mapping):
        """
        Sets or updates the fields with their corresponding values.

        :param mapping: a dict with keys and values
        """
        return self.db.hmset(self.key, mapping)

    keys = hkeys
    values = hvals
    _get_dict = hgetall
    __getitem__ = hget
    __setitem__ = hset
    __delitem__ = hdel
    __len__ = hlen
    __contains__ = hexists
    dict = property(_get_dict, _set_dict)
