**Update: Version 1.4.0 adds support for Django 1.6 and 1.7
and drops support for Django < 1.4**

Linguo
======

Linguo aims to make model translation easy. It is designed to let you use the
built-in Django features (Query API, Model Forms, Admin, etc) as intended.
Linguo integrates relatively easily with your existing code and performs the
translation retrieval logic transparently (similar to ugettext). It does this
by creating additional columns for each language and using proxy properties to
make it transparent to you.



Features
--------

* Automatically references the correct translation based on the current active
  language.
* Lets you use the Django ORM normally (no need to worry about which fields are
  translatable, linguo figures it out for you).
* Support ModelForms by automatically retrieving/saving values based on the
  active language.
* Supports Django versions 1.4.9 to 1.7.1
* Comprehensive test coverage



Usage
-----

Subclass ``MultilingualModel`` and define the ``translate`` property:
'''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''

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

``MultilingualManager`` allows you to transparently perform filtering and
ordering on translatable fields (more on this below).


Assuming your ``LANGUAGES`` settings looks like this ...
''''''''''''''''''''''''''''''''''''''''''''''''''''''''
::

    LANGUAGES = (
        ('en', ugettext('English')),
        ('fr', ugettext('French')),
    )


Then, you can do this:
''''''''''''''''''''''

**Create a product:** It automatically sets the values for the current active
language.
::

    from django.utils import translation  # import the translation package

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


If you **switch languages**, it will automatically retrieve the corresponding
translated values.
::

    translation.activate('fr')

    product.name
    -> 'French Name'

    product.description
    -> 'French description'


If you **modify translatable fields**, it will automatically assign it to
current active language.
::

    translation.activate('fr')

    product.name = 'New French Name'
    product.save()

    translation.activate('en')

    product.name  # This remains untouched in English
    -> 'English Name'


Non-translated fields will have the same value regardless of the language
we are operating in.
::

    translation.activate('en')
    product.price = 99
    product.save()

    translation.activate('fr')
    product.price
    -> 99


Querying the database
'''''''''''''''''''''

**Filtering and ordering** works as you would expect it to. It will
filter/order in the language you are operating in. You need to have
``MultilingualManager`` on the model in order for this feature to work.
::

    translation.activate('fr')
    Product.objects.filter(name='French Name').order_by('name')


Model Forms for Multilingual models
'''''''''''''''''''''''''''''''''''

Model Forms work transparently in the sense that it automatically saves the form
data to the current active language. However, you **must specify the
``fields``** attribute on the form. Otherwise you will end up with fields for
every language (eg. ``name``, ``name_fr``, etc.) which is probably not what you
want (if you do want this, see section below on 'Admin Model Forms'). ::

    class ProductForm(forms.ModelForm):
        class Meta:
            fields = ('name', 'description', 'price',)
            model = Product

When saving the form, it will automatically save the form data to the fields in
the **current active language**.
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


Admin Model Forms (editing multiple languages at the same time)
'''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''
In the admin, you most probably want to include fields for each language (eg.
``name``, ``name_fr``, etc.). In this case you must subclass
``MultilingualModelForm`` and use it as the admin form.
::

    # Form definition
    from linguo.forms import MultilingualModelForm

    class ProductAdminForm(MultilingualModelForm):
        class Meta:
            model = Product

    # Admin definition
    class ProductAdmin(admin.ModelAdmin):
        form = ProductAdminForm


``MultilingualModelForm`` can be used anytime you want to allow editing multiple
language simultaneously (not just in the admin). Basically, it just **disables
the automatic routing** to the current active language.


Installation
------------

#. Add ``linguo`` to your ``INSTALLED_APPS`` setting.
#. Ensure the ``LANGUAGES`` setting contains all the languages for your site.

It is highly recommended that you use `south <http://south.aeracode.org/>`_ so
that changes to your model can be migrated using automatic schema migrations.
This is because linguo creates new fields on your model that are transparent to
you. See the section below on "Behind The Scenes" for more details.


Adding new languages
''''''''''''''''''''

* Append the new language to the ``LANGUAGES`` setting.
    - You should avoid changing the primary language (ie. the first language in the list). If you do that, you will have to migrate the data in that column.
* If using ``south``, perform an automatic schemamigration:
    ::

        ./manage.py schemamigration <app-name> --auto
* If NOT using ``south``, examine the schema change by running:
    ::

        ./manage.py sql <app-name>

You'll have to manually write the SQL statement to alter the table.


Running the tests
-----------------
::

    ./manage.py test tests --settings=linguo.tests.settings


Troubleshooting
---------------

If you run into this message when generating migrations:
::

    $ ./manage.py schemamigration yourapp --auto
    ? The field 'YourModel.field_text_de' does not have a default specified, yet is NOT NULL.
    ? Since you are adding this field, you MUST specify a default
    ? value to use for existing rows. Would you like to:
    ?  1. Quit now, and add a default to the field in models.py
    ?  2. Specify a one-off value to use for existing columns now
    ? Please select a choice:

It means you have ``blank=False, default=None`` on one or more of your models.


Behind The Scenes (How It Works)
--------------------------------
For each field marked as translatable, ``linguo`` will create additional
database fields for each additional language.

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

On the instantiated model, "name" becomes a ``property`` that appropriately
gets/sets the values for the corresponding field that matches the language we
are working with.

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


License
-------

This app is licensed under the BSD license. See the LICENSE file for details.
Basically, feel free to do what you want with this code, but I'm not liable if
your computer blows up.
