# coding=utf-8

import django
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.db import IntegrityError
from django.test import TestCase
from django.utils import translation

from linguo.tests.forms import BarForm, BarFormWithFieldsSpecified, \
    BarFormWithFieldsExcluded, MultilingualBarFormAllFields
from linguo.tests.models import Foo, FooRel, Moo, Bar, BarRel, Moe, Gem, \
    FooCategory, Hop, Ord, Doc, Lan


class LinguoTests(TestCase):

    def setUp(self):
        self.old_lang = translation.get_language()
        translation.activate('en')

    def tearDown(self):
        translation.activate(self.old_lang)


class Tests(LinguoTests):

    def testOrderingOfFieldsWithinModel(self):
        expected = ['id', 'price', 'name', 'name_fr']
        for i in range(len(Foo._meta.fields)):
            self.assertEqual(Foo._meta.fields[i].name, expected[i])

    def testCreation(self):
        translation.activate('en')
        obj = Foo.objects.create(name='Foo', price=10)

        obj = Foo.objects.get(pk=obj.pk)
        self.assertEquals(obj.name, 'Foo')
        self.assertEquals(obj.price, 10)

        translation.activate('fr')
        Foo.objects.create(name='FrenchName', price=15)
        translation.activate('en')

        self.assertEquals(Foo.objects.count(), 2)

    def testTranslate(self):
        """
        We should be able to translate fields on the object.
        """
        obj = Foo.objects.create(name='Foo', price=10)
        obj.translate(name='FooFr', language='fr')
        obj.save()

        # Refresh from db
        obj = Foo.objects.get(id=obj.id)

        self.assertEquals(obj.name, 'Foo')
        self.assertEquals(obj.price, 10)

        translation.activate('fr')
        self.assertEquals(obj.name, 'FooFr')
        self.assertEquals(Foo.objects.count(), 1)

    def testDelayedCreation(self):
        obj = Foo()
        obj.name = 'Foo'
        obj.price = 10

        translation.activate('fr')
        obj.name = 'FooFr'
        obj.save()

        translation.activate('en')
        obj = Foo.objects.get(pk=obj.pk)
        self.assertEquals(obj.name, 'Foo')
        self.assertEquals(obj.price, 10)

        translation.activate('fr')
        self.assertEquals(obj.name, 'FooFr')
        self.assertEquals(obj.price, 10)

    def testMultipleTransFields(self):
        obj = Hop.objects.create(name='hop', description='desc', price=11)
        obj.translate(name='hop_fr', description='desc_fr',
            language='fr')

        self.assertEquals(obj.name, 'hop')
        self.assertEquals(obj.description, 'desc')
        self.assertEquals(obj.price, 11)

        translation.activate('fr')
        self.assertEquals(obj.name, 'hop_fr')
        self.assertEquals(obj.description, 'desc_fr')
        self.assertEquals(obj.price, 11)

    def testMultipleTransFieldsButNotSettingOneDuringCreation(self):
        obj = Hop.objects.create(name='hop', price=11)
        self.assertEquals(obj.name, 'hop')
        self.assertEquals(obj.price, 11)

    def testSwitchingActiveLanguageSetsValuesOnTranslatedFields(self):
        obj = Foo.objects.create(name='Foo', price=10)
        obj.translate(name='FooFr', language='fr')

        translation.activate('fr')
        self.assertEquals(obj.name, 'FooFr')
        obj.name = 'NewFooFr'

        translation.activate('en')
        self.assertEquals(obj.name, 'Foo')

        obj.save()

        # Refresh from db
        obj = Foo.objects.get(id=obj.id)
        self.assertEquals(obj.name, 'Foo')
        translation.activate('fr')
        self.assertEquals(obj.name, 'NewFooFr')

    def testCreateTranslationWithNewValueForNonTransField(self):
        """
        That value of non-trans fields should be the same for all translations.
        """
        obj = Foo.objects.create(name='Foo', price=10)
        obj.translate(name='FooFr', price=20, language='fr')

        translation.activate('fr')
        self.assertEquals(obj.name, 'FooFr')
        self.assertEquals(obj.price, 20)

        translation.activate('en')
        self.assertEquals(obj.price, 20)
        # Ensure no other fields were changed
        self.assertEquals(obj.name, 'Foo')

    def testQuerysetUpdate(self):
        obj = Foo.objects.create(name='Foo', price=10)
        obj.translate(name='FooFr', language='fr')
        obj.save()

        obj2 = Foo.objects.create(name='Foo2', price=13)
        obj2.translate(name='Foo2Fr', language='fr')
        obj2.save()

        qs = Foo.objects.all()
        self.assertEquals(qs.count(), 2)
        qs.update(name='NewFoo')

        # Refresh objects from db
        obj = Foo.objects.get(pk=obj.pk)
        obj2 = Foo.objects.get(pk=obj2.pk)

        self.assertEquals(obj.price, 10)
        self.assertEquals(obj.name, 'NewFoo')
        self.assertEquals(obj2.price, 13)
        self.assertEquals(obj2.name, 'NewFoo')

        translation.activate('fr')
        self.assertEquals(obj.name, 'FooFr')
        self.assertEquals(obj.price, 10)
        self.assertEquals(obj2.name, 'Foo2Fr')
        self.assertEquals(obj2.price, 13)

    def testQuerysetUpdateInOtherLanguageSetsValuesOnOtherLanguageOnly(self):
        obj = Foo.objects.create(name='Foo', price=10)
        obj.translate(name='FooFr', language='fr')
        obj.save()
        obj2 = Foo.objects.create(name='Foo2', price=13)
        obj2.translate(name='Foo2Fr', language='fr')
        obj2.save()

        translation.activate('fr')
        qs = Foo.objects.all()
        self.assertEquals(qs.count(), 2)
        qs.update(name='NewFooFr')

        # Refresh objects from db
        obj = Foo.objects.get(pk=obj.pk)
        obj2 = Foo.objects.get(pk=obj2.pk)

        self.assertEquals(obj.price, 10)
        self.assertEquals(obj.name, 'NewFooFr')
        self.assertEquals(obj2.price, 13)
        self.assertEquals(obj2.name, 'NewFooFr')

        translation.activate('en')
        self.assertEquals(obj.name, 'Foo')
        self.assertEquals(obj.price, 10)
        self.assertEquals(obj2.name, 'Foo2')
        self.assertEquals(obj2.price, 13)

    def testUniqueTogetherUsingTransFields(self):
        Foo.objects.create(name='Foo', price=10)

        try:  # name, price are unique together
            Foo.objects.create(name='Foo', price=10)
        except IntegrityError:
            pass
        else:
            self.fail()

    def testFilteringOnTransField(self):
        obj = Foo.objects.create(name='English Foo', price=10)
        obj.translate(name='French Foo', language='fr')
        obj.save()

        qs = Foo.objects.filter(name="English Foo")
        self.assertEquals(qs.count(), 1)
        self.assertEquals(qs[0], obj)

        qs = Foo.objects.filter(name__startswith="English")
        self.assertEquals(qs.count(), 1)
        self.assertEquals(qs[0], obj)
        qs = Foo.objects.exclude(name__startswith="English")
        self.assertEquals(qs.count(), 0)

        translation.activate('fr')
        qs = Foo.objects.filter(name="French Foo")
        self.assertEquals(qs.count(), 1)
        self.assertEquals(qs[0], obj)

        qs = Foo.objects.filter(name__startswith="French")
        self.assertEquals(qs.count(), 1)
        self.assertEquals(qs[0], obj)
        qs = Foo.objects.exclude(name__startswith="French")
        self.assertEquals(qs.count(), 0)

    def testFilteringUsingExplicitFieldName(self):
        obj = Foo.objects.create(name='English Foo', price=10)
        obj.translate(name='French Foo', language='fr')
        obj.save()

        obj2 = Foo.objects.create(name='Another English Foo', price=20)
        obj2.translate(name='Another French Foo', language='fr')
        obj2.save()

        # we're in english
        qs = Foo.objects.filter(name_en="English Foo")
        self.assertEquals(qs.count(), 1)
        self.assertEquals(qs[0], obj)

        qs = Foo.objects.filter(name_en__startswith="English")
        self.assertEquals(qs.count(), 1)
        self.assertEquals(qs[0], obj)
        qs = Foo.objects.exclude(name_en__startswith="English")
        self.assertEquals(qs.count(), 1)
        self.assertEquals(qs[0], obj2)

        # try using the french field name
        qs = Foo.objects.filter(name_fr="French Foo")
        self.assertEquals(qs.count(), 1)
        self.assertEquals(qs[0], obj)

        qs = Foo.objects.filter(name_fr__startswith="French")
        self.assertEquals(qs.count(), 1)
        self.assertEquals(qs[0], obj)
        qs = Foo.objects.exclude(name_fr__startswith="French")
        self.assertEquals(qs.count(), 1)
        self.assertEquals(qs[0], obj2)

        # now try in french
        translation.activate('fr')
        qs = Foo.objects.filter(name_en="English Foo")
        self.assertEquals(qs.count(), 1)
        self.assertEquals(qs[0], obj)

        qs = Foo.objects.filter(name_en__startswith="English")
        self.assertEquals(qs.count(), 1)
        self.assertEquals(qs[0], obj)
        qs = Foo.objects.exclude(name_en__startswith="English")
        self.assertEquals(qs.count(), 1)
        self.assertEquals(qs[0], obj2)

        # try using the french field name
        qs = Foo.objects.filter(name_fr="French Foo")
        self.assertEquals(qs.count(), 1)
        self.assertEquals(qs[0], obj)

        qs = Foo.objects.filter(name_fr__startswith="French")
        self.assertEquals(qs.count(), 1)
        self.assertEquals(qs[0], obj)
        qs = Foo.objects.exclude(name_fr__startswith="French")
        self.assertEquals(qs.count(), 1)
        self.assertEquals(qs[0], obj2)

    def testOrderingOnTransField(self):
        obj = Foo.objects.create(name='English Foo', price=10)
        obj.translate(name='French Foo', language='fr')
        obj.save()

        obj2 = Foo.objects.create(name='Another English Foo', price=12)
        obj2.translate(name='Another French Foo', language='fr')
        obj2.save()

        qs = Foo.objects.order_by('name')
        self.assertEquals(qs.count(), 2)
        self.assertEquals(qs[0], obj2)
        self.assertEquals(qs[1], obj)

        translation.activate('fr')
        qs = Foo.objects.order_by('name')
        self.assertEquals(qs.count(), 2)
        self.assertEquals(qs[0], obj2)
        self.assertEquals(qs[1], obj)
        self.assertEquals(qs[1].name, 'French Foo')

    def testDefaultOrderingIsTransField(self):
        """
        Test a model that has a trans field in the default ordering.
        """
        f1 = FooCategory.objects.create(name='B2 foo')
        f1.translate(name='B2 foo', language='fr')
        f1.save()

        f2 = FooCategory.objects.create(name='A1 foo')
        f2.translate(name='C3 foo', language='fr')
        f2.save()

        f3 = FooCategory.objects.create(name='C3 foo')
        f3.translate(name='A1 foo', language='fr')
        f3.save()

        qs_en = FooCategory.objects.all()
        self.assertEquals(qs_en[0], f2)
        self.assertEquals(qs_en[1], f1)
        self.assertEquals(qs_en[2], f3)

        translation.activate('fr')
        qs_fr = FooCategory.objects.all()
        self.assertEquals(qs_fr[0], f3)
        self.assertEquals(qs_fr[1], f1)
        self.assertEquals(qs_fr[2], f2)

    def testFilteringOnRelatedObjectsTransField(self):
        # Test filtering on related object's translatable field
        obj = Foo.objects.create(name='English Foo', price=10)
        obj.translate(name='French Foo', language='fr')
        obj.save()

        obj2 = Foo.objects.create(name='Another English Foo', price=12)
        obj2.translate(name='Another French Foo', language='fr')
        obj2.save()

        m1 = FooRel.objects.create(myfoo=obj, desc="description 1")
        m2 = FooRel.objects.create(myfoo=obj2, desc="description 2")

        qs = FooRel.objects.filter(myfoo__name='Another English Foo')
        self.assertEquals(qs.count(), 1)
        self.assertEquals(qs[0], m2)

        qs = FooRel.objects.filter(myfoo__name__startswith='English')
        self.assertEquals(qs.count(), 1)
        self.assertEquals(qs[0], m1)

        translation.activate('fr')

        qs = FooRel.objects.filter(myfoo__name='Another French Foo')
        self.assertEquals(qs.count(), 1)
        self.assertEquals(qs[0], m2)

        qs = FooRel.objects.filter(myfoo__name__startswith='French')
        self.assertEquals(qs.count(), 1)
        self.assertEquals(qs[0], m1)

    def testFilteringOnRelatedObjectsUsingExplicitFieldName(self):
        obj = Foo.objects.create(name='English Foo', price=10)
        obj.translate(name='French Foo', language='fr')
        obj.save()

        obj2 = Foo.objects.create(name='Another English Foo', price=20)
        obj2.translate(name='Another French Foo', language='fr')
        obj2.save()

        m1 = FooRel.objects.create(myfoo=obj, desc="description 1")
        m2 = FooRel.objects.create(myfoo=obj2, desc="description 2")

        # we're in english
        translation.activate('en')
        qs = FooRel.objects.filter(myfoo__name_en='English Foo')
        self.assertEquals(qs.count(), 1)
        self.assertEquals(qs[0], m1)

        qs = FooRel.objects.filter(myfoo__name_en__startswith='Another')
        self.assertEquals(qs.count(), 1)
        self.assertEquals(qs[0], m2)

        # try using the french field name
        qs = FooRel.objects.filter(myfoo__name_fr='French Foo')
        self.assertEquals(qs.count(), 1)
        self.assertEquals(qs[0], m1)

        qs = FooRel.objects.filter(myfoo__name_fr__startswith='Another')
        self.assertEquals(qs.count(), 1)
        self.assertEquals(qs[0], m2)

        # now try in french
        translation.activate('fr')
        qs = FooRel.objects.filter(myfoo__name_en='English Foo')
        self.assertEquals(qs.count(), 1)
        self.assertEquals(qs[0], m1)

        qs = FooRel.objects.filter(myfoo__name_en__startswith='Another')
        self.assertEquals(qs.count(), 1)
        self.assertEquals(qs[0], m2)

        # try using the french field name
        qs = FooRel.objects.filter(myfoo__name_fr='French Foo')
        self.assertEquals(qs.count(), 1)
        self.assertEquals(qs[0], m1)

        qs = FooRel.objects.filter(myfoo__name_fr__startswith='Another')
        self.assertEquals(qs.count(), 1)
        self.assertEquals(qs[0], m2)

    def testModelWithTranslatableFileField(self):
        doc = Doc.objects.create(pdf='something.pdf')
        doc.translate(pdf='something-fr.pdf', language='fr')
        doc.save()

        translation.activate('en')
        self.assertEqual(Doc.objects.get().pdf.url, 'something.pdf')

        translation.activate('fr')
        self.assertEqual(Doc.objects.get().pdf.url, 'something-fr.pdf')

    def testModelWithAFieldCalledLanguageThatIsNotTranslatable(self):
        lan = Lan.objects.create(name='Test en', language='en')
        lan.translate(name='Test fr', language='fr')
        lan.save()

        translation.activate('en')
        self.assertEqual(Lan.objects.get().name, 'Test en')
        self.assertEqual(Lan.objects.get().language, 'en')

        translation.activate('fr')
        self.assertEqual(Lan.objects.get().name, 'Test fr')
        self.assertEqual(Lan.objects.get().language, 'en')


class InheritanceTests(LinguoTests):

    def testOrderingOfFieldsWithinModel(self):
        expected = ['id', 'price', 'name', 'name_fr', 'foo_ptr', 'quantity',
            'description', 'description_fr']
        for i in range(len(Bar._meta.fields)):
            self.assertEqual(Bar._meta.fields[i].name, expected[i])

    def testCreation(self):
        translation.activate('en')
        obj = Bar.objects.create(name='Bar', description='test',
            price=9, quantity=2)

        obj = Bar.objects.get(pk=obj.pk)
        self.assertEquals(obj.name, 'Bar')
        self.assertEquals(obj.description, 'test')
        self.assertEquals(obj.price, 9)
        self.assertEquals(obj.quantity, 2)

        translation.activate('fr')
        Bar.objects.create(name='FrenchBar', description='test in french',
            price=7, quantity=5)
        translation.activate('en')

        self.assertEquals(Bar.objects.count(), 2)

    def testTranslate(self):
        """
        We should be able to create a translation of an object.
        """
        obj = Bar.objects.create(name='Bar', description='test',
            price=9, quantity=2)
        obj.translate(name='BarFr', description='test FR',
            language='fr')
        obj.save()

        # Refresh from db
        obj = Bar.objects.get(pk=obj.pk)

        self.assertEquals(obj.name, 'Bar')
        self.assertEquals(obj.description, 'test')
        self.assertEquals(obj.price, 9)
        self.assertEquals(obj.quantity, 2)

        translation.activate('fr')
        self.assertEquals(obj.name, 'BarFr')
        self.assertEquals(obj.description, 'test FR')
        self.assertEquals(obj.price, 9)
        self.assertEquals(obj.quantity, 2)

    def testDelayedCreation(self):
        obj = Bar()
        obj.name = 'Bar'
        obj.description = 'Some desc'
        obj.price = 9
        obj.quantity = 2

        translation.activate('fr')
        obj.name = 'BarFr'
        obj.description = 'Some desc fr'
        obj.save()

        translation.activate('en')
        obj = Bar.objects.get(pk=obj.pk)
        self.assertEquals(obj.name, 'Bar')
        self.assertEquals(obj.description, 'Some desc')
        self.assertEquals(obj.price, 9)
        self.assertEquals(obj.quantity, 2)

        translation.activate('fr')
        self.assertEquals(obj.name, 'BarFr')
        self.assertEquals(obj.description, 'Some desc fr')
        self.assertEquals(obj.price, 9)
        self.assertEquals(obj.quantity, 2)

    def testSwitchingActiveLanguageSetValuesOnTranslatedFields(self):
        obj = Bar.objects.create(name='Bar', description='test',
            price=9, quantity=2)
        obj.translate(name='BarFr', description='test FR',
            language='fr')

        translation.activate('fr')
        self.assertEquals(obj.name, 'BarFr')
        obj.name = 'NewBarFr'

        translation.activate('en')
        self.assertEquals(obj.name, 'Bar')

        obj.save()

        # Refresh from db
        obj = Foo.objects.get(id=obj.id)
        self.assertEquals(obj.name, 'Bar')
        translation.activate('fr')
        self.assertEquals(obj.name, 'NewBarFr')

    def testCreateTranslationWithNewValueForNonTransField(self):
        """
        That value of non-trans fields should be the same for all translations.
        """

        obj = Bar.objects.create(name='Bar', description='test',
            price=9, quantity=2)
        obj.translate(name='BarFr', description='test FR',
            price=20, quantity=40, language='fr')

        translation.activate('fr')
        self.assertEquals(obj.name, 'BarFr')
        self.assertEquals(obj.description, 'test FR')
        self.assertEquals(obj.price, 20)
        self.assertEquals(obj.quantity, 40)

        translation.activate('en')
        self.assertEquals(obj.price, 20)
        self.assertEquals(obj.quantity, 40)
        # Ensure no other fields were changed
        self.assertEquals(obj.name, 'Bar')
        self.assertEquals(obj.description, 'test')

    def testQuerysetUpdate(self):
        obj = Bar.objects.create(name='Bar', description='test',
            price=9, quantity=2)
        obj.translate(name='BarFr', description='test FR',
            language='fr')
        obj.save()

        obj2 = Bar.objects.create(name='Bar2', description='bar desc',
            price=13, quantity=5)
        obj2.translate(name='Bar2Fr', description='test2 FR',
            language='fr')
        obj2.save()

        qs = Bar.objects.all()
        self.assertEquals(qs.count(), 2)
        qs.update(name='NewBar', quantity=99)

        # Refresh objects from db
        obj = Bar.objects.get(pk=obj.pk)
        obj2 = Bar.objects.get(pk=obj2.pk)

        self.assertEquals(obj.name, 'NewBar')
        self.assertEquals(obj.quantity, 99)
        self.assertEquals(obj2.name, 'NewBar')
        self.assertEquals(obj2.quantity, 99)

        translation.activate('fr')
        self.assertEquals(obj.name, 'BarFr')
        self.assertEquals(obj.quantity, 99)
        self.assertEquals(obj2.name, 'Bar2Fr')
        self.assertEquals(obj2.quantity, 99)

    def testQuerysetUpdateInOtherLanguageSetsValuesOnOtherLanguageOnly(self):
        obj = Bar.objects.create(name='Bar', description='test',
            price=9, quantity=2)
        obj.translate(name='BarFr', description='test FR',
            language='fr')
        obj.save()

        obj2 = Bar.objects.create(name='Bar2', description='bar desc',
            price=13, quantity=5)
        obj2.translate(name='Bar2Fr', description='test2 FR',
            language='fr')
        obj2.save()

        translation.activate('fr')
        qs = Bar.objects.all()
        self.assertEquals(qs.count(), 2)
        qs.update(name='NewBarFr', quantity=99)

        # Refresh objects from db
        obj = Bar.objects.get(pk=obj.pk)
        obj2 = Bar.objects.get(pk=obj2.pk)

        self.assertEquals(obj.name, 'NewBarFr')
        self.assertEquals(obj.quantity, 99)
        self.assertEquals(obj2.name, 'NewBarFr')
        self.assertEquals(obj2.quantity, 99)

        translation.activate('en')
        self.assertEquals(obj.name, 'Bar')
        self.assertEquals(obj.quantity, 99)
        self.assertEquals(obj2.name, 'Bar2')
        self.assertEquals(obj2.quantity, 99)

    def testUniqueTogether(self):
        """
        Ensure that the unique_together definitions in child is working.
        """
        Moo.objects.create(name='Moo', price=3, q1=4)

        try:
            Moo.objects.create(name='Moo2', price=15, q1=4)
        except IntegrityError:
            pass
        else:
            self.fail()

    def testUniqueTogetherInParent(self):
        """
        Ensure that the unique_together definitions in parent is working.
        """
        Moo.objects.create(name='Moo', price=3, q1=4)
        try:
            Moo.objects.create(name='Moo', price=3, q1=88)
        except IntegrityError:
            pass
        else:
            self.fail()

    def testFilteringOnTransField(self):
        obj = Bar.objects.create(name='English Bar', description='English test',
            price=9, quantity=2)
        obj.translate(name='French Bar', description='French test',
            language='fr')
        obj.save()

        qs = Bar.objects.filter(name="English Bar")
        self.assertEquals(qs.count(), 1)
        self.assertEquals(qs[0], obj)

        qs = Bar.objects.filter(name__startswith="English")
        self.assertEquals(qs.count(), 1)
        self.assertEquals(qs[0], obj)
        qs = Bar.objects.exclude(name__startswith="English")
        self.assertEquals(qs.count(), 0)

        translation.activate('fr')
        qs = Bar.objects.filter(name="French Bar")
        self.assertEquals(qs.count(), 1)
        self.assertEquals(qs[0], obj)

        qs = Bar.objects.filter(name__startswith="French")
        self.assertEquals(qs.count(), 1)
        self.assertEquals(qs[0], obj)
        qs = Bar.objects.exclude(name__startswith="French")
        self.assertEquals(qs.count(), 0)

    def testOrderingOnTransField(self):
        obj = Bar.objects.create(name='English Bar', description='English test',
            price=9, quantity=2)
        obj.translate(name='French Bar', description='French test',
            language='fr')
        obj.save()

        obj2 = Bar.objects.create(name='Another English Bar', description='another english test',
            price=22, quantity=25)
        obj2.translate(name='Another French Bar', description='another french test',
            language='fr')
        obj2.save()

        qs = Bar.objects.order_by('name')
        self.assertEquals(qs.count(), 2)
        self.assertEquals(qs[0], obj2)
        self.assertEquals(qs[1], obj)

        translation.activate('fr')

        qs = Bar.objects.order_by('name')
        self.assertEquals(qs.count(), 2)
        self.assertEquals(qs[0], obj2)
        self.assertEquals(qs[1], obj)
        self.assertEquals(qs[1].name, 'French Bar')

    def testDefaultOrderingIsTransAndInheritedTransField(self):
        """
        Test a model that has an inherited trans field in the default ordering.
        """
        o1 = Ord.objects.create(name='B2 test', price=1)
        o1.translate(name='B2 test F', price=1, language='fr')
        o1.save()

        o2 = Ord.objects.create(name='A1 test', price=2, last_name='Appleseed')
        o2.translate(name='C3 test F', price=2, last_name='Charlie', language='fr')
        o2.save()

        o2b = Ord.objects.create(name='A1 test', price=3, last_name='Zoltan')
        o2b.translate(name='C3 test F', price=3, last_name='Bobby', language='fr')
        o2b.save()

        o3 = Ord.objects.create(name='C3 foo', price=4)
        o3.translate(name='A1 test F', price=4, language='fr')
        o3.save()

        qs_en = Ord.objects.all()
        self.assertEquals(qs_en[0], o2)
        self.assertEquals(qs_en[1], o2b)
        self.assertEquals(qs_en[2], o1)
        self.assertEquals(qs_en[3], o3)

        translation.activate('fr')
        qs_fr = Ord.objects.all()
        self.assertEquals(qs_fr[0], o3)
        self.assertEquals(qs_fr[1], o1)
        self.assertEquals(qs_fr[2], o2b)
        self.assertEquals(qs_fr[3], o2)

    def testFilteringOnRelatedObjectsTransField(self):
        obj = Bar.objects.create(name='English Bar', description='English test',
            price=9, quantity=2)
        obj.translate(name='French Bar', description='French test',
            language='fr')
        obj.save()

        obj2 = Bar.objects.create(name='Another English Bar', description='another english test',
            price=22, quantity=25)
        obj2.translate(name='Another French Bar', description='another french test',
            language='fr')
        obj2.save()

        m1 = BarRel.objects.create(mybar=obj, desc="description 1")
        m2 = BarRel.objects.create(mybar=obj2, desc="description 2")

        qs = BarRel.objects.filter(mybar__name='Another English Bar')
        self.assertEquals(qs.count(), 1)
        self.assertEquals(qs[0], m2)

        qs = BarRel.objects.filter(mybar__name__startswith='English')
        self.assertEquals(qs.count(), 1)
        self.assertEquals(qs[0], m1)

        translation.activate('fr')

        qs = BarRel.objects.filter(mybar__name='Another French Bar')
        self.assertEquals(qs.count(), 1)
        self.assertEquals(qs[0], m2)

        qs = BarRel.objects.filter(mybar__name__startswith='French')
        self.assertEquals(qs.count(), 1)
        self.assertEquals(qs[0], m1)

    def testExtendingAbstract(self):
        """
        Test a model that extends an abstract model an defines a new
        non trans field.
        """
        obj = Moe.objects.create(name='test', description='test description',
            price=5, quantity=3
        )
        obj.translate(language='fr',
            name='test-fr', description='test description fr'
        )
        obj.save()

        obj = Moe.objects.get(pk=obj.pk)
        self.assertEquals(obj.name, 'test')
        self.assertEquals(obj.description, 'test description')
        self.assertEquals(obj.price, 5)
        self.assertEquals(obj.quantity, 3)

        Moe.objects.create(name='Other', description='test other', price=15, quantity=13)

        self.assertEquals(Moe.objects.count(), 2)

        translation.activate('fr')
        self.assertEquals(obj.name, 'test-fr')
        self.assertEquals(obj.description, 'test description fr')
        self.assertEquals(obj.price, 5)
        self.assertEquals(obj.quantity, 3)

    def testExtendingAbstractKeepsNonTransFields(self):
        obj = Moe.objects.create(
           name='test', description='test description', price=5, quantity=3
        )
        obj.translate(language='fr',
            name='test-fr', description='test description fr',
            price=13  # Changing price
        )
        obj.quantity = 99  # Changing quantity
        obj.save()

        obj = Moe.objects.get(pk=obj.pk)
        self.assertEquals(obj.price, 13)
        self.assertEquals(obj.quantity, 99)

        obj.price = 66
        obj.quantity = 77
        obj.save()

        translation.activate('fr')
        self.assertEquals(obj.price, 66)
        self.assertEquals(obj.quantity, 77)


class ForeignKeyTests(LinguoTests):

    def testModelWithFK(self):
        """
        A trans model has a foreign key to another trans model.
        The foreign key is not language specific.
        """
        obj = Foo.objects.create(name='English Foo', price=10)
        obj.translate(name='French Foo', language='fr')
        obj.save()

        obj2 = Foo.objects.create(name='Another English Foo', price=12)
        obj2.translate(name='Another French Foo', language='fr')
        obj2.save()

        rel1 = Gem.objects.create(somefoo=obj, gemtype='a')
        rel1.translate(gemtype='b', language='fr')
        rel1.save()

        rel2 = Gem.objects.create(somefoo=obj2, gemtype='a')

        self.assertEquals(rel1.somefoo, obj)
        # Ensure the reverse manager returns expected results
        self.assertEquals(obj.gem_set.count(), 1)
        self.assertEquals(obj.gem_set.all()[0], rel1)

        translation.activate('fr')
        self.assertEquals(rel1.somefoo, obj)
        self.assertEquals(obj.gem_set.count(), 1)
        self.assertEquals(obj.gem_set.all()[0], rel1)

        translation.activate('en')
        self.assertEquals(rel2.somefoo, obj2)
        self.assertEquals(obj2.gem_set.count(), 1)
        self.assertEquals(obj2.gem_set.all()[0], rel2)

    def testChangeFKWithInTranslatedLanguage(self):
        obj = Foo.objects.create(name='English Foo', price=10)

        obj2 = Foo.objects.create(name='Another English Foo', price=12)
        obj2.translate(name='Another French Foo', language='fr')
        obj2.save()

        rel1 = Gem.objects.create(somefoo=obj, gemtype='a')
        rel1.translate(gemtype='b', language='fr')
        rel1.save()

        translation.activate('fr')
        rel1.somefoo = obj2
        rel1.save()

        translation.activate('en')
        rel2 = Gem.objects.create(somefoo=obj2, gemtype='a')
        rel1 = Gem.objects.get(pk=rel1.pk)
        self.assertEquals(rel1.somefoo, obj2)
        self.assertEquals(rel2.somefoo, obj2)

        self.assertEquals(obj2.gem_set.count(), 2)
        self.assertEquals(obj2.gem_set.order_by('id')[0], rel1)
        self.assertEquals(obj2.gem_set.order_by('id')[1], rel2)

        translation.activate('fr')
        self.assertEquals(obj2.gem_set.count(), 2)
        self.assertEquals(obj2.gem_set.order_by('id')[0], rel1)
        self.assertEquals(obj2.gem_set.order_by('id')[1], rel2)

        self.assertEquals(obj.gem_set.count(), 0)

    def testRemoveFk(self):
        """
        Test for consistency when you remove a foreign key connection.
        """
        obj = Foo.objects.create(name='English Foo', price=10)
        obj.translate(name='French Foo', language='fr')

        obj2 = Foo.objects.create(name='Another English Foo', price=12)

        rel1 = Gem.objects.create(somefoo=obj, gemtype='a')
        rel1.translate(gemtype='b', language='fr')
        rel1.somefoo = None
        rel1.save()

        rel2 = Gem.objects.create(somefoo=obj2, gemtype='a')

        translation.activate('fr')
        self.assertEquals(rel1.somefoo, None)
        self.assertEquals(rel2.somefoo, obj2)
        self.assertEquals(obj.gem_set.count(), 0)
        self.assertEquals(obj2.gem_set.count(), 1)

    def testFKReverseCreation(self):
        """
        Test creating an object using the reverse manager.
        """
        Foo.objects.create(name='English Foo', price=10)
        obj2 = Foo.objects.create(name='Another English Foo', price=12)
        obj2.translate(name='Another French Foo', language='fr')
        obj2.save()

        rel1 = obj2.gem_set.create(gemtype='a')

        obj2 = Foo.objects.get(pk=obj2.pk)

        self.assertEquals(obj2.gem_set.count(), 1)
        self.assertEquals(obj2.gem_set.order_by('id')[0], rel1)

        translation.activate('fr')
        self.assertEquals(obj2.gem_set.count(), 1)
        self.assertEquals(obj2.gem_set.order_by('id')[0], rel1)

    def testFKReverseAddition(self):
        """
        Test adding an object using the reverse manager.
        """
        obj = Foo.objects.create(name='English Foo', price=10)
        obj2 = Foo.objects.create(name='Another English Foo', price=12)
        obj2.translate(name='Another French Foo', language='fr')
        obj2.save()

        rel1 = Gem.objects.create(somefoo=obj, gemtype='a')
        obj2.gem_set.add(rel1)
        rel1 = Gem.objects.get(pk=rel1.pk)
        self.assertEquals(rel1.somefoo, obj2)
        self.assertEquals(obj2.gem_set.count(), 1)
        self.assertEquals(obj2.gem_set.all()[0], rel1)

    def testFKReverseRemoval(self):
        """
        Test removing an object using the reverse manager.
        """
        obj = Foo.objects.create(name='English Foo', price=10)
        obj2 = Foo.objects.create(name='Another English Foo', price=12)
        obj2.translate(name='Another French Foo', language='fr')
        obj2.save()

        rel1 = Gem.objects.create(somefoo=obj, gemtype='a')
        rel1.translate(gemtype='b', language='fr')

        obj2.gem_set.add(rel1)

        rel1 = Gem.objects.get(pk=rel1.pk)
        self.assertEquals(rel1.somefoo, obj2)

        self.assertEquals(obj.gem_set.count(), 0)
        self.assertEquals(obj2.gem_set.count(), 1)
        self.assertEquals(obj2.gem_set.all()[0], rel1)

        translation.activate('fr')
        self.assertEquals(rel1.somefoo, obj2)
        self.assertEquals(obj.gem_set.count(), 0)
        self.assertEquals(obj2.gem_set.count(), 1)
        self.assertEquals(obj2.gem_set.all()[0], rel1)

        translation.activate('en')
        obj2.gem_set.remove(rel1)
        rel1 = Gem.objects.get(pk=rel1.pk)
        self.assertEquals(rel1.somefoo, None)
        self.assertEquals(obj2.gem_set.count(), 0)

        translation.activate('fr')
        self.assertEquals(rel1.somefoo, None)
        self.assertEquals(obj2.gem_set.count(), 0)

    def testSetFKInTranslatedLanguage(self):
        obj = Foo.objects.create(name='English Foo', price=10)
        obj.translate(name='French Foo', language='fr')
        obj.save()

        translation.activate('fr')
        rel1 = Gem.objects.create(gemtype='a', somefoo=obj)

        translation.activate('en')
        self.assertEquals(obj.gem_set.count(), 1)
        self.assertEquals(obj.gem_set.all()[0], rel1)

    def testFKReverseAdditionOnTranslatedLanguage(self):
        obj = Foo.objects.create(name='English Foo', price=10)
        obj.translate(name='French Foo', language='fr')
        obj.save()

        rel1 = Gem.objects.create(gemtype='a')

        translation.activate('fr')
        obj.gem_set.add(rel1)
        rel1 = Gem.objects.get(pk=rel1.pk)

        self.assertEquals(rel1.somefoo, obj)

        self.assertEquals(obj.gem_set.count(), 1)
        self.assertEquals(obj.gem_set.all()[0], rel1)


class ManyToManyTests(LinguoTests):

    def testCreateM2M(self):
        obj = Foo.objects.create(name='English Foo', price=10)
        cat = obj.categories.create(name='C1')
        cat2 = FooCategory.objects.create(name='C2')

        self.assertEquals(obj.categories.count(), 1)
        self.assertEquals(obj.categories.all()[0], cat)

        obj.translate(language='fr', name='French Foo')
        obj.save()

        translation.activate('fr')
        self.assertEquals(obj.categories.count(), 1)
        self.assertEquals(obj.categories.all()[0], cat)

        # Reverse lookup should return only foo
        self.assertEquals(cat.foo_set.count(), 1)
        self.assertEquals(cat.foo_set.all()[0], obj)

        translation.activate('en')
        cat.translate(language='fr', name='C1 fr')
        cat.save()

        translation.activate('fr')
        self.assertEquals(cat.foo_set.all()[0], obj)

        translation.activate('en')
        obj2 = Foo.objects.create(name='Another Foo', price=5)
        self.assertEquals(obj2.categories.count(), 0)

        self.assertEquals(cat.foo_set.count(), 1)
        self.assertEquals(cat.foo_set.all()[0], obj)
        self.assertEquals(cat2.foo_set.count(), 0)

    def testRemovingM2M(self):
        obj = Foo.objects.create(name='English Foo', price=10)
        obj.translate(language='fr', name='French Foo')
        obj.save()

        obj2 = Foo.objects.create(name='Another English Foo', price=12)

        cat = obj.categories.create(name='C1')
        cat2 = obj2.categories.create(name='C2')
        translation.activate('fr')
        cat3 = obj.categories.create(name='C3')
        translation.activate('en')

        self.assertEquals(obj.categories.count(), 2)

        translation.activate('fr')
        self.assertEquals(obj.categories.count(), 2)
        obj.categories.remove(cat)
        self.assertEquals(obj.categories.count(), 1)
        self.assertEquals(obj.categories.all()[0], cat3)

        translation.activate('en')
        self.assertEquals(obj.categories.count(), 1)
        self.assertEquals(obj.categories.all()[0], cat3)

        self.assertEquals(obj2.categories.count(), 1)
        self.assertEquals(obj2.categories.all()[0], cat2)
        self.assertEquals(cat2.foo_set.all()[0], obj2)

    def testClearingM2M(self):
        obj = Foo.objects.create(name='English Foo', price=10)
        obj.translate(language='fr', name='French Foo')
        obj.save()
        obj2 = Foo.objects.create(name='Another English Foo', price=12)
        obj2.save()

        obj.categories.create(name='C1')
        cat2 = obj2.categories.create(name='C2')

        translation.activate('fr')
        obj.categories.create(name='C3')

        self.assertEquals(obj.categories.count(), 2)

        translation.activate('fr')
        self.assertEquals(obj.categories.count(), 2)
        obj.categories.clear()
        self.assertEquals(obj.categories.count(), 0)

        translation.activate('en')
        self.assertEquals(obj.categories.count(), 0)

        self.assertEquals(obj2.categories.count(), 1)
        self.assertEquals(obj2.categories.all()[0], cat2)
        self.assertEquals(cat2.foo_set.all()[0], obj2)


class FormTests(LinguoTests):

    def testModelForm(self):
        form = BarForm()
        self.assertEqual(len(form.fields), 7)
        self.assertTrue('name' in form.fields)
        self.assertTrue('name_fr' in form.fields)
        self.assertTrue('price' in form.fields)
        self.assertTrue('categories' in form.fields)
        self.assertTrue('quantity' in form.fields)
        self.assertTrue('description' in form.fields)
        self.assertTrue('description_fr' in form.fields)

        data = {'name': 'Test', 'name_fr': 'French Test', 'price': 13,
            'quantity': 3, 'description': 'This is a test', 'description_fr': 'French Description',
        }
        form = BarForm(data=data)
        self.assertEqual(unicode(form['name'].label), u'Name')
        self.assertEqual(unicode(form['name_fr'].label), u'Name (French)')
        self.assertEqual(unicode(form['description'].label), u'Description')
        self.assertEqual(unicode(form['description_fr'].label), u'Description (French)')
        bar = form.save()
        self.assertEqual(bar.name, 'Test')
        self.assertEqual(bar.price, 13)
        self.assertEqual(bar.quantity, 3)
        self.assertEqual(bar.description, 'This is a test')

        translation.activate('fr')
        self.assertEqual(bar.name, 'French Test')
        self.assertEqual(bar.price, 13)
        self.assertEqual(bar.quantity, 3)
        self.assertEqual(bar.description, 'French Description')

        translation.activate('en')
        # Create the form with an instance
        data2 = {'name': 'Changed', 'name_fr': 'Changed French', 'price': 43,
            'quantity': 22, 'description': 'Changed description',
            'description_fr': 'Changed description French'
        }
        form = BarForm(instance=bar, data=data2)
        bar = form.save()
        self.assertEqual(bar.name, 'Changed')
        self.assertEqual(bar.price, 43)
        self.assertEqual(bar.quantity, 22)
        self.assertEqual(bar.description, 'Changed description')

        translation.activate('fr')
        self.assertEqual(bar.name, 'Changed French')
        self.assertEqual(bar.price, 43)
        self.assertEqual(bar.quantity, 22)
        self.assertEqual(bar.description, 'Changed description French')

    def testModelFormInSecondaryLanguage(self):
        translation.activate('fr')
        form = BarForm()
        # When we are in French name and description point to French fields (not the English)
        # name_fr and description_fr are actually redundant
        # But we want name_fr and description_fr to take precedence over name and description
        data = {'name': 'Test', 'name_fr': 'French Test', 'price': 13,
            'quantity': 3, 'description': 'This is a test', 'description_fr': 'French Description',
        }
        form = BarForm(data=data)

        # These translations are not meant to be correct it is solely for the purpose of testing
        self.assertEqual(unicode(form['name'].label), u'Neom')
        self.assertEqual(unicode(form['name_fr'].label), u'Neom (Français)')
        self.assertEqual(unicode(form['description'].label), u'Description')  # This does not get translated because Django generates the verbose_name as a string
        self.assertEqual(unicode(form['description_fr'].label), u'Déscriptione (Français)')
        bar = form.save()

        translation.activate('en')
        self.assertEqual(bar.name, '')
        self.assertEqual(bar.price, 13)
        self.assertEqual(bar.quantity, 3)
        self.assertEqual(bar.description, '')

        translation.activate('fr')
        self.assertEqual(bar.name, 'French Test')
        self.assertEqual(bar.price, 13)
        self.assertEqual(bar.quantity, 3)
        self.assertEqual(bar.description, 'French Description')

    def testModelFormWithFieldsSpecified(self):
        form = BarFormWithFieldsSpecified()
        self.assertEqual(len(form.fields), 4)
        self.assertTrue('name' in form.fields)
        self.assertTrue('price' in form.fields)
        self.assertTrue('quantity' in form.fields)
        self.assertTrue('description' in form.fields)

        data = {'name': 'Test', 'price': 13,
            'quantity': 3, 'description': 'This is a test',
        }
        form = BarFormWithFieldsSpecified(data=data)
        bar = form.save()
        self.assertEqual(bar.name, 'Test')
        self.assertEqual(bar.price, 13)
        self.assertEqual(bar.quantity, 3)
        self.assertEqual(bar.description, 'This is a test')

        translation.activate('fr')
        self.assertEqual(bar.name, '')
        self.assertEqual(bar.price, 13)
        self.assertEqual(bar.quantity, 3)
        self.assertEqual(bar.description, '')

        translation.activate('en')
        # Create the form with an instance
        data2 = {'name': 'Changed', 'price': 43,
            'quantity': 22, 'description': 'Changed description',
        }
        form = BarFormWithFieldsSpecified(instance=bar, data=data2)
        bar = form.save()
        self.assertEqual(bar.name, 'Changed')
        self.assertEqual(bar.price, 43)
        self.assertEqual(bar.quantity, 22)
        self.assertEqual(bar.description, 'Changed description')

        translation.activate('fr')
        self.assertEqual(bar.name, '')
        self.assertEqual(bar.price, 43)
        self.assertEqual(bar.quantity, 22)
        self.assertEqual(bar.description, '')

    def testModelFormWithFieldsSpecifiedInSecondaryLanguage(self):
        translation.activate('fr')
        form = BarFormWithFieldsSpecified()
        self.assertEqual(len(form.fields), 4)
        self.assertTrue('name' in form.fields)
        self.assertTrue('price' in form.fields)
        self.assertTrue('quantity' in form.fields)
        self.assertTrue('description' in form.fields)

        data = {'name': 'Test French', 'price': 13,
            'quantity': 3, 'description': 'This is a French test',
        }
        form = BarFormWithFieldsSpecified(data=data)
        bar = form.save()
        self.assertEqual(bar.name, 'Test French')
        self.assertEqual(bar.price, 13)
        self.assertEqual(bar.quantity, 3)
        self.assertEqual(bar.description, 'This is a French test')

        translation.activate('en')
        self.assertEqual(bar.name, '')
        self.assertEqual(bar.price, 13)
        self.assertEqual(bar.quantity, 3)
        self.assertEqual(bar.description, '')

        translation.activate('fr')
        # Create the form with an instance
        data2 = {'name': 'Changed', 'price': 43,
            'quantity': 22, 'description': 'Changed description',
        }
        form = BarFormWithFieldsSpecified(instance=bar, data=data2)
        bar = form.save()
        self.assertEqual(bar.name, 'Changed')
        self.assertEqual(bar.price, 43)
        self.assertEqual(bar.quantity, 22)
        self.assertEqual(bar.description, 'Changed description')

        translation.activate('en')
        self.assertEqual(bar.name, '')
        self.assertEqual(bar.price, 43)
        self.assertEqual(bar.quantity, 22)
        self.assertEqual(bar.description, '')


if django.VERSION[:3] >= (1, 1, 2):  # The AdminTests only pass with django >= 1.1.2 (but compatibility is django >= 1.0.3)
    class AdminTests(LinguoTests):

        def setUp(self):
            super(AdminTests, self).setUp()

            self.user = User.objects.create_user(username='test', password='test',
                email='test@test.com'
            )
            self.user.is_staff = True
            self.user.is_superuser = True
            self.user.save()
            self.client.login(username='test', password='test')

        def testAdminChangelistFeatures(self):
            # Create some Bar objects
            b1 = Bar.objects.create(name="apple", price=2, description="hello world", quantity=1)
            b1.translate(name="pomme", description="allo monde", language="fr")
            b1.save()

            b2 = Bar.objects.create(name="computer", price=3, description="oh my god", quantity=3)
            b2.translate(name="ordinator", description="oh mon dieu", language="fr")
            b2.save()

            url = reverse('admin:tests_bar_changelist')
            response = self.client.get(url)

            # Check that the correct language is being displayed
            self.assertContains(response, 'hello world')
            self.assertContains(response, 'oh my god')

            # Check the list filters
            self.assertContains(response, '?name=apple')
            self.assertContains(response, '?name=computer')

            # Check that the filtering works
            response = self.client.get(url, {'name': 'computer'})
            self.assertContains(response, 'oh my god')
            self.assertNotContains(response, 'hello world')

            # Check the searching
            response = self.client.get(url, {'q': 'world'})
            self.assertContains(response, 'hello world')
            self.assertNotContains(response, 'oh my god')

        def testAdminAddSubmission(self):
            url = reverse('admin:tests_bar_add')
            response = self.client.post(url, data={
                'name': 'Bar',
                'name_fr': 'French Bar',
                'price': 12,
                'quantity': 5,
                'description': 'English description.',
                'description_fr': 'French description.'
            })
            self.assertEqual(response.status_code, 302)

        def testAdminChangeSubmission(self):
            obj = Bar(name='Bar', price=12, quantity=5, description='Hello')
            obj.translate(language='fr', name='French Bar', description='French Hello')
            obj.save()

            url = reverse('admin:tests_bar_change', args=[obj.id])
            response = self.client.post(url, data={
                'name': 'Bar2',
                'name_fr': 'French Bar2',
                'price': 222,
                'quantity': 55,
                'description': 'Hello2',
                'description_fr': 'French Hello2'
            })
            self.assertEqual(response.status_code, 302)


class TestMultilingualForm(LinguoTests):
    def testCreatesModelInstanceWithAllFieldValues(self):
        translation.activate('fr')
        form = MultilingualBarFormAllFields(data={
            'name': 'Bar',
            'name_fr': 'French Bar',
            'price': 12,
            'quantity': 5,
            'description': 'English description.',
            'description_fr': 'French description.'
        })

        instance = form.save()

        translation.activate('en')
        instance = Bar.objects.get(id=instance.id)  # Refresh from db

        self.assertEqual(instance.name, 'Bar')
        self.assertEqual(instance.price, 12)
        self.assertEqual(instance.quantity, 5)
        self.assertEqual(instance.description, 'English description.')

        translation.activate('fr')
        self.assertEqual(instance.name, 'French Bar')
        self.assertEqual(instance.price, 12)
        self.assertEqual(instance.quantity, 5)
        self.assertEqual(instance.description, 'French description.')

    def testUpdatesModelInstanceWithAllFieldValues(self):
        instance = Bar(name='Bar', price=12, quantity=5, description='Hello')
        instance.translate(language='fr', name='French Bar', description='French Hello')
        instance.save()

        translation.activate('fr')
        form = MultilingualBarFormAllFields(instance=instance, data={
            'name': 'Bar2',
            'name_fr': 'French Bar2',
            'price': 222,
            'quantity': 55,
            'description': 'Hello2',
            'description_fr': 'French Hello2'
        })

        instance = form.save()

        translation.activate('en')
        instance = Bar.objects.get(id=instance.id)  # Refresh from db

        self.assertEqual(instance.name, 'Bar2')
        self.assertEqual(instance.price, 222)
        self.assertEqual(instance.quantity, 55)
        self.assertEqual(instance.description, 'Hello2')

        translation.activate('fr')
        self.assertEqual(instance.name, 'French Bar2')
        self.assertEqual(instance.price, 222)
        self.assertEqual(instance.quantity, 55)
        self.assertEqual(instance.description, 'French Hello2')

    def testInitialDataContainsAllFieldValues(self):
        instance = Bar(name='Bar', price=12, quantity=5, description='Hello')
        instance.translate(language='fr', name='French Bar', description='French Hello')
        instance.save()

        translation.activate('fr')
        form = MultilingualBarFormAllFields(instance=instance)
        self.assertEqual(form.initial['name'], 'Bar')
        self.assertEqual(form.initial['name_fr'], 'French Bar')
        self.assertEqual(form.initial['price'], 12)
        self.assertEqual(form.initial['quantity'], 5)
        self.assertEqual(form.initial['description'], 'Hello')
        self.assertEqual(form.initial['description_fr'], 'French Hello')

class TestFeaturesThatShouldveBeenPresent(LinguoTests):

    def testDbColumnNameHandling(self):
        """
        Test that a modle with db_column set on a translatable field
        properly works.
        """
        instance = DbColumnNameModel(name="english name")
        instance.translate(language='fr', name="french name")
        instance.save()

        translation.activate('fr')
        m = DbColumnNameModel.objects.get(id=instance.id)
        self.assertEqual(m.name, 'french name')

        translation.activate('en')
        m = DbColumnNameModel.objects.get(id=instance.id)
        self.assertEqual(m.name, 'english name')



class TestsForUnupportedFeatures(object):  # LinguoTests):

    def testTransFieldHasNotNullConstraint(self):
        """
        Test a trans model with a trans field that has a not null constraint.
        """
        pass

    def testExtendingToMakeTranslatable(self):
        """
        Test the ability to extend a non-translatable model with MultilingualModel
        in order to make some field translatable.
        """
        pass

    def testSubclassingAbstractModelIntoTranslatableModel(self):
        """
        Test the ability to subclass a a non-translatable Abstract model
        and extend with MultilingualModel in order to make some field translatable.
        """
        pass

    def testModelFormWithFieldsExcluded(self):
        form = BarFormWithFieldsExcluded()
        self.assertEqual(len(form.fields), 4)
        self.assertTrue('price' in form.fields)
        self.assertTrue('quantity' in form.fields)
        self.assertTrue('description' in form.fields)
        self.assertTrue('description_fr' in form.fields)

    def testAdminChangelistFeaturesInSecondaryLanguage(self):

        # Create some Bar objects
        b1 = Bar.objects.create(name="apple", price=2, description="hello world", quantity=1)
        b1.translate(name="pomme", description="allo monde", language="fr")
        b1.save()

        b2 = Bar.objects.create(name="computer", price=3, description="oh my god", quantity=3)
        b2.translate(name="ordinator", description="oh mon dieu", language="fr")
        b2.save()

        translation.activate('fr')
        url = reverse('admin:tests_bar_changelist')
        response = self.client.get(url)

        # Check that the correct language is being displayed
        self.assertContains(response, 'allo monde')
        self.assertContains(response, 'oh mon dieu')
        self.assertNotContains(response, 'hello world')
        self.assertNotContains(response, 'oh my god')

        # Check the list filters
        self.assertContains(response, '?name=pomme')
        self.assertContains(response, '?name=ordinator')

        # Check that the filtering works
        response = self.client.get(url, {'name': 'ordinator'})
        self.assertContains(response, 'oh mon dieu')
        self.assertNotContains(response, 'allo monde')

        # Check the searching
        response = self.client.get(url, {'q': 'monde'})
        self.assertContains(response, 'allo monde')
        self.assertNotContains(response, 'oh mon dieu')
