# -*- coding: utf-8 -*-
"""
Defines the fields that can be added to redisco models.
"""
import time
import sys
from datetime import datetime, date
from dateutil.tz import tzutc, tzlocal
from calendar import timegm
from redisco.containers import List
from .exceptions import FieldValidationError, MissingID

__all__ = ['Attribute', 'CharField', 'ListField', 'DateTimeField',
           'DateField', 'ReferenceField', 'Collection', 'IntegerField',
           'FloatField', 'BooleanField', 'Counter']


class Attribute(object):
    """Defines an attribute of the model.

    The attribute accepts strings and are stored in Redis as
    they are - strings.

    Options
        name      -- alternate name of the attribute. This will be used
                     as the key to use when interacting with Redis.
        indexed   -- Index this attribute. Unindexed attributes cannot
                     be used in queries. Default: True.
        unique    -- validates the uniqueness of the value of the
                     attribute.
        validator -- a callable that can validate the value of the
                     attribute.
        default   -- Initial value of the attribute.

    """
    def __init__(self,
                 name=None,
                 indexed=True,
                 required=False,
                 validator=None,
                 unique=False,
                 default=None):
        self.name = name
        self.indexed = indexed
        self.required = required
        self.validator = validator
        self.default = default
        self.unique = unique
        self.zindexable = False

    def __get__(self, instance, owner):
        try:
            return getattr(instance, '_' + self.name)
        except AttributeError:
            if callable(self.default):
                default = self.default()
            else:
                default = self.default
            self.__set__(instance, default)
            return default

    def __set__(self, instance, value):
        setattr(instance, '_' + self.name, value)

    def typecast_for_read(self, value):
        """Typecasts the value for reading from Redis."""
        # The redis client encodes all unicode data to utf-8 by default.
        return value

    def typecast_for_storage(self, value):
        """Typecasts the value for storing to Redis."""
        try:
            return str(value)
        except UnicodeError:
            return value.decode('utf-8')

    def value_type(self):
        return str

    def acceptable_types(self):
        return str

    def validate(self, instance):
        val = getattr(instance, self.name)
        errors = []
        # type_validation
        if val is not None and not isinstance(val, self.acceptable_types()):
            errors.append((self.name, 'bad type',))
        # validate first standard stuff
        if self.required:
            if val is None or not str(val).strip():
                errors.append((self.name, 'required'))
        # validate uniquness
        if val and self.unique:
            error = self.validate_uniqueness(instance, val)
            if error:
                errors.append(error)
        # validate using validator
        if self.validator:
            r = self.validator(self.name, val)
            if r:
                errors.extend(r)
        if errors:
            raise FieldValidationError(errors)

    def validate_uniqueness(self, instance, val):
        encoded = self.typecast_for_storage(val)
        matches = instance.__class__.objects.filter(**{self.name: encoded})
        if len(matches) > 0:
            try:
                instance_id = instance.id
                no_id = False
            except MissingID:
                no_id = True
            if (len(matches) != 1) or no_id or (matches.first().id != instance.id):
                return (self.name, 'not unique',)


class CharField(Attribute):

    def __init__(self, max_length=255, **kwargs):
        super(CharField, self).__init__(**kwargs)
        self.max_length = max_length

    def validate(self, instance):
        errors = []
        super(CharField, self).validate(instance)

        val = getattr(instance, self.name)

        if val and len(val) > self.max_length:
            errors.append((self.name, 'exceeds max length'))

        if errors:
            raise FieldValidationError(errors)


class BooleanField(Attribute):
    def typecast_for_read(self, value):
        return bool(int(value))

    def typecast_for_storage(self, value):
        if value is None:
            return "0"
        return "1" if value else "0"

    def value_type(self):
        return bool

    def acceptable_types(self):
        return self.value_type()


class IntegerField(Attribute):
    def __init__(self, **kwargs):
        super(IntegerField, self).__init__(**kwargs)
        self.zindexable = True

    def typecast_for_read(self, value):
        return int(value)

    def typecast_for_storage(self, value):
        if value is None:
            return "0"
        return str(value)

    def value_type(self):
        return int

    def acceptable_types(self):
        return int


class FloatField(Attribute):
    def __init__(self, **kwargs):
        super(FloatField, self).__init__(**kwargs)
        self.zindexable = True

    def typecast_for_read(self, value):
        return float(value)

    def typecast_for_storage(self, value):
        if value is None:
            return "0"
        return "%f" % value

    def value_type(self):
        return float

    def acceptable_types(self):
        return self.value_type()


class DateTimeField(Attribute):

    def __init__(self, auto_now=False, auto_now_add=False, **kwargs):
        super(DateTimeField, self).__init__(**kwargs)
        self.auto_now = auto_now
        self.auto_now_add = auto_now_add
        self.zindexable = True

    def typecast_for_read(self, value):
        try:
            # We load as if the timestampe was naive
            dt = datetime.fromtimestamp(float(value), tzutc())
            # And gently override (ie: not convert) to the TZ to UTC
            return dt
        except (TypeError, ValueError):
            return None

    def typecast_for_storage(self, value):
        if not isinstance(value, datetime):
            raise TypeError("%s should be datetime object, and not a %s" % (self.name, type(value)))
        if value is None:
            return None
        # Are we timezone aware ? If no, make it TimeZone Local
        if value.tzinfo is None:
            value = value.replace(tzinfo=tzlocal())
        return "%d.%06d" % (float(timegm(value.utctimetuple())),  value.microsecond)

    def value_type(self):
        return datetime

    def acceptable_types(self):
        return self.value_type()


class DateField(Attribute):

    def __init__(self, auto_now=False, auto_now_add=False, **kwargs):
        super(DateField, self).__init__(**kwargs)
        self.auto_now = auto_now
        self.auto_now_add = auto_now_add
        self.zindexable = True

    def typecast_for_read(self, value):
        try:
            # We load as if it is UTC time
            dt = date.fromtimestamp(float(value))
            # And assign (ie: not convert) the UTC TimeZone
            return dt
        except (TypeError, ValueError):
            return None

    def typecast_for_storage(self, value):
        if not isinstance(value, date):
            raise TypeError("%s should be date object, and not a %s" % (self.name, type(value)))
        if value is None:
            return None
        return "%d" % float(timegm(value.timetuple()))

    def value_type(self):
        return date

    def acceptable_types(self):
        return self.value_type()


class ListField(object):
    """Stores a list of objects.

    target_type -- can be a Python object or a redisco model class.

    If target_type is not a redisco model class, the target_type should
    also a callable that casts the (string) value of a list element into
    target_type. E.g. str, int, float.

    ListField also accepts a string that refers to a redisco model.

    """
    def __init__(self, target_type,
                 name=None,
                 indexed=True,
                 required=False,
                 validator=None,
                 default=None):
        self._target_type = target_type
        self.name = name
        self.indexed = indexed
        self.required = required
        self.validator = validator
        self.default = default or []
        from .base import Model
        self._redisco_model = (isinstance(target_type, str) or
                               issubclass(target_type, Model))

    def __get__(self, instance, owner):
        try:
            return getattr(instance, '_' + self.name)
        except AttributeError:
            if instance.is_new():
                val = self.default
            else:
                key = instance.key(att=self.name)
                val = List(key).members
            if val is not None:
                klass = self.value_type()
                if self._redisco_model:
                    # val = filter(lambda o: o is not None, [klass.objects.get_by_id(v) for v in val])
                    val = [o for o in [klass.objects.get_by_id(v) for v in val] if o is not None]
                else:
                    val = [klass(v) for v in val]
            self.__set__(instance, val)
            return val

    def __set__(self, instance, value):
        setattr(instance, '_' + self.name, value)

    def value_type(self):
        if isinstance(self._target_type, str):
            t = self._target_type
            from .base import get_model_from_key
            self._target_type = get_model_from_key(self._target_type)
            if self._target_type is None:
                raise ValueError("Unknown Redisco class %s" % t)
        return self._target_type

    def validate(self, instance):
        val = getattr(instance, self.name)
        errors = []

        if val:
            if not isinstance(val, list):
                errors.append((self.name, 'bad type'))
            else:
                for item in val:
                    if not isinstance(item, self.value_type()):
                        errors.append((self.name, 'bad type in list'))

        # validate first standard stuff
        if self.required:
            if not val:
                errors.append((self.name, 'required'))
        # validate using validator
        if self.validator:
            r = self.validator(val)
            if r:
                errors.extend(r)
        if errors:
            raise FieldValidationError(errors)


class Collection(object):
    """
    A simple container that will be replaced by the good imports
    and the good filter query.
    """
    def __init__(self, target_type):
        self.target_type = target_type

    def __get__(self, instance, owner):
        if not isinstance(self.target_type, str):
            raise TypeError("A collection only accepts a string representing the Class")

            # __import__ should be something like __import__('mymod.mysubmod', fromlist=['MyClass'])
        klass_path = self.target_type.split(".")
        fromlist = klass_path[-1]
        frompath = ".".join(klass_path[0:-1])
        # if the path is not empty, then it worth importing the class, otherwise, it's
        # a local Class and it's already been imported.
        if frompath:
            mod = __import__(frompath, fromlist=[fromlist])
        else:
            mod = sys.modules[__name__]

        klass = getattr(mod, fromlist)
        return klass.objects.filter(**{instance.__class__.__name__.lower() + '_id': instance.id})

    def __set__(self, instance, value):
        """
        Prevent the argument to be overriden
        """
        raise AttributeError("can't override a collection of object")


class ReferenceField(object):
    def __init__(self,
                 target_type,
                 name=None,
                 attname=None,
                 indexed=True,
                 required=False,
                 related_name=None,
                 default=None,
                 validator=None):
        self._target_type = target_type
        self.name = name
        self.indexed = indexed
        self.required = required
        self._attname = attname
        self._related_name = related_name
        self.validator = validator
        self.default = default

    def __set__(self, instance, value):
        """
        Will set the referenced object unless None is provided
        which will simply remove the reference
        """
        if not isinstance(value, self.value_type()) and \
                value is not None:
            raise TypeError
        # remove the cached value from the instance
        if hasattr(instance, '_' + self.name):
            delattr(instance, '_' + self.name)
        # Remove the attribute_id reference
        setattr(instance, self.attname, None)
        # Set it to the new value if any.
        if value is not None:
            setattr(instance, self.attname, value.id)

    def __get__(self, instance, owner):
        try:
            if not hasattr(instance, '_' + self.name):
                o = self.value_type().objects.get_by_id(getattr(instance, self.attname))
                setattr(instance, '_' + self.name, o)
            return getattr(instance, '_' + self.name)
        except AttributeError:
            setattr(instance, '_' + self.name, self.default)
            return self.default

    def value_type(self):
        return self._target_type

    @property
    def attname(self):
        if self._attname is None:
            self._attname = self.name + '_id'
        return self._attname

    @property
    def related_name(self):
        return self._related_name

    def validate(self, instance):
        val = getattr(instance, self.name)
        errors = []

        if val:
            if not isinstance(val, self.value_type()):
                errors.append((self.name, 'bad type for reference'))

        # validate first standard stuff
        if self.required:
            if not val:
                errors.append((self.name, 'required'))
        # validate using validator
        if self.validator:
            r = self.validator(val)
            if r:
                errors.extend(r)
        if errors:
            raise FieldValidationError(errors)


class Counter(IntegerField):
    def __init__(self, **kwargs):
        super(Counter, self).__init__(**kwargs)
        if 'default' not in kwargs or self.default is None:
            self.default = 0
        self.zindexable = True

    def __set__(self, instance, value):
        raise AttributeError("can't set a counter.")

    def __get__(self, instance, owner):
        if not instance.is_new():
            v = instance.db.hget(instance.key(), self.name)
            if v is None:
                return 0
            return int(v)
        else:
            return 0
