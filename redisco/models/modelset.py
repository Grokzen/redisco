# -*- coding: utf-8 -*-
"""
Handles the queries.
"""
# redisco imports
import redisco
from redisco.containers import SortedSet, Set, List
from redisco.models.exceptions import AttributeNotIndexed


# Model Set
class ModelSet(Set):
    def __init__(self, model_class):
        self.model_class = model_class
        self.key = model_class._all_key
        # We access directly _meta as .db is a property and should be
        # access from an instance, not a Class
        self._db = model_class._meta['db'] or redisco.get_client()
        self._filters = {}
        self._exclusions = {}
        self._zfilters = []
        self._ordering = []
        self._limit = None
        self._offset = None
        self._return_values = False

    #################
    # MAGIC METHODS #
    #################

    def __getitem__(self, index):
        """
        Will look in _set to get the id and simply return the instance of the model.
        """
        if isinstance(index, slice):
            pipeline = self._db.pipeline()
            for id in self._set[index]:
                pipeline.hgetall(self.model_class.instance_key(id))
            rawdata = pipeline.execute()
            if self._return_values:
                return rawdata
            else:
                instances = []
                for id, rd in zip(self._set[index], rawdata):
                    instances.append(self.model_class.load_from_raw_data(id, rd))
                return instances
        else:
            id = self._set[index]
            if id:
                return self._get_item_with_id(id)
            else:
                raise IndexError

    def __repr__(self):
        if len(self._set) > 30:
            m = self._set[:30]
        else:
            m = self._set
        # s = map(lambda id: self._get_item_with_id(id), m)
        s = [self._get_item_with_id(id) for id in m]
        return "%s" % s

    def __iter__(self):
        for id in self._set:
            yield self._get_item_with_id(id)

    def __len__(self):
        return len(self._set)

    def __contains__(self, val):
        return val.id in self._set

    ##########################################
    # METHODS THAT RETURN A SET OF INSTANCES #
    ##########################################
    def get_by_id(self, id):
        """
        Returns the object definied by ``id``.

        :param id: the ``id`` of the objects to lookup.
        :returns: The object instance or None if not found.

        >>> from redisco import models
        >>> class Foo(models.Model):
        ...     name = models.Attribute()
        ...
        >>> f = Foo(name="Einstein")
        >>> f.save()
        True
        >>> Foo.objects.get_by_id(f.id) == f
        True
        >>> [f.delete() for f in Foo.objects.all()] # doctest: +ELLIPSIS
        [...]
        """
        if (self._filters or self._exclusions or self._zfilters) and str(id) not in self._set:
            return
        return self._get_item_with_id(id)

    def get(self, **kwargs):
        return self.filter(**kwargs).first()

    def first(self):
        """
        Return the first object of a collections.

        :return: The object or Non if the lookup gives no result


        >>> from redisco import models
        >>> class Foo(models.Model):
        ...     name = models.Attribute()
        ...
        >>> f = Foo(name="toto")
        >>> f.save()
        True
        >>> Foo.objects.filter(name="toto").first() # doctest: +ELLIPSIS
        <Foo:...>
        >>> [f.delete() for f in Foo.objects.all()] # doctest: +ELLIPSIS
        [...]
        """
        try:
            return self.limit(1).__getitem__(0)
        except IndexError:
            return None

    count = __len__

    #####################################
    # METHODS THAT MODIFY THE MODEL SET #
    #####################################

    def values(self):
        """
        Returns dictionaries rather than model-instance objects.
        """
        clone = self._clone()
        clone._return_values = True
        return clone

    def filter(self, **kwargs):
        """
        Filter a collection on criteria

        >>> from redisco import models
        >>> class Foo(models.Model):
        ...     name = models.Attribute()
        ...
        >>> Foo(name="toto").save()
        True
        >>> Foo(name="toto").save()
        True
        >>> Foo.objects.filter() # doctest: +ELLIPSIS
        [<Foo:...>, <Foo:...>]
        >>> [f.delete() for f in Foo.objects.all()] # doctest: +ELLIPSIS
        [...]
        """
        clone = self._clone()
        if not clone._filters:
            clone._filters = {}
        clone._filters.update(kwargs)
        return clone

    def exclude(self, **kwargs):
        """
        Exclude a collection within a lookup.


        >>> from redisco import models
        >>> class Foo(models.Model):
        ...    name = models.Attribute()
        ...    exclude_me = models.BooleanField()
        ...
        >>> Foo(name="Einstein").save()
        True
        >>> Foo(name="Edison", exclude_me=True).save()
        True
        >>> Foo.objects.exclude(exclude_me=True).first().name
        'Einstein'
        >>> [f.delete() for f in Foo.objects.all()] # doctest: +ELLIPSIS
        [...]
        """
        clone = self._clone()
        if not clone._exclusions:
            clone._exclusions = {}
        clone._exclusions.update(kwargs)
        return clone

    def zfilter(self, **kwargs):
        clone = self._clone()
        if not clone._zfilters:
            clone._zfilters = []
        clone._zfilters.append(kwargs)
        return clone

    # this should only be called once
    def order(self, field):
        """
        Enable ordering in collections when doing a lookup.

        .. Warning:: This should only be called once per lookup.

        >>> from redisco import models
        >>> class Foo(models.Model):
        ...    name = models.Attribute()
        ...    exclude_me = models.BooleanField()
        ...
        >>> Foo(name="Abba").save()
        True
        >>> Foo(name="Zztop").save()
        True
        >>> Foo.objects.all().order("-name").first().name
        'Zztop'
        >>> Foo.objects.all().order("name").first().name
        'Abba'
        >>> [f.delete() for f in Foo.objects.all()] # doctest: +ELLIPSIS
        [...]
        """
        fname = field.lstrip('-')
        if fname not in self.model_class._indices:
            raise ValueError("Order parameter should be an indexed attribute.")
        alpha = True
        if fname in self.model_class._attributes:
            v = self.model_class._attributes[fname]
            alpha = not v.zindexable
        clone = self._clone()
        if not clone._ordering:
            clone._ordering = []
        clone._ordering.append((field, alpha,))
        return clone

    def limit(self, n, offset=0):
        """
        Limit the size of the collection to *n* elements.
        """
        clone = self._clone()
        clone._limit = n
        clone._offset = offset
        return clone

    def create(self, **kwargs):
        """
        Create an object of the class.

        .. Note:: This is the same as creating an instance of the class and saving it.

        >>> from redisco import models
        >>> class Foo(models.Model):
        ...     name = models.Attribute()
        ...
        >>> Foo.objects.create(name="Obama") # doctest: +ELLIPSIS
        <Foo:...>
        >>> [f.delete() for f in Foo.objects.all()] # doctest: +ELLIPSIS
        [...]
        """
        instance = self.model_class(**kwargs)
        if instance.save():
            return instance
        else:
            return None

    def all(self):
        """
        Return all elements of the collection.
        """
        return self._clone()

    def get_or_create(self, **kwargs):
        """
        Return an element of the collection or create it if necessary.

        >>> from redisco import models
        >>> class Foo(models.Model):
        ...     name = models.Attribute()
        ...
        >>> new_obj = Foo.objects.get_or_create(name="Obama")
        >>> get_obj = Foo.objects.get_or_create(name="Obama")
        >>> new_obj == get_obj
        True
        >>> [f.delete() for f in Foo.objects.all()] # doctest: +ELLIPSIS
        [...]
        """
        opts = {}
        for k, v in kwargs.items():
            if k in self.model_class._indices:
                opts[k] = v
        o = self.filter(**opts).first()
        if o:
            return o
        else:
            return self.create(**kwargs)

    def get_indexed_values(self, attribute_name):
        """
        Return indexed values for a model attribute in unsorted form.

        >>> from redisco import models
        >>> class Foo(models.Model):
        ...     name = models.Attribute(indexed=True)
        ...
        >>> c = Foo.objects.create(name="Obama")
        >>> c = Foo.objects.create(name="Hollande")
        >>> c = Foo.objects.create(name="Merkel")
        >>> c = Foo.objects.create(name="Merkel")
        >>> a = Foo.objects.get_indexed_values("name")
        >>> b = ["Hollande", "Merkel", "Obama"]
        >>> [i in b for i in a]
        [True, True, True]
        """
        if attribute_name not in self.model_class._indices:
            # TODO: k is not defined O.o
            raise AttributeNotIndexed("Attribute %s is not indexed in %s class." % (k, self.model_class.__name__))
        wildcard_search_key = "%s:%s:*" % (self.model_class._key, attribute_name)
        keys = self._db.keys(wildcard_search_key)
        attribute = self.model_class._attributes[attribute_name]
        values = [attribute.typecast_for_read(k.split(":")[2]) for k in keys]
        return values

    @property
    def db(self):
        return self._db

    ###################
    # PRIVATE METHODS #
    ###################

    @property
    def _set(self):
        """
        This contains the list of ids that have been looked-up,
        filtered and ordered. This set is build hen we first access
        it and is cached for has long has the ModelSet exist.
        """
        # For performance reasons, only one zfilter is allowed.
        if hasattr(self, '_cached_set'):
            return self._cached_set
        s = Set(self.key, db=self.db)
        if self._zfilters:
            s = self._add_zfilters(s)
        if self._filters:
            s = self._add_set_filter(s)
        if self._exclusions:
            s = self._add_set_exclusions(s)
        n = self._order(s.key)
        self._cached_set = n
        return self._cached_set

    def _add_set_filter(self, s):
        """
        This function is the internal of the `filter` function.
        It simply creates a new "intersection" of indexed keys (the filter) and
        the previous filtered keys (if any).

        .. Note:: This function uses the ``Set`` container class.

        :return: the new Set
        """
        indices = []
        for k, v in self._filters.items():
            index = self._build_key_from_filter_item(k, v)
            if k not in self.model_class._indices:
                raise AttributeNotIndexed("Attribute %s is not indexed in %s class." % (k, self.model_class.__name__))
            indices.append(index)
        new_set_key = "~%s.%s" % ("+".join([self.key] + indices), id(self))
        s.intersection(new_set_key, *[Set(n, db=self.db) for n in indices])
        new_set = Set(new_set_key, db=self.db)
        new_set.set_expire()
        return new_set

    def _add_set_exclusions(self, s):
        """
        This function is the internals of the `filter` function.
        It simply creates a new "difference" of indexed keys (the filter) and
        the previous filtered keys (if any).

        .. Note:: This function uses the ``Set`` container class.

        :return: the new Set
        """
        indices = []
        for k, v in self._exclusions.items():
            index = self._build_key_from_filter_item(k, v)
            if k not in self.model_class._indices:
                raise AttributeNotIndexed("Attribute %s is not indexed in %s class." % (k, self.model_class.__name__))
            indices.append(index)
        new_set_key = "~%s.%s" % ("-".join([self.key] + indices), id(self))
        s.difference(new_set_key, *[Set(n, db=self.db) for n in indices])
        new_set = Set(new_set_key, db=self.db)
        new_set.set_expire()
        return new_set

    def _add_zfilters(self, s):
        """
        This function is the internals of the zfilter function.
        It will create a SortedSet and will compare the scores to
        the value provided.

        :return: a SortedSet with the ids.

        """
        k, v = next(iter(self._zfilters[0].items()))
        try:
            att, op = k.split('__')
        except ValueError:
            raise ValueError("zfilter should have an operator.")
        index = "%s:%s" % (self.model_class._key, att)
        desc = self.model_class._attributes[att]
        zset = SortedSet(index, db=self.db)
        limit, offset = self._get_limit_and_offset()
        new_set_key = "~%s.%s" % ("+".join([self.key, att, op]), id(self))
        new_set_key_temp = "#%s.%s" % ("+".join([self.key, att, op]), id(self))
        members = []
        if isinstance(v, (tuple, list,)):
            min, max = v
            min = float(desc.typecast_for_storage(min))
            max = float(desc.typecast_for_storage(max))
        else:
            v = float(desc.typecast_for_storage(v))
        if op == 'lt':
            members = zset.lt(v, limit, offset)
        elif op == 'gt':
            members = zset.gt(v, limit, offset)
        elif op == 'gte':
            members = zset.ge(v, limit, offset)
        elif op == 'le':
            members = zset.le(v, limit, offset)
        elif op == 'lte':
            members = zset.le(v, limit, offset)
        elif op == 'in':
            members = zset.between(min, max, limit, offset)

        temp_set = Set(new_set_key_temp, db=self.db)
        if members:
            temp_set.add(*members)
        temp_set.set_expire()

        s.intersection(new_set_key, temp_set)
        new_set = Set(new_set_key, db=self.db)
        new_set.set_expire()
        return new_set

    def _order(self, skey):
        """
        This function does not job. It will only call the good
        subfunction in case we want an ordering or not.
        """
        if self._ordering:
            return self._set_with_ordering(skey)
        else:
            return self._set_without_ordering(skey)

    def _set_with_ordering(self, skey):
        """
        Final call for finally ordering the looked-up collection.
        The ordering will be done by Redis itself and stored as a temporary set.

        :return: a Set of `id`
        """
        num, start = self._get_limit_and_offset()
        old_set_key = skey
        for ordering, alpha in self._ordering:
            if ordering.startswith('-'):
                desc = True
                ordering = ordering.lstrip('-')
            else:
                desc = False
            new_set_key = "%s#%s.%s" % (old_set_key, ordering, id(self))
            by = "%s:*->%s" % (self.model_class._key, ordering)
            self.db.sort(old_set_key,
                         by=by,
                         store=new_set_key,
                         alpha=alpha,
                         start=start,
                         num=num,
                         desc=desc)
            if old_set_key != self.key:
                Set(old_set_key, db=self.db).set_expire()
            new_list = List(new_set_key, db=self.db)
            new_list.set_expire()
            return new_list

    def _set_without_ordering(self, skey):
        """
        Final call for "non-ordered" looked up.
        We order by id anyway and this is done by redis (same as above).

        :returns: A Set of `id`
        """
        # sort by id
        num, start = self._get_limit_and_offset()
        old_set_key = skey
        new_set_key = "%s#.%s" % (old_set_key, id(self))
        self.db.sort(old_set_key,
                     store=new_set_key,
                     start=start,
                     num=num)
        if old_set_key != self.key:
            Set(old_set_key, db=self.db).set_expire()
        new_list = List(new_set_key, db=self.db)
        new_list.set_expire()
        return new_list

    def _get_limit_and_offset(self):
        """
        Return the limit and offset of the looked up ids.
        """
        if (self._limit is not None and self._offset is None) or \
                (self._limit is None and self._offset is not None):
                    raise "Limit and offset must be specified"

        if self._limit is None:
            return (None, None)
        else:
            return (self._limit, self._offset)

    def _get_item_with_id(self, id):
        """
        Fetch an object and return the instance.
        """
        if self._return_values:
            instance_key = self.model_class.instance_key(id)
            return self.db.hgetall(instance_key)
        else:
            return self.model_class.get_by_id(id)

    def _build_key_from_filter_item(self, index, value):
        """
        Build the keys from the filter so we can fetch the good keys
        with the indices.
        Example:
            Foo.objects.filter(name='bar')
            => 'Foo:name:bar'
        """
        desc = self.model_class._attributes.get(index)
        if desc:
            value = desc.typecast_for_storage(value)
        _k = "%s:%s:%s" % (self.model_class._key, index, value)
        return _k

    def _clone(self):
        """
        This function allows the chaining of lookup calls.
        Example:
            Foo.objects.filter().filter().exclude()...

        :returns: a modelset instance with all the previous filters.
        """
        klass = self.__class__
        c = klass(self.model_class)

        if self._filters:
            c._filters = self._filters
        if self._exclusions:
            c._exclusions = self._exclusions
        if self._zfilters:
            c._zfilters = self._zfilters
        if self._ordering:
            c._ordering = self._ordering
        c._limit = self._limit
        c._offset = self._offset
        c._return_values = self._return_values
        return c
