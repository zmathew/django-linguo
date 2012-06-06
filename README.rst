Linguo
======


Overview
--------
Linguo is a Django application that provides the ability to have multilingual models (ie. translatable fields on models). This means that you can have fields on a model with different values for different languages (similar to ugettext, but for models).

It does this by creating additional columns for each language and using accessors to make it transparent to you.

::

    product.name
    -> 'Foo'

    # If you switch languages, you get the translated value for the field:
    translation.activate('fr')

    product.name
    -> 'French Foo'


Features
~~~~~~~~
* Automatically retrieves translated values in the current active language.
* Supports filtering and ordering on translatable fields.
* Can support ModelForms for translatable models that automatically save values to the active language.
* Supports Django versions 1.2 to 1.4
* Comprehensive test coverage


Usage
-----

Subclass ``MultilingualModel`` and specify the fields to be translated in the ``Meta`` class ``translate`` property:
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
::

    from linguo.models import MultilingualModel
    from linguo.managers import MultilingualManager

    class Product(MultilingualModel):
        name = models.CharField(max_length=255, verbose_name=_('name'))
        description = models.TextField(verbose_name=_('description'))
        price = models.FloatField(verbose_name=_('price'))

        objects = MultilingualManager()

        class Meta:
            # name and description are translatable fields
            translate = ('name', 'description')

``MultilingualManager`` allows you to transparently perform filtering and ordering on translatable fields (more on this below).


Assuming your ``LANGUAGES`` settings looks like this ...
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
::

    LANGUAGES = (
        ('en', ugettext('English')),
        ('fr', ugettext('French')),
    )


Then, you can do this:
~~~~~~~~~~~~~~~~~~~~~~

**Create a product:** It automatically sets the values for the current active language.
::

    translation.activate('en')
    product = Product.objects.create(
        name='English Name',
        description='English description',
        price=10
    )


**Translate the fields** on that product.
::

    product.translate(language='fr',
        name='French Name', description='French description'
    )
    product.save()
    # You don't have to specify price, because it is not a translatable field


If we **switch languages**, it will automatically retrieve the corresponding translated values.
::

    translation.activate('fr')

    product.name
    -> 'French Name'

    product.description
    -> 'French description'


Non-translated fields will have the same value regardless of the language we are operating in.
::
    
    translation.activate('en')
    product.price
    -> 10.0

    translation.activate('fr')
    product.price
    -> 10.0


Querying the database
~~~~~~~~~~~~~~~~~~~~~

**Filtering and ordering** works as you would expect it to. It will filter/order in the language you are operating in. You need to use ``MultilingualManager`` on the model in order for this feature to work.
::

    translation.activate('fr')
    Product.objects.filter(name='French Name').order_by('name')


Model Forms for Multilingual models
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Model Forms work transparently in the sense that it automatically saves the form data to the current active language.

But by default, a Model Form for a Multlingual model will contains **all** the fields for **every language** (eg. ``name``, ``name_fr``, etc.). Typically this is not what you want. You just need to specify the ``fields`` attribute so that it doesn't generate separate fields for each language.
::

    class ProductForm(forms.ModelForm):
        class Meta:
            fields = ('name', 'description', 'price',)
            model = Product


The template output and field names for the form will be the same regardless of the language you are operating in.

When saving the form, it will automatically save the form data to the fields in the **current active language**.
::

    translation.activate('fr') # Activate French

    data = {'name': 'French Name', 'description': 'French Description', 'price': 37}
    form = ProductForm(data=data)

    new_product = form.save()

    new_product.name
    -> 'French Name'

    new_product.description
    -> 'French Description'

    new_product.price
    -> 37.0


    # Other languages will not be affected

    translation.activate('en')

    new_product.name
    -> ''

    new_product.description
    -> ''

    new_product.price
    -> 37
     # Of course, non-translatable fields will have a consistent value


Installation
------------

1. You just need to ensure ``linguo`` is in your ``PYTHONPATH`` so that you can import ``MultilingualModel`` and ``MultilingualManager``. You can use ``distutils`` to have it installed into your Python packages folder
(``python setup.py install``).

2`. Ensure the ``LANGUAGES`` setting contains all the languages for your site.


**It is highly recommended that you use south** (`<http://south.aeracode.org/>`__) so that changes to your model can be migrated using automatic schema migrations. This is because linguo creates new fields on your model that are transparent to you. See the section below on "Behind The Scenes" for more details.


Adding new languages
~~~~~~~~~~~~~~~~~~~~

* Append the new language to the ``LANGUAGES`` setting.
    - You should avoid changing the primary language (ie. the first language in the list). If you do that, you will have to migrate the data in that column.

* If using ``south``, perform an automatic schemamigration:
    ::

    ./manage.py schemamigration <app-name> --auto

* If NOT using ``south``, examine the schema change by running:
    ::

    ./manage.py sql <app-name>

    You'll have to manually write the SQL statement to alter the table .


Running the tests
~~~~~~~~~~~~~~~~~
::

    ./manage.py test tests --settings=linguo.tests.settings


Behind The Scenes (How It Works)
--------------------------------
For each field marked as translatable, ``linguo`` will create additional database fields for each additional language.

For example, if you mark the following field as translatable ...
::

    name = models.CharField(_('name'), max_length=255)

    class Meta:
        translate = ('name',)

... and you have three languages (en, fr, de). Your model will have the following db fields:
::

    name = models.CharField(_('name'), max_length=255) # This is for the FIRST language "en"
    name_fr = models.CharField(_('name (French)'), max_length=255) # This is for "fr"
    name_de = models.CharField(_('name (German)'), max_length=255) # This is for "de"

On the instantiated model, "name" becomes a ``property`` that appropriately gets/sets the values
for the corresponding field that matches the language we are working with.

For example, if the current language is "fr" ...
::

    product = Product()
    product.name = "test" # --> sets name_fr

... this will set ``product.name_fr`` (not ``product.name``)


Database filtering works because ``MultingualQueryset`` rewrites the query.

For example, if the current language is "fr", and we run the following query ...
::

    Product.objects.filter(name="test")

... it will be rewritten to be ...
::

    Product.objects.filter(name_fr="test")



Contributors
------------

This app was developed by `Zach Mathew  <https://github.com/zmathew/>`__
at `Trapeze Media <http://trapeze.com>`__.

See the AUTHORS file for full list of contributors.



License
-------

This app is licensed under the BSD license. See the LICENSE file for details.

