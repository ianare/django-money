# -*- coding: utf-8 -*-
"""
Created on May 7, 2011

@author: jake
"""
from decimal import Decimal

from django.db import models

import moneyed

from djmoney.models.fields import MoneyIntegerField

from .._compat import reversion


class ModelWithVanillaMoneyField(models.Model):
    money = MoneyIntegerField(max_digits=10, decimal_places=2)
    second_money = MoneyIntegerField(max_digits=10, decimal_places=2, default_currency='EUR')
    integer = models.IntegerField(default=0)


class ModelWithDefaultAsInt(models.Model):
    money = MoneyIntegerField(default=123, max_digits=10, decimal_places=2, default_currency='GHS')


class ModelWithDefaultAsStringWithCurrency(models.Model):
    money = MoneyIntegerField(default='123 USD', max_digits=10, decimal_places=2)

    class Meta:
        verbose_name = 'model_default_string_currency'


class ModelWithDefaultAsString(models.Model):
    money = MoneyIntegerField(default='123', max_digits=10, decimal_places=2, default_currency='PLN')


class ModelWithDefaultAsFloat(models.Model):
    money = MoneyIntegerField(default=12.05, max_digits=10, decimal_places=2, default_currency='PLN')


class ModelWithDefaultAsDecimal(models.Model):
    money = MoneyIntegerField(default=Decimal('0.01'), max_digits=10, decimal_places=2, default_currency='CHF')


class ModelWithDefaultAsMoney(models.Model):
    money = MoneyIntegerField(default=moneyed.Money('0.01', 'RUB'), max_digits=10, decimal_places=2)


class ModelWithTwoMoneyFields(models.Model):
    amount1 = MoneyIntegerField(max_digits=10, decimal_places=2)
    amount2 = MoneyIntegerField(max_digits=10, decimal_places=3)


class ModelRelatedToModelWithMoney(models.Model):
    moneyModel = models.ForeignKey(ModelWithVanillaMoneyField)


class ModelWithChoicesMoneyField(models.Model):
    money = MoneyIntegerField(
        max_digits=10,
        decimal_places=2,
        currency_choices=[
            (moneyed.USD, 'US Dollars'),
            (moneyed.ZWN, 'Zimbabwian')
        ],
    )


class ModelWithNonMoneyField(models.Model):
    money = MoneyIntegerField(max_digits=10, decimal_places=2, default_currency='USD')
    desc = models.CharField(max_length=10)


class AbstractModel(models.Model):
    money = MoneyIntegerField(max_digits=10, decimal_places=2, default_currency='USD')
    m2m_field = models.ManyToManyField(ModelWithDefaultAsInt)

    class Meta:
        abstract = True


class InheritorModel(AbstractModel):
    second_field = MoneyIntegerField(max_digits=10, decimal_places=2, default_currency='USD')


class RevisionedModel(models.Model):
    amount = MoneyIntegerField(max_digits=10, decimal_places=2, default_currency='USD')

reversion.register(RevisionedModel)


class BaseModel(models.Model):
    money = MoneyIntegerField(max_digits=10, decimal_places=2, default_currency='USD')


class InheritedModel(BaseModel):
    second_field = MoneyIntegerField(max_digits=10, decimal_places=2, default_currency='USD')


class SimpleModel(models.Model):
    money = MoneyIntegerField(max_digits=10, decimal_places=2, default_currency='USD')


class NullMoneyFieldModel(models.Model):
    field = MoneyIntegerField(max_digits=10, decimal_places=2, null=True)


class ProxyModel(SimpleModel):

    class Meta:
        proxy = True
