Django-int-money
================

Rewrite/Fork of Django-money, with some key differences:

- simplified code base
- store money amounts as integers
- store currency information in a table rather than a field

Rationale
---------
Storing money values as integers in the database has several advantages:

- takes up less space in the database
- avoids any issues with rounding or conversion errors compared to floats
  (don't use floats for money values, **ever**!)
- allows using the datbase to perform SUMs, AVGs, etc more efficiently compared to NUMERIC / DECIMAL types
- easier to import or export data to other systems

Storing the currency information at the table level has several advantages:

- takes up less space in the database: not needing a char(3) field for every amount to be stored
  can have a significant impact. Consider a table with 5 money fields containing a million entries,
  that's about a 20 Mb difference.
- from a data modeling perspective, it's best to completely separate different currency types.
  There's no valid reason to ever do calculations on different currencies.

On the other hand, this requires a little more planning ahead when designing
the data model, since adding a currency to the application requires adding a
table.

To alleviate this problem, table inheritence is used to avoid needless repetition.


Requirements
------------
Django versions: 1.7, 1.8, 1.9

Python versions: 3.3, 3.4, 3.5

PyPy versions: PyPy3 2.4

Yeah, that's right: there's no official Python 2 support.
We are now living in the ``__future__`` ;-)

Via ``py-moneyed``, ``django-int-money`` gets:

-  Support for proper Money value handling (using the standard Money
   design pattern)
-  A currency class and definitions for all currencies in circulation
-  Formatting of most currencies with correct currency sign


Installation
------------

Django-int-money currently needs ``py-moneyed`` v0.4 (or later) to work.

You can obtain the source code for ``django-int-money`` from here:

::

    https://github.com/ianare/django-int-money

And the source for ``py-moneyed`` from here:

::

    https://github.com/limist/py-moneyed

Using `pip`:

    pip install py-moneyed django-int-money

Model Usage
-----------

Use as normal model fields

.. code:: python

        from dj_intmoney.models.fields import MoneyIntegerField
        from django.db import models

        class BankAccountUSD(models.Model):

            balance = MoneyIntegerField()

            @staticmethod
            def get_currency():
                return "USD"


        class BankAccountEUR(models.Model):

            balance = MoneyIntegerField()

            @staticmethod
            def get_currency():
                return "EUR"


Support for Django migrations built in.


Adding a new Currency
---------------------

Currencies are listed on moneyed, and this modules use this to provide a
choice list on the admin, also for validation.

To add a new currency available on all the project, you can simple add
this two lines on your ``settings.py`` file

.. code:: python

        import moneyed
        from moneyed.localization import _FORMATTER
        from decimal import ROUND_HALF_EVEN

        BOB = moneyed.add_currency(
            code='BOB',
            numeric='068',
            name='Peso boliviano',
            countries=('BOLIVIA', )
        )

        # Currency Formatter will output 2.000,00 Bs.
        _FORMATTER.add_sign_definition(
            'default',
            BOB,
            prefix=u'Bs. '
        )

        _FORMATTER.add_formatting_definition(
            'es_BO',
            group_size=3, group_separator=".", decimal_point=",",
            positive_sign="",  trailing_positive_sign="",
            negative_sign="-", trailing_negative_sign="",
            rounding_method=ROUND_HALF_EVEN)


Important note on model managers
--------------------------------

Django-money leaves you to use any custom model managers you like for
your models, but it needs to wrap some of the methods to allow searching
for models with money values.

This is done automatically for the "objects" attribute in any model that
uses MoneyIntegerField. However, if you assign managers to some other
attribute, you have to wrap your manager manually, like so:

.. code:: python

        from djmoney.models.managers import money_manager
        class BankAccount(models.Model):

            balance = MoneyIntegerField(max_digits=10, decimal_places=2, default_currency='USD')

            accounts = money_manager(MyCustomManager())

Also, the money\_manager wrapper only wraps the standard QuerySet
methods. If you define custom QuerySet methods, that do not end up using
any of the standard ones (like "get", "filter" and so on), then you also
need to manually decorate those custom methods, like so:

.. code:: python

        from djmoney.models.managers import understand_money

        class MyCustomQuerySet(QuerySet):

           @understand_money
           def my_custom_method(*args,**kwargs):
               # Awesome stuff

Format localization
-------------------

The formatting is turned on if you have set ``USE_L10N = True`` in the
your settings file.

If formatting is disabled in the configuration, then in the templates
will be used default formatting.

In the templates you can use a special tag to format the money.

In the file ``settings.py`` add to ``INSTALLED_APPS`` entry from the
library ``dj_intmoney``:

.. code:: python

        INSTALLED_APPS += ( 'dj_intmoney', )

In the template, add:

::

        {% load dj_intmoney %}
        ...
        {% money_localize money %}

and that is all.

Instructions to the tag ``money_localize``:

::

            {% money_localize <money_object> [ on(default) | off ] [as var_name] %}
            {% money_localize <amount> <currency> [ on(default) | off ] [as var_name] %}

Examples:

The same effect:

::

            {% money_localize money_object %}
            {% money_localize money_object on %}

Assignment to a variable:

::

            {% money_localize money_object on as NEW_MONEY_OBJECT %}

Formatting the number with currency:

::

            {% money_localize '4.5' 'USD' %}

::

    Return::

        MoneyPatched object

Testing
-------

Install the required packages:

::

    git clone https://github.com/ianare/django-int-money

    cd ./django-money/

    pip install -e .[tests] # installation with required packages for testing

Recommended way to run the tests:

.. code:: bash

    tox

Testing the application in the current environment python:

.. code:: bash

    make test

Working with Exchange Rates
---------------------------

To work with exchange rates, check out this repo that builds off of
django-money: https://github.com/evonove/django-money-rates

