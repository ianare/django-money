# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from warnings import warn

from django import VERSION
from django.core import validators
from django.core.exceptions import ValidationError
from django.forms import DecimalField, MultiValueField

from moneyed.classes import Money

from ..settings import CURRENCY_CHOICES
from .widgets import MoneyWidget


__all__ = ('MoneyField',)


class MoneyField(DecimalField):

    def __init__(self, max_value=None, min_value=None,
                 max_digits=None, decimal_places=None, *args, **kwargs):

        # TODO: No idea what currency_widget is supposed to do since it doesn't
        # even receive currency choices as input. Somehow it's supposed to be
        # instantiated from outside. Hard to tell.
        # if currency_widget:
        #     self.widget = currency_widget
        # else:
        #     self.widget = MoneyWidget(amount_widget=amount_field.widget, currency_widget=currency_field.widget)

        # The two fields that this widget comprises
        super(MoneyField, self).__init__(max_value, min_value, max_digits, decimal_places, *args, **kwargs)

    def prepare_value(self, value):
        return value.amount