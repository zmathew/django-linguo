from django.db import models
from django.utils.translation import ugettext_lazy as _

from linguo.managers import MultilingualManager
from linguo.models import MultilingualModel


class FooCategory(MultilingualModel):
    name = models.CharField(max_length=255, verbose_name=_('name'))

    objects = MultilingualManager()

    class Meta:
        ordering = ('name', 'id',)
        translate = ('name',)


class Foo(MultilingualModel):
    price = models.PositiveIntegerField(verbose_name=_('price'))
    name = models.CharField(max_length=255, verbose_name=_('name'))
    categories = models.ManyToManyField(FooCategory, blank=True)

    objects = MultilingualManager()

    class Meta:
        translate = ('name',)
        unique_together = ('name', 'price',)


class FooRel(models.Model):
    myfoo = models.ForeignKey(Foo)
    desc = models.CharField(max_length=255, verbose_name=_('desc'))

    objects = MultilingualManager()


class Moo(Foo):
    q1 = models.PositiveIntegerField()

    class Meta:
        unique_together = ('q1',)


class Bar(Foo):
    quantity = models.PositiveIntegerField(verbose_name=_('quantity'))
    description = models.CharField(max_length=255)

    objects = MultilingualManager()

    class Meta:
        translate = ('description',)


class BarRel(models.Model):
    mybar = models.ForeignKey(Bar)
    desc = models.CharField(max_length=255, verbose_name=_('desc'))

    objects = MultilingualManager()


class AbstractMoe(MultilingualModel):
    name = models.CharField(max_length=255, verbose_name=_('name'))
    price = models.PositiveIntegerField(verbose_name=_('price'))

    class Meta:
        abstract = True
        translate = ('name',)


class Moe(AbstractMoe):
    description = models.CharField(max_length=255,
        verbose_name=_('description'),
    )
    quantity = models.PositiveIntegerField(verbose_name=_('quantity'))

    class Meta:
        translate = ('description',)


class Gem(MultilingualModel):
    gemtype = models.CharField(max_length=255, verbose_name=_('gem type'),
        choices=(('a', 'A Type'), ('b', 'B Type'),)
    )
    somefoo = models.ForeignKey(Foo, null=True, blank=True)

    objects = MultilingualManager()

    class Meta:
        translate = ('gemtype',)


class Hop(MultilingualModel):
    name = models.CharField(max_length=255, verbose_name=_('name'))
    description = models.CharField(max_length=255,
        verbose_name=_('description'),
    )
    price = models.PositiveIntegerField(verbose_name=_('price'))

    objects = MultilingualManager()

    class Meta:
        translate = ('name', 'description',)


class Ord(Foo):
    last_name = models.CharField(max_length=255)

    objects = MultilingualManager()

    class Meta:
        ordering = ('name', 'last_name', 'id',)
        translate = ('last_name',)

    def __unicode__(self):
        return u'%s %s' % (self.name, self.last_name)


class Doc(MultilingualModel):
    pdf = models.FileField(upload_to='files/test/')

    class Meta:
        translate = ('pdf',)


class Lan(MultilingualModel):
    name = models.CharField(max_length=255)
    language = models.CharField(max_length=255, default=None)

    class Meta:
        translate = ('name',)


class DbColumnNameModel(MultilingualModel):
    name = models.CharField(max_length=50, db_column="prefixed_name")

    class Meta:
        translate = ('name',)

"""
class AbstractCar(models.Model):
    name = models.CharField(max_length=255, verbose_name=_('name'), default=None)
    price = models.PositiveIntegerField(verbose_name=_('price'))

    class Meta:
        abstract = True
        unique_together = ('name', 'price',)


class TransCar(MultilingualModel, AbstractCar):
    description = models.CharField(max_length=255,
        verbose_name=_('description'),
    )
    quantity = models.PositiveIntegerField(verbose_name=_('quantity'))

    class Meta:
        translate = ('description',)


class TransCarRel(models.Model):
    mytranscar = models.ForeignKey(TransCar)
    desc = models.CharField(max_length=255, verbose_name=_('desc'))

    objects = MultilingualManager()


class Coo(MultilingualModel, Car):
    q1 = models.PositiveIntegerField()

    class Meta:
        translate = ('price',)
        unique_together = ('q1',)


class TransAbstractCar(MultilingualModel, AbstractCar):
    description = models.CharField(max_length=255,
        verbose_name=_('description'),
    )
    quantity = models.PositiveIntegerField(verbose_name=_('quantity'))

    class Meta:
        translate = ('price', 'description')
"""