# -*- coding: utf-8 -*-
from __future__ import division

import inspect
from decimal import ROUND_DOWN, Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F
from django.db.models.signals import class_prepared
from django.utils import translation

from moneyed import Currency, Money
from moneyed.localization import _FORMATTER, format_money

from djmoney import forms

from .._compat import (
    BaseExpression,
    Expression,
    deconstructible,
    smart_unicode,
    split_expression,
    string_types,
)


# If django-money-rates is installed we can automatically
# perform operations with different currencies
if 'djmoney_rates' in settings.INSTALLED_APPS:
    try:
        from djmoney_rates.utils import convert_money
        AUTO_CONVERT_MONEY = True
    except ImportError:
        # NOTE. djmoney_rates doesn't support Django 1.9+
        AUTO_CONVERT_MONEY = False
else:
    AUTO_CONVERT_MONEY = False


__all__ = ('MoneyIntegerField', 'NotSupportedLookup')

SUPPORTED_LOOKUPS = ('exact', 'isnull', 'lt', 'gt', 'lte', 'gte')


class NotSupportedLookup(Exception):

    def __init__(self, lookup):
        self.lookup = lookup

    def __str__(self):
        return 'Lookup \'%s\' is not supported for MoneyIntegerField' % self.lookup


@deconstructible
class MoneyPatched(Money):

    # Set to True or False has a higher priority
    # than USE_L10N == True in the django settings file.
    # The variable "self.use_l10n" has three states:
    use_l10n = None

    def __float__(self):
        return float(self.amount)

    def _convert_to_local_currency(self, other):
        """
        Converts other Money instances to the local currency
        """
        if AUTO_CONVERT_MONEY:
            return convert_money(other.amount, other.currency, self.currency)
        else:
            return other

    @classmethod
    def _patch_to_current_class(cls, money):
        """
        Converts object of type MoneyPatched on the object of type Money.
        """
        return cls(money.amount, money.currency)

    def __pos__(self):
        return MoneyPatched._patch_to_current_class(
            super(MoneyPatched, self).__pos__())

    def __neg__(self):
        return MoneyPatched._patch_to_current_class(
            super(MoneyPatched, self).__neg__())

    def __add__(self, other):
        other = self._convert_to_local_currency(other)
        return MoneyPatched._patch_to_current_class(
            super(MoneyPatched, self).__add__(other))

    def __sub__(self, other):
        other = self._convert_to_local_currency(other)
        return MoneyPatched._patch_to_current_class(
            super(MoneyPatched, self).__sub__(other))

    def __mul__(self, other):

        return MoneyPatched._patch_to_current_class(
            super(MoneyPatched, self).__mul__(other))

    def __eq__(self, other):
        if hasattr(other, 'currency'):
            if self.currency == other.currency:
                return self.amount == other.amount
            raise TypeError('Cannot add or subtract two Money ' +
                            'instances with different currencies.')
        return False

    def __truediv__(self, other):
        if isinstance(other, Money):
            return super(MoneyPatched, self).__truediv__(other)
        else:
            return self._patch_to_current_class(
                super(MoneyPatched, self).__truediv__(other))

    def __rmod__(self, other):
        return MoneyPatched._patch_to_current_class(
            super(MoneyPatched, self).__rmod__(other))

    def __get_current_locale(self):
        # get_language can return None starting on django 1.8
        language = translation.get_language() or settings.LANGUAGE_CODE
        locale = translation.to_locale(language)

        if _FORMATTER.get_formatting_definition(locale):
            return locale

        if _FORMATTER.get_formatting_definition('%s_%s' % (locale, locale)):
            return '%s_%s' % (locale, locale)

        return ''

    def __use_l10n(self):
        """
        Return boolean.
        """
        if self.use_l10n is None:
            return settings.USE_L10N
        return self.use_l10n

    def __unicode__(self):
        if self.__use_l10n():
            locale = self.__get_current_locale()
            if locale:
                return format_money(self, locale=locale)

        return format_money(self)

    __str__ = __unicode__

    def __repr__(self):
        return '%s %s' % (self.amount.to_integral_value(ROUND_DOWN), self.currency)


def get_value(obj, expr):
    """
    Extracts value from object or expression.
    """
    if isinstance(expr, F):
        expr = getattr(obj, expr.name)
    elif hasattr(expr, 'value'):
        expr = expr.value
    return expr


def validate_money_expression(obj, expr):
    """
    Money supports different types of expressions, but you can't do following:
      - Add or subtract money with not-money
      - Any exponentiation
      - Any operations with money in different currencies
      - Multiplication, division, modulo with money instances on both sides of expression
    """
    lhs, rhs = split_expression(expr)
    connector = expr.connector
    lhs = get_value(obj, lhs)
    rhs = get_value(obj, rhs)

    if (not isinstance(rhs, Money) and connector in ('+', '-')) or connector == '^':
        raise ValidationError('Invalid F expression for MoneyIntegerField.', code='invalid')
    if isinstance(lhs, Money) and isinstance(rhs, Money):
        if connector in ('*', '/', '^', '%%'):
            raise ValidationError('Invalid F expression for MoneyIntegerField.', code='invalid')
        if lhs.currency != rhs.currency:
            raise ValidationError('You cannot use F() with different currencies.', code='invalid')


def validate_money_value(value):
    """
    Valid value for money are:
      - Single numeric value
      - Money instances
      - Pairs of numeric value and currency. Currency can't be None.
    """
    if isinstance(value, (list, tuple)) and (len(value) != 2 or value[1] is None):
        raise ValidationError(
            'Invalid value for MoneyIntegerField: %(value)s.',
            code='invalid',
            params={'value': value},
        )


def get_currency(value):
    """
    Extracts currency from value.
    """
    if isinstance(value, Money):
        return smart_unicode(value.currency)
    elif isinstance(value, (list, tuple)):
        return value[1]


class MoneyFieldProxy(object):

    def __init__(self, field):
        self.field = field
        # self.currency_field_name = get_currency_field_name(self.field.name)

    def _money_from_obj(self, obj):
        amount = obj.__dict__[self.field.name]
        currency = self.field.model.get_currency()
        if amount is None:
            return None
        return MoneyPatched(amount=amount, currency=currency)

    def __get__(self, obj, type=None):
        if obj is None:
            raise AttributeError('Can only be accessed via an instance.')
        if isinstance(obj.__dict__[self.field.name], BaseExpression):
            return obj.__dict__[self.field.name]
        if not isinstance(obj.__dict__[self.field.name], Money):
            obj.__dict__[self.field.name] = self._money_from_obj(obj)
        return obj.__dict__[self.field.name]

    def __set__(self, obj, value):  # noqa
        # if isinstance(value, BaseExpression):
        #     validate_money_expression(obj, value)
        #     prepare_expression(value)
        # else:
        #     validate_money_value(value)
        #     currency = get_currency(value)
        #     if currency:
        #         self.set_currency(obj, currency)
        value = self.field.to_python(value)
        obj.__dict__[self.field.name] = value

    # def set_currency(self, obj, value):
    #     # we have to determine whether to replace the currency.
    #     # i.e. if we do the following:
    #     # .objects.get_or_create(money_currency='EUR')
    #     # then the currency is already set up, before this code hits
    #     # __set__ of MoneyIntegerField. This is because the currency field
    #     # has less creation counter than money field.
    #     object_currency = obj.__dict__[self.currency_field_name]
    #     default_currency = str(self.field.default_currency)
    #     if object_currency != value and (object_currency == default_currency or value != default_currency):
    #         # in other words, update the currency only if it wasn't
    #         # changed before.
    #         setattr(obj, self.currency_field_name, value)


class MoneyIntegerField(models.IntegerField):
    description = 'A field which stores both the currency and amount of money.'

    def __init__(self, verbose_name=None, name=None,
                 default=None, **kwargs):
        nullable = kwargs.get('null', False)
        if default is None and not nullable:
            # Backwards compatible fix for non-nullable fields
            default = 0

        default = Money(default, )

        if not (nullable and default is None) and not isinstance(default, Money):
            raise Exception(
                'default value must be an instance of Money, is: %s' % str(default))

        super(MoneyIntegerField, self).__init__(verbose_name, name, default=default, **kwargs)

    def to_python(self, value):
        if isinstance(value, Expression):
            return value
        if isinstance(value, Money):
            value = value.amount
        elif isinstance(value, float):
            value = Decimal.from_float(value)
        elif isinstance(value, str):
            value = Decimal(value)
        elif isinstance(value, int):
            value = Decimal(value) / 100
        return value
        #return super(MoneyIntegerField, self).to_python(value)

    def contribute_to_class(self, cls, name):
        if not cls._meta.abstract:
            cls._meta.has_money_field = True
        super(MoneyIntegerField, self).contribute_to_class(cls, name)
        setattr(cls, self.name, MoneyFieldProxy(self))

    def get_db_prep_save(self, value, connection):
        if isinstance(value, Expression):
            return value
        if isinstance(value, Money):
            value = int(value.amount * 100)
        elif isinstance(value, int):
            value = int(Decimal(value) * 100)
        return super(MoneyIntegerField, self).get_db_prep_save(value, connection)

    def get_db_prep_lookup(self, lookup_type, value, connection, prepared=False):
        if lookup_type not in SUPPORTED_LOOKUPS:
            raise NotSupportedLookup(lookup_type)
        value = self.get_db_prep_save(value, connection)
        return super(MoneyIntegerField, self).get_db_prep_lookup(lookup_type, value, connection, prepared)

    def get_default(self):
        if isinstance(self.default, Money):
            frm = inspect.stack()[1]
            mod = inspect.getmodule(frm[0])
            return self.default
        else:
            return super(MoneyIntegerField, self).get_default()

    def formfield(self, **kwargs):
        defaults = {'form_class': forms.MoneyField}
        defaults.update(kwargs)
        defaults['currency_choices'] = self.currency_choices
        return super(MoneyIntegerField, self).formfield(**defaults)

    def value_to_string(self, obj):
        value = self._get_val_from_obj(obj)
        return self.get_prep_value(value)

    # Django 1.7 migration support
    def deconstruct(self):
        name, path, args, kwargs = super(MoneyIntegerField, self).deconstruct()

        if self.default is not None:
            kwargs['default'] = self.default.amount
        return name, path, args, kwargs


def patch_managers(sender, **kwargs):
    """
    Patches models managers
    """
    from .managers import money_manager

    if hasattr(sender._meta, 'has_money_field'):
        sender.copy_managers([
            (_id, name, money_manager(manager))
            for _id, name, manager in sender._meta.concrete_managers
        ])


class_prepared.connect(patch_managers)
