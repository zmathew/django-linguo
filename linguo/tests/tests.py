# coding=utf-8

import django
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.urlresolvers import reverse
from django.db import IntegrityError
from django.test import TestCase
from django.utils import translation
from django.utils.translation import ugettext as _

from linguo.exceptions import InvalidActionError
from linguo.tests.forms import BarForm, BarFormWithFieldsSpecified, \
    BarFormWithFieldsExcluded, BarFormWithCustomField
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
        expected = ['id', 'price', 'name', 'name_fr',]
        for i in range(len(Foo._meta.fields)):
            self.assertEqual(Foo._meta.fields[i].name, expected[i])
        
    def testCreation(self):
        translation.activate('en')
        obj = Foo.objects.create(name='Foo', price=10)
        self.assertTrue(obj._language, 'en')

        obj = Foo.objects.get(pk=obj.pk)
        self.assertEquals(obj.name, 'Foo')
        self.assertEquals(obj.price , 10)

        translation.activate('fr')
        obj_fr = Foo.objects.create(name='FrenchName', price=15)
        translation.activate('en')
        self.assertEquals(obj_fr._language, 'fr')

        self.assertEquals(Foo.objects.count(), 2)
    
    def testCreateWithInvalidLanguageReturnsError(self):
        try:
            Foo.objects.create(name='Foo', price=10, language='abcd')
        except ValidationError, err:
            self.assertTrue(u"'abcd' is not a valid language." in unicode(err))

    def testDelayedCreation(self):
        obj = Foo()
        obj.name = 'Foo'
        obj.price = 10
        obj.save()

        obj2 = Foo.objects.get(pk=obj.pk)
        self.assertEquals(obj2.name, 'Foo')
        self.assertEquals(obj2.price , 10)

    def testCreateTranslation(self):
        """
        We should be able to create a translation of an object.
        """
        obj_en = Foo.objects.create(name='Foo', price=10, language='en')
        obj_fr = obj_en.create_translation(name='FooFr', language='fr')

        self.assertEquals(type(obj_fr), type(obj_en))
        self.assertEquals(obj_fr.price, obj_en.price)

        self.assertEquals(obj_en.name, 'Foo')
        self.assertEquals(obj_fr.name, 'FooFr')
        self.assertEquals(Foo.objects.count(), 1)
    
    def testMultipleTransFields(self):
        obj_en = Hop.objects.create(name='hop', description='desc', price=11)
        obj_fr = obj_en.create_translation(name='hop_fr', description='desc_fr',
            language='fr')
        
        obj_en = Hop.objects.get(pk=obj_en.pk) # refresh from db
        self.assertEquals(obj_en.name, 'hop')
        self.assertEquals(obj_fr.name, 'hop_fr')
        self.assertEquals(obj_en.description, 'desc')
        self.assertEquals(obj_fr.description, 'desc_fr')
        self.assertEquals(obj_en.price, 11)
        self.assertEquals(obj_fr.price, 11)
    
    def testMultipleTransFieldsButNotSettingOneDuringCreation(self):
        obj_en = Hop.objects.create(name='hop', price=11)
        self.assertEquals(obj_en.name, 'hop')
        self.assertEquals(obj_en.price, 11)
        
    def testGettingTranslations(self):
        """
        Test the ability to get translations of an object
        """
        obj_en = Foo.objects.create(name='Foo', price=10, language='en')
        obj_fr = obj_en.create_translation(name='FooFr', language='fr')

        obj_en = Foo.objects.get(pk=obj_en.pk)

        other = Foo.objects.create(name='Other', price=30, language='en')
        self.assertEquals(Foo.objects.count(), 2)

        obj_en_fr_trans = obj_en.get_translation(language='fr')
        self.assertEquals(obj_en_fr_trans, obj_fr)
        self.assertEquals(obj_en_fr_trans.price, 10)
        self.assertEquals(obj_en_fr_trans.get_translation(language='en'), obj_en)
        obj_fr_en_trans = obj_fr.get_translation(language='en')
        self.assertEquals(obj_fr_en_trans, obj_en)

    def testTranslationSwitching(self):
        """
        Test the ability to switch an object's active translation
        """
        obj_en = Foo.objects.create(name='Foo', price=10, language='en')
        obj_fr = obj_en.create_translation(name='FooFr', language='fr')
        obj = Foo.objects.get(pk=obj_en.pk)
        obj.translate('en')
        self.assertEquals(obj.name, 'Foo')
        obj.translate('fr')
        self.assertEquals(obj.name, 'FooFr')

    def testCreateTranslationWithNewValueForNonTransField(self):
        """
        That value of non-trans fields should be the same for all translations.
        """
        obj_en = Foo.objects.create(name='Foo', price=10, language='en')
        obj_fr = obj_en.create_translation(name='FooFr', price=20, language='fr')
        
        obj_en = Foo.objects.get(pk=obj_en.pk) # refresh from db

        self.assertEquals(obj_fr.name, 'FooFr')
        self.assertEquals(obj_fr.price, 20)
        # Ensure obj_en has its price changed to the new value.
        self.assertEquals(obj_en.price, obj_fr.price)

        # Ensure no other fields of obj_en were changed
        self.assertEquals(obj_en.name, 'Foo')
        self.assertEquals(obj_en._language, 'en')

    def testCreateTranslationWithoutSaving(self):
        obj = Foo()
        obj.name = 'Foo'
        obj.price = 10

        try:
            obj2 = obj.create_translation(name='Foo2', language='fr')
        except InvalidActionError, e:
            self.assertEquals(unicode(e),
                _('Cannot create a translation of an unsaved object.')
            )
        else:
            self.fail()

    def testQuerysetUpdate(self):
        """
        Test that calling the update() method on a queryset should keep the db
        in a consistent state.
        """
        obj_en = Foo.objects.create(name='Foo', price=10, language='en')
        obj_fr = obj_en.create_translation(name='FooFr', language='fr')
        obj2 = Foo.objects.create(name='Foo2', price=13, language='en')

        qs = Foo.objects.all()
        self.assertEquals(qs.count(), 2)
        qs.update(price=12)

        # Refresh objects from db
        obj_en = Foo.objects.get(pk=obj_en.pk)
        obj_fr = obj_en.get_translation('fr')
        obj2 = Foo.objects.get(pk=obj2.pk)

        self.assertEquals(obj_en.price, 12)
        self.assertEquals(obj_fr.price, 12)
        self.assertEquals(obj2.price, 12)

    def testQuerysetUpdateExcludesOneTranslation(self):
        """
        If we have a queryset that excludes one of the translations,
        and we then call update() changing non-trans field,
        the excluded translation should be updated aswell.
        """
        obj_en = Foo.objects.create(name='Foo', price=10, language='en')
        obj_fr = obj_en.create_translation(name='FooFr', language='fr')
        obj2 = Foo.objects.create(name='Foo2', price=13, language='en')
        obj3 = Foo.objects.create(name='Foo3', price=65, language='en')

        qs = Foo.objects.filter(id__in=[obj_en.id, obj2.id,])
        qs.update(price=12)

        # Refresh from db
        obj_en = Foo.objects.get(pk=obj_en.pk)
        obj_fr = Foo.objects.get(pk=obj_fr.pk)
        obj2 = Foo.objects.get(pk=obj2.pk)
        obj3 = Foo.objects.get(pk=obj3.pk)

        self.assertEquals(obj_en.price, 12)
        self.assertEquals(obj_fr.price, 12) # This is the key test here
        self.assertEquals(obj2.price, 12)
        self.assertEquals(obj3.price, 65) # This should not have changed

    def testUniqueTogetherUsingTransFields(self):
        obj = Foo.objects.create(name='Foo', price=10)

        try: # name, price are unique together
            obj2 = Foo.objects.create(name='Foo', price=10)
        except IntegrityError, e:
            pass
        else:
            self.fail()

    def testFilteringOnTransField(self):
        obj_en = Foo.objects.create(name='English Foo', price=10, language='en')
        obj_fr = obj_en.create_translation(name='French Foo', language='fr')

        qs = Foo.objects.filter(name="English Foo")
        self.assertEquals(qs.count(), 1)
        self.assertEquals(qs[0], obj_en)

        qs = Foo.objects.filter(name__startswith="English")
        self.assertEquals(qs.count(), 1)
        self.assertEquals(qs[0], obj_en)
        qs = Foo.objects.exclude(name__startswith="English")
        self.assertEquals(qs.count(), 0)

        translation.activate('fr')

        qs = Foo.objects.filter(name="French Foo")
        self.assertEquals(qs.count(), 1)
        self.assertEquals(qs[0], obj_fr)

        qs = Foo.objects.filter(name__startswith="French")
        self.assertEquals(qs.count(), 1)
        self.assertEquals(qs[0], obj_fr)
        qs = Foo.objects.exclude(name__startswith="French")
        self.assertEquals(qs.count(), 0)

    def testFilteringUsingExplicitFieldName(self):
        obj_en = Foo.objects.create(name='English Foo', price=10, language='en')
        obj_fr = obj_en.create_translation(name='French Foo', language='fr')

        obj2_en = Foo.objects.create(name='Another English Foo', price=20, language='en')
        obj2_fr = obj2_en.create_translation(name='Another French Foo', language='fr')

        # we're in english
        translation.activate('en')
        qs = Foo.objects.filter(name_en="English Foo")
        self.assertEquals(qs.count(), 1)
        self.assertEquals(qs[0], obj_en)

        qs = Foo.objects.filter(name_en__startswith="English")
        self.assertEquals(qs.count(), 1)
        self.assertEquals(qs[0], obj_en)
        qs = Foo.objects.exclude(name_en__startswith="English")
        self.assertEquals(qs.count(), 1)
        self.assertEquals(qs[0], obj2_en)

        # try using the french field name
        qs = Foo.objects.filter(name_fr="French Foo")
        self.assertEquals(qs.count(), 1)
        self.assertEquals(qs[0], obj_en)

        qs = Foo.objects.filter(name_fr__startswith="French")
        self.assertEquals(qs.count(), 1)
        self.assertEquals(qs[0], obj_en)
        qs = Foo.objects.exclude(name_fr__startswith="French")
        self.assertEquals(qs.count(), 1)
        self.assertEquals(qs[0], obj2_en)

        # now try in french
        translation.activate('fr')
        qs = Foo.objects.filter(name_en="English Foo")
        self.assertEquals(qs.count(), 1)
        self.assertEquals(qs[0], obj_en)

        qs = Foo.objects.filter(name_en__startswith="English")
        self.assertEquals(qs.count(), 1)
        self.assertEquals(qs[0], obj_en)
        qs = Foo.objects.exclude(name_en__startswith="English")
        self.assertEquals(qs.count(), 1)
        self.assertEquals(qs[0], obj2_en)

        # try using the french field name
        qs = Foo.objects.filter(name_fr="French Foo")
        self.assertEquals(qs.count(), 1)
        self.assertEquals(qs[0], obj_en)

        qs = Foo.objects.filter(name_fr__startswith="French")
        self.assertEquals(qs.count(), 1)
        self.assertEquals(qs[0], obj_en)
        qs = Foo.objects.exclude(name_fr__startswith="French")
        self.assertEquals(qs.count(), 1)
        self.assertEquals(qs[0], obj2_en)

    def testOrderingOnTransField(self):
        obj_en = Foo.objects.create(name='English Foo', price=10, language='en')
        obj_fr = obj_en.create_translation(name='French Foo', language='fr')

        obj2 = Foo.objects.create(name='Another English Foo', price=12, language='en')
        obj2_fr = obj2.create_translation(name='Another French Foo', language='fr')

        qs = Foo.objects.order_by('name')
        self.assertEquals(qs.count(), 2)
        self.assertEquals(qs[0], obj2)
        self.assertEquals(qs[1], obj_en)

        translation.activate('fr')
        qs = Foo.objects.order_by('name')
        self.assertEquals(qs.count(), 2)
        self.assertEquals(qs[0], obj2)
        self.assertEquals(qs[1], obj_fr)
        self.assertEquals(qs[1].name, 'French Foo')

    def testDefaultOrderingIsTransField(self):
        """
        Test a model that has a trans field in the default ordering.
        """
        f1 = FooCategory.objects.create(name='B2 foo')
        f1.create_translation(name='B2 foo', language='fr')
        
        f2 = FooCategory.objects.create(name='A1 foo')
        f2.create_translation(name='C3 foo', language='fr')
        
        f3 = FooCategory.objects.create(name='C3 foo')
        f3.create_translation(name='A1 foo', language='fr')
        
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
        obj_en = Foo.objects.create(name='English Foo', price=10, language='en')
        obj_fr = obj_en.create_translation(name='French Foo', language='fr')

        obj2 = Foo.objects.create(name='Another English Foo', price=12, language='en')
        obj2_fr = obj2.create_translation(name='Another French Foo', language='fr')

        m1 = FooRel.objects.create(myfoo=obj_en, desc="description 1")
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
        obj_en = Foo.objects.create(name='English Foo', price=10, language='en')
        obj_fr = obj_en.create_translation(name='French Foo', language='fr')

        obj2_en = Foo.objects.create(name='Another English Foo', price=20, language='en')
        obj2_fr = obj2_en.create_translation(name='Another French Foo', language='fr')

        m1 = FooRel.objects.create(myfoo=obj_en, desc="description 1")
        m2 = FooRel.objects.create(myfoo=obj2_en, desc="description 2")

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
        doc_en = Doc.objects.create(pdf='something.pdf')
        doc_fr = doc_en.create_translation(pdf='something-fr.pdf', language='fr')
        
        translation.activate('en')
        self.assertEqual(Doc.objects.get().pdf.url, 'something.pdf')
        
        translation.activate('fr')
        self.assertEqual(Doc.objects.get().pdf.url, 'something-fr.pdf')        
        
    def testModelWithAFieldCalledLanguageThatIsNotTranslatable(self):
        lan_en = Lan.objects.create(name='Test en', language='en')
        lan_fr = lan_en.create_translation(name='Test fr', language='fr')
        
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
            price=9, quantity=2, language='en')
        self.assertTrue(obj._language, 'en')

        obj = Bar.objects.get(pk=obj.pk)
        self.assertEquals(obj.name, 'Bar')
        self.assertEquals(obj.description, 'test')
        self.assertEquals(obj.price , 9)
        self.assertEquals(obj.quantity , 2)

        translation.activate('fr')
        obj_fr = Bar.objects.create(name='FrenchBar', description='test in french',
            price=7, quantity=5)
        translation.activate('en')
        self.assertEquals(obj_fr._language, 'fr')

        self.assertEquals(Bar.objects.count(), 2)

    def testDelayedCreation(self):
        obj = Bar()
        obj.name = 'Bar'
        obj.description = 'Some desc'
        obj.price = 9
        obj.quantity = 2
        obj.save()

        obj2 = Bar.objects.get(pk=obj.pk)
        self.assertEquals(obj2.name, 'Bar')
        self.assertEquals(obj2.description, 'Some desc')
        self.assertEquals(obj2.price , 9)
        self.assertEquals(obj2.quantity , 2)

    def testCreateTranslation(self):
        """
        We should be able to create a translation of an object.
        """
        obj_en = Bar.objects.create(name='Bar', description='test',
            price=9, quantity=2, language='en')
        obj_fr = obj_en.create_translation(name='BarFr', description='test FR',
            language='fr')

        obj_en = Bar.objects.get(pk=obj_en.pk)

        self.assertEquals(type(obj_fr), type(obj_en))
        self.assertEquals(obj_en.name, 'Bar')
        self.assertEquals(obj_fr.name, 'BarFr')
        self.assertEquals(obj_en.description, 'test')
        self.assertEquals(obj_fr.description, 'test FR')
        self.assertEquals(obj_fr.price, obj_en.price)
        self.assertEquals(obj_fr.quantity, obj_en.quantity)

        self.assertEquals(Foo.objects.count(), 1)

    def testGettingTranslations(self):
        """
        Test the ability to get translations of an object.
        """
        obj_en = Bar.objects.create(name='Bar', description='test',
            price=9, quantity=2, language='en')
        obj_fr = obj_en.create_translation(name='BarFr', description='test FR',
            language='fr')

        obj_en = Bar.objects.get(pk=obj_en.pk)

        other = Bar.objects.create(name='Bar2', description='test 2',
            price=19, quantity=21, language='en')
        self.assertEquals(Foo.objects.count(), 2)

        obj_en_fr_trans = obj_en.get_translation(language='fr')
        self.assertEquals(obj_en_fr_trans, obj_fr)
        self.assertEquals(obj_en_fr_trans.price, 9)
        self.assertEquals(obj_en_fr_trans.quantity, 2)
        self.assertEquals(obj_en_fr_trans.get_translation(language='en'), obj_en)
        obj_fr_en_trans = obj_fr.get_translation(language='en')
        self.assertEquals(obj_fr_en_trans, obj_en)

    def testCreateTranslationWithNewValueForNonTransField(self):
        """
        That value of non-trans fields should be the same for all translations.
        """

        obj_en = Bar.objects.create(name='Bar', description='test',
            price=9, quantity=2, language='en')

        obj_fr = obj_en.create_translation(name='BarFr', description='test FR',
            price=20, quantity=40,
            language='fr')

        obj_en = Bar.objects.get(pk=obj_en.pk) # refresh from db

        self.assertEquals(obj_fr.name, 'BarFr')
        self.assertEquals(obj_fr.description, 'test FR')
        self.assertEquals(obj_fr.price, 20)
        self.assertEquals(obj_fr.quantity, 40)
        # Ensure obj_en has its price changed to the new value.
        self.assertEquals(obj_en.price, obj_fr.price)
        self.assertEquals(obj_en.quantity, 40)

        # Ensure no other fields of obj_en were changed
        self.assertEquals(obj_en.name, 'Bar')
        self.assertEquals(obj_en.description, 'test')
        self.assertEquals(obj_en._language, 'en')

    def testCreateTranslationWithoutSaving(self):
        obj = Bar()
        obj.name = 'Bar'
        obj.description = 'Some description'
        obj.price = 10
        obj.quantity = 2

        try:
            obj2 = obj.create_translation(name='Bar2', description='sadfsd',
                price=13, quantity=3, language='fr')
        except InvalidActionError, e:
            self.assertEquals(unicode(e),
                _('Cannot create a translation of an unsaved object.')
            )
        else:
            self.fail()

    def testQuerysetUpdate(self):
        """
        Test that calling the update() method on a queryset should keep the db
        in a consistent state.
        """

        obj_en = Bar.objects.create(name='Bar', description='test',
            price=9, quantity=2, language='en')
        obj_fr = obj_en.create_translation(name='BarFr', description='test FR',
            language='fr')
        obj2 = Bar.objects.create(name='Bar2', description='bar desc',
            price=13, quantity=5, language='en')

        qs = Bar.objects.all()
        self.assertEquals(qs.count(), 2)
        qs.update(price=88)
        qs.update(quantity=99)

        # Refresh objects from db
        obj_en = Bar.objects.get(pk=obj_en.pk)
        obj_fr = obj_en.get_translation('fr')
        obj2 = Bar.objects.get(pk=obj2.pk)

        self.assertEquals(obj_en.price, 88)
        self.assertEquals(obj_fr.price, 88)
        self.assertEquals(obj2.price, 88)
        self.assertEquals(obj_en.quantity, 99)
        self.assertEquals(obj_fr.quantity, 99)
        self.assertEquals(obj2.quantity, 99)

    def testQuerysetUpdateExcludesOneTranslation(self):
        """
        If we have a queryset that excludes one of the translations,
        and we then call update() changing non-trans field,
        the excluded translation should be updated aswell.
        """
        obj_en = Bar.objects.create(name='Bar', description='test',
            price=9, quantity=2, language='en')
        obj_fr = obj_en.create_translation(name='BarFr', description='test FR',
            language='fr')

        obj2 = Bar.objects.create(name='Bar2', description='bar2 desc',
            price=22, quantity=25, language='en')
        obj3 = Bar.objects.create(name='Bar3', description='bar3 desc',
            price=33, quantity=35, language='en')

        qs = Bar.objects.filter(id__in=[obj_en.id, obj2.id,])
        qs.update(price=54)
        qs.update(quantity=7)

        # Refresh from db
        obj_en = Bar.objects.get(pk=obj_en.pk)
        obj_fr = Bar.objects.get(pk=obj_fr.pk)
        obj2 = Bar.objects.get(pk=obj2.pk)
        obj3 = Bar.objects.get(pk=obj3.pk)

        self.assertEquals(obj_en.price, 54)
        self.assertEquals(obj_fr.price, 54) # This is the key test here
        self.assertEquals(obj_en.quantity, 7)
        self.assertEquals(obj_fr.quantity, 7)
        self.assertEquals(obj2.price, 54)
        self.assertEquals(obj2.quantity, 7)
        self.assertEquals(obj3.price, 33) # This should not have changed
        self.assertEquals(obj3.quantity, 35) # This should not have changed

    def testUniqueTogether(self):
        """
        Ensure that the unique_together definitions in child is working.
        """
        obj = Moo.objects.create(name='Moo', price=3, q1=4)

        try:
            Moo.objects.create(name='Moo2', price=15, q1=4)
        except IntegrityError, e:
            pass
        else:
            self.fail()

    def testUniqueTogetherInParent(self):
        """
        Ensure that the unique_together definitions in parent is working.
        """
        obj = Moo.objects.create(name='Moo', price=3, q1=4)
        try:
            Moo.objects.create(name='Moo', price=3, q1=88)
        except IntegrityError, e:
            pass
        else:
            self.fail()

    def testFilteringOnTransField(self):
        obj_en = Bar.objects.create(name='English Bar', description='English test',
            price=9, quantity=2, language='en')
        obj_fr = obj_en.create_translation(name='French Bar', description='French test',
            language='fr')

        qs = Bar.objects.filter(name="English Bar")
        self.assertEquals(qs.count(), 1)
        self.assertEquals(qs[0], obj_en)

        qs = Bar.objects.filter(name__startswith="English")
        self.assertEquals(qs.count(), 1)
        self.assertEquals(qs[0], obj_en)
        qs = Bar.objects.exclude(name__startswith="English")
        self.assertEquals(qs.count(), 0)

        translation.activate('fr')

        qs = Bar.objects.filter(name="French Bar")
        self.assertEquals(qs.count(), 1)
        self.assertEquals(qs[0], obj_fr)

        qs = Bar.objects.filter(name__startswith="French")
        self.assertEquals(qs.count(), 1)
        self.assertEquals(qs[0], obj_fr)
        qs = Bar.objects.exclude(name__startswith="French")
        self.assertEquals(qs.count(), 0)

    def testOrderingOnTransField(self):
        obj_en = Bar.objects.create(name='English Bar', description='English test',
            price=9, quantity=2, language='en')
        obj_fr = obj_en.create_translation(name='French Bar', description='French test',
            language='fr')

        obj2 = Bar.objects.create(name='Another English Bar', description='another english test',
            price=22, quantity=25, language='en')
        obj2_fr = obj2.create_translation(name='Another French Bar', description='another french test',
            language='fr')

        qs = Bar.objects.order_by('name')
        self.assertEquals(qs.count(), 2)
        self.assertEquals(qs[0], obj2)
        self.assertEquals(qs[1], obj_en)

        translation.activate('fr')

        qs = Bar.objects.order_by('name')
        self.assertEquals(qs.count(), 2)
        self.assertEquals(qs[0], obj2)
        self.assertEquals(qs[1], obj_fr)
        self.assertEquals(qs[1].name, 'French Bar')
    
    def testDefaultOrderingIsTransAndInheritedTransField(self):
        """
        Test a model that has an inherited trans field in the default ordering.
        """
        o1 = Ord.objects.create(name='B2 test', price=1)
        o1.create_translation(name='B2 test F', price=1, language='fr')
        
        o2 = Ord.objects.create(name='A1 test', price=2, last_name='Appleseed')
        o2.create_translation(name='C3 test F', price=2, last_name='Charlie', language='fr')
        
        o2b = Ord.objects.create(name='A1 test', price=3, last_name='Zoltan')
        o2b.create_translation(name='C3 test F', price=3, last_name='Bobby', language='fr')
        
        o3 = Ord.objects.create(name='C3 foo', price=4)
        o3.create_translation(name='A1 test F', price=4, language='fr')
        
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
        obj_en = Bar.objects.create(name='English Bar', description='English test',
            price=9, quantity=2, language='en')
        obj_fr = obj_en.create_translation(name='French Bar', description='French test',
            language='fr')

        obj2 = Bar.objects.create(name='Another English Bar', description='another english test',
            price=22, quantity=25, language='en')
        obj2_fr = obj2.create_translation(name='Another French Bar', description='another french test',
            language='fr')

        m1 = BarRel.objects.create(mybar=obj_en, desc="description 1")
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
        obj_en = Moe.objects.create(language='en',
           name='test', description='test description', price=5, quantity=3)
        obj_fr = obj_en.create_translation(language='fr',
            name='test-fr', description='test description fr'
        )

        obj_en = Moe.objects.get(pk=obj_en.pk)
        self.assertEquals(obj_en.name, 'test')
        self.assertEquals(obj_en.description, 'test description')
        self.assertEquals(obj_en.price, 5)
        self.assertEquals(obj_en.quantity, 3)

        other = Moe.objects.create(language='en',
           name='Other', description='test other', price=15, quantity=13)

        self.assertEquals(Moe.objects.count(), 2)

        obj_en_fr_trans = obj_en.get_translation(language='fr')
        self.assertEquals(obj_en_fr_trans, obj_fr)
        self.assertEquals(obj_en_fr_trans.name, 'test-fr')
        self.assertEquals(obj_en_fr_trans.description, 'test description fr')
        self.assertEquals(obj_en_fr_trans.price, 5)
        self.assertEquals(obj_en_fr_trans.quantity, 3)

        self.assertEquals(obj_en_fr_trans.get_translation(language='en'), obj_en)
        obj_fr_en_trans = obj_fr.get_translation(language='en')
        self.assertEquals(obj_fr_en_trans, obj_en)

    def testExtendingAbstractKeepsNonTransFields(self):
        obj_en = Moe.objects.create(language='en',
           name='test', description='test description', price=5, quantity=3)
        obj_fr = obj_en.create_translation(language='fr',
            name='test-fr', description='test description fr',
            price=13 #Changing price
        )
        obj_fr.quantity = 99 # Changing quantity
        obj_fr.save()

        obj_en = Moe.objects.get(pk=obj_en.pk)
        self.assertEquals(obj_en.price, 13)
        self.assertEquals(obj_en.quantity, 99)

        obj_en.price = 66
        obj_en.quantity = 77
        obj_en.save()

        translation.activate('fr')
        obj_fr = Moe.objects.get(pk=obj_fr.pk)
        self.assertEquals(obj_fr.price, 66)
        self.assertEquals(obj_fr.quantity, 77)


class ForeignKeyTests(LinguoTests):

    def testModelWithFK(self):
        """
        A trans model has a foreign key to another trans model.
        The foreign key is not language specific.
        """
        obj_en = Foo.objects.create(name='English Foo', price=10, language='en')

        obj2 = Foo.objects.create(name='Another English Foo', price=12, language='en')
        obj2_fr = obj2.create_translation(name='Another French Foo', language='fr')

        rel1 = Gem.objects.create(somefoo=obj_en, gemtype='a')
        rel1_fr = rel1.create_translation(gemtype='b', language='fr')

        rel2 = Gem.objects.create(somefoo=obj2, gemtype='a')

        rel1 = Gem.objects.get(pk=rel1.pk)
        rel2 = Gem.objects.get(pk=rel2.pk)

        self.assertEquals(rel1.somefoo, obj_en)
        rel1_fr = rel1.get_translation('fr')
        self.assertEquals(rel1_fr.somefoo, obj_en)

        # Ensure the reverse manager returns expected results
        self.assertEquals(obj_en.gem_set.count(), 1)
        self.assertEquals(obj_en.gem_set.all()[0], rel1)
        # The translation should have the consistent results
        obj_fr = obj_en.create_translation(name='French Foo', language='fr')
        self.assertEquals(obj_fr.gem_set.count(), 1)
        self.assertEquals(obj_fr.gem_set.all()[0], rel1)

        self.assertEquals(rel2.somefoo, obj2)
        self.assertEquals(obj2.gem_set.count(), 1)
        self.assertEquals(obj2.gem_set.all()[0], rel2)


    def testChangeFKOnTranslation(self):
        """
        Test for consistency when you change the foreign key on a translation.
        """
        obj_en = Foo.objects.create(name='English Foo', price=10, language='en')

        obj2 = Foo.objects.create(name='Another English Foo', price=12, language='en')
        obj2_fr = obj2.create_translation(name='Another French Foo', language='fr')

        rel1 = Gem.objects.create(somefoo=obj_en, gemtype='a')
        rel1_fr = rel1.create_translation(gemtype='b', language='fr')
        rel1_fr.somefoo = obj2
        rel1_fr.save()

        rel2 = Gem.objects.create(somefoo=obj2, gemtype='a')

        rel1 = Gem.objects.get(pk=rel1.pk)
        self.assertEquals(rel1.somefoo, obj2)
        self.assertEquals(rel1_fr.somefoo, obj2)
        self.assertEquals(rel2.somefoo, obj2)

        self.assertEquals(obj2.gem_set.count(), 2)
        self.assertEquals(obj2.gem_set.order_by('id')[0], rel1)
        self.assertEquals(obj2.gem_set.order_by('id')[1], rel2)

        self.assertEquals(obj2_fr.gem_set.count(), 2)
        self.assertEquals(obj2_fr.gem_set.order_by('id')[0], rel1)
        self.assertEquals(obj2_fr.gem_set.order_by('id')[1], rel2)

        self.assertEquals(obj_en.gem_set.count(), 0)

    def testRemoveFk(self):
        """
        Test for consistency when you remove a foreign key connection.
        """
        obj_en = Foo.objects.create(name='English Foo', price=10, language='en')
        obj_fr = obj_en.create_translation(name='French Foo', language='fr')

        obj2 = Foo.objects.create(name='Another English Foo', price=12, language='en')

        rel1 = Gem.objects.create(somefoo=obj_en, gemtype='a')
        rel1_fr = rel1.create_translation(gemtype='b', language='fr')
        rel1.somefoo = None
        rel1.save()

        rel2 = Gem.objects.create(somefoo=obj2, gemtype='a')

        rel1 = Gem.objects.get(pk=rel1.pk)
        rel1_fr = Gem.objects.get(pk=rel1_fr.pk)
        self.assertEquals(rel1.somefoo, None)
        self.assertEquals(rel1_fr.somefoo, None)
        self.assertEquals(rel2.somefoo, obj2)
        self.assertEquals(obj_en.gem_set.count(), 0)
        self.assertEquals(obj_fr.gem_set.count(), 0)
        self.assertEquals(obj2.gem_set.count(), 1)

    def testFKReverseCreation(self):
        """
        Test creating an object using the reverse manager.
        """
        obj_en = Foo.objects.create(name='English Foo', price=10, language='en')
        obj2 = Foo.objects.create(name='Another English Foo', price=12, language='en')
        obj2_fr = obj2.create_translation(name='Another French Foo', language='fr')

        rel1 = obj2.gem_set.create(gemtype='a')

        obj2 = Foo.objects.get(pk=obj2.pk)
        obj2_fr = Foo.objects.get(pk=obj2_fr.pk)

        self.assertEquals(obj2.gem_set.count(), 1)
        self.assertEquals(obj2.gem_set.order_by('id')[0], rel1)
        self.assertEquals(obj2_fr.gem_set.count(), 1)
        self.assertEquals(obj2_fr.gem_set.order_by('id')[0], rel1)

    def testFKReverseAddition(self):
        """
        Test adding an object using the reverse manager.
        """
        obj_en = Foo.objects.create(name='English Foo', price=10, language='en')
        obj2 = Foo.objects.create(name='Another English Foo', price=12, language='en')
        obj2_fr = obj2.create_translation(name='Another French Foo', language='fr')

        rel1 = Gem.objects.create(somefoo=obj_en, gemtype='a')
        obj2.gem_set.add(rel1)
        rel1 = Gem.objects.get(pk=rel1.pk)
        self.assertEquals(rel1.somefoo, obj2)
        self.assertEquals(obj2.gem_set.count(), 1)
        self.assertEquals(obj2.gem_set.all()[0], rel1)

    def testFKReverseRemoval(self):
        """
        Test removing an object using the reverse manager.
        """
        obj_en = Foo.objects.create(name='English Foo', price=10, language='en')
        obj2 = Foo.objects.create(name='Another English Foo', price=12, language='en')
        obj2_fr = obj2.create_translation(name='Another French Foo', language='fr')

        rel1 = Gem.objects.create(somefoo=obj_en, gemtype='a')
        rel1_fr = rel1.create_translation(gemtype='b', language='fr')

        obj2.gem_set.add(rel1)

        rel1 = Gem.objects.get(pk=rel1.pk)
        rel1_fr = Gem.objects.get(pk=rel1_fr.pk)
        self.assertEquals(rel1.somefoo, obj2)
        self.assertEquals(rel1_fr.somefoo, obj2)

        self.assertEquals(obj_en.gem_set.count(), 0)
        self.assertEquals(obj2.gem_set.count(), 1)
        self.assertEquals(obj2.gem_set.all()[0], rel1)
        self.assertEquals(obj2_fr.gem_set.count(), 1)
        self.assertEquals(obj2_fr.gem_set.all()[0], rel1)

        obj2.gem_set.remove(rel1)
        rel1 = Gem.objects.get(pk=rel1.pk)
        rel1_fr = Gem.objects.get(pk=rel1_fr.pk)
        self.assertEquals(rel1.somefoo, None)
        self.assertEquals(rel1_fr.somefoo, None)
        self.assertEquals(obj2.gem_set.count(), 0)
        self.assertEquals(obj2_fr.gem_set.count(), 0)

    def testFKToTranslation(self):
        """
        Test when the foreign key points to a translation of an object.
        """
        obj_en = Foo.objects.create(name='English Foo', price=10, language='en')
        obj_fr = obj_en.create_translation(name='French Foo', language='fr')

        rel1 = Gem.objects.create(language='en', gemtype='a', somefoo=obj_fr)

        self.assertEquals(obj_fr.gem_set.count(), 1)
        self.assertEquals(obj_fr.gem_set.all()[0], rel1)

        self.assertEquals(obj_en.gem_set.count(), 1)
        self.assertEquals(obj_en.gem_set.all()[0], rel1)

    def testFKReverseAdditionOnTranslation(self):
        """
        Test adding an object using the reverse manager of a translation.
        """
        obj_en = Foo.objects.create(name='English Foo', price=10, language='en')
        obj_fr = obj_en.create_translation(name='French Foo', language='fr')

        rel1 = Gem.objects.create(language='en', gemtype='a')
        obj_fr.gem_set.add(rel1)
        rel1 = Gem.objects.get(pk=rel1.pk)

        self.assertEquals(rel1.somefoo, obj_fr)

        self.assertEquals(obj_fr.gem_set.count(), 1)
        self.assertEquals(obj_fr.gem_set.all()[0], rel1)
        self.assertEquals(obj_en.gem_set.count(), 1)
        self.assertEquals(obj_en.gem_set.all()[0], rel1)

class ManyToManyTests(LinguoTests):

    def testCreateM2M(self):
        obj = Foo.objects.create(name='English Foo', price=10, language='en')
        cat = obj.categories.create(name='C1')
        cat2 = FooCategory.objects.create(name='C2')

        self.assertEquals(obj.categories.count(), 1)
        self.assertEquals(obj.categories.all()[0], cat)

        # obj fr should have the same categories
        obj_fr = obj.create_translation(language='fr', name='French Foo')

        self.assertEquals(obj_fr.categories.count(), 1)
        self.assertEquals(obj_fr.categories.all()[0], cat)

        # Reverse lookup should return only foo
        self.assertEquals(cat.foo_set.count(), 1)
        self.assertEquals(cat.foo_set.all()[0], obj)

        # cat fr should have the same foo
        cat_fr = cat.create_translation(language='fr', name='C1 fr')
        self.assertEquals(cat_fr.foo_set.all()[0], obj)

        obj2 = Foo.objects.create(language='en', name='Another Foo', price=5)
        self.assertEquals(obj2.categories.count(), 0)

        self.assertEquals(cat.foo_set.count(), 1)
        self.assertEquals(cat.foo_set.all()[0], obj)
        self.assertEquals(cat2.foo_set.count(), 0)

    def testRemovingM2M(self):
        obj = Foo.objects.create(name='English Foo', price=10, language='en')
        obj_fr = obj.create_translation(language='fr', name='French Foo')

        obj2 = Foo.objects.create(name='Another English Foo', price=12, language='en')

        cat = obj.categories.create(name='C1')
        cat2 = obj2.categories.create(name='C2')
        cat3 = obj_fr.categories.create(name='C3')

        self.assertEquals(obj.categories.count(), 2)
        self.assertEquals(obj_fr.categories.count(), 2)

        obj_fr.categories.remove(cat)

        self.assertEquals(obj_fr.categories.count(), 1)
        self.assertEquals(obj_fr.categories.all()[0], cat3)
        self.assertEquals(obj.categories.count(), 1)
        self.assertEquals(obj.categories.all()[0], cat3)

        self.assertEquals(obj2.categories.count(), 1)
        self.assertEquals(obj2.categories.all()[0], cat2)
        self.assertEquals(cat2.foo_set.all()[0], obj2)

    def testClearingM2M(self):
        obj = Foo.objects.create(name='English Foo', price=10, language='en')
        obj_fr = obj.create_translation(language='fr', name='French Foo')
        obj2 = Foo.objects.create(name='Another English Foo', price=12, language='en')
        cat = obj.categories.create(name='C1')
        cat2 = obj2.categories.create(name='C2')
        cat3 = obj_fr.categories.create(name='C3')

        self.assertEquals(obj.categories.count(), 2)
        self.assertEquals(obj_fr.categories.count(), 2)

        obj_fr.categories.clear()

        self.assertEquals(obj_fr.categories.count(), 0)
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
        self.assertEqual(bar._language, 'en')
        self.assertEqual(bar.name, 'Test')
        self.assertEqual(bar.price, 13)
        self.assertEqual(bar.quantity, 3)
        self.assertEqual(bar.description, 'This is a test')
        bar_fr = bar.get_translation('fr')
        self.assertEqual(bar_fr._language, 'fr')
        self.assertEqual(bar_fr.name, 'French Test')
        self.assertEqual(bar_fr.price, 13)
        self.assertEqual(bar_fr.quantity, 3)
        self.assertEqual(bar_fr.description, 'French Description')
        
        # Create the form with an instance
        data2 = {'name': 'Changed', 'name_fr': 'Changed French', 'price': 43,
            'quantity': 22, 'description': 'Changed description',
            'description_fr': 'Changed description French'
        }
        form = BarForm(instance=bar, data=data2)
        bar = form.save()
        self.assertEqual(bar._language, 'en')
        self.assertEqual(bar.name, 'Changed')
        self.assertEqual(bar.price, 43)
        self.assertEqual(bar.quantity, 22)
        self.assertEqual(bar.description, 'Changed description')
        bar_fr = bar.get_translation('fr')
        self.assertEqual(bar_fr._language, 'fr')
        self.assertEqual(bar_fr.name, 'Changed French')
        self.assertEqual(bar_fr.price, 43)
        self.assertEqual(bar_fr.quantity, 22)
        self.assertEqual(bar_fr.description, 'Changed description French')
    
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
        self.assertEqual(unicode(form['description'].label), u'Description') # This does not get translated because Django generates the verbose_name as a string
        self.assertEqual(unicode(form['description_fr'].label), u'Déscriptione (Français)')
        bar_fr = form.save()
        
        bar = bar_fr.get_translation('en')
        self.assertEqual(bar._language, 'en')
        self.assertEqual(bar.name, '')
        self.assertEqual(bar.price, 13)
        self.assertEqual(bar.quantity, 3)
        self.assertEqual(bar.description, '')
        
        self.assertEqual(bar_fr._language, 'fr')
        self.assertEqual(bar_fr.name, 'French Test')
        self.assertEqual(bar_fr.price, 13)
        self.assertEqual(bar_fr.quantity, 3)
        self.assertEqual(bar_fr.description, 'French Description')
    
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
        self.assertEqual(bar._language, 'en')
        self.assertEqual(bar.name, 'Test')
        self.assertEqual(bar.price, 13)
        self.assertEqual(bar.quantity, 3)
        self.assertEqual(bar.description, 'This is a test')
        bar_fr = bar.get_translation('fr')
        self.assertEqual(bar_fr._language, 'fr')
        self.assertEqual(bar_fr.name, '')
        self.assertEqual(bar_fr.price, 13)
        self.assertEqual(bar_fr.quantity, 3)
        self.assertEqual(bar_fr.description, '')
        
        # Create the form with an instance
        data2 = {'name': 'Changed', 'price': 43,
            'quantity': 22, 'description': 'Changed description',
        }
        form = BarFormWithFieldsSpecified(instance=bar, data=data2)
        bar = form.save()
        self.assertEqual(bar._language, 'en')
        self.assertEqual(bar.name, 'Changed')
        self.assertEqual(bar.price, 43)
        self.assertEqual(bar.quantity, 22)
        self.assertEqual(bar.description, 'Changed description')
        bar_fr = bar.get_translation('fr')
        self.assertEqual(bar_fr._language, 'fr')
        self.assertEqual(bar_fr.name, '')
        self.assertEqual(bar_fr.price, 43)
        self.assertEqual(bar_fr.quantity, 22)
        self.assertEqual(bar_fr.description, '')
    
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
        bar_fr = form.save()
        self.assertEqual(bar_fr._language, 'fr')
        self.assertEqual(bar_fr.name, 'Test French')
        self.assertEqual(bar_fr.price, 13)
        self.assertEqual(bar_fr.quantity, 3)
        self.assertEqual(bar_fr.description, 'This is a French test')
        bar_en = bar_fr.get_translation('en')
        self.assertEqual(bar_en._language, 'en')
        self.assertEqual(bar_en.name, '')
        self.assertEqual(bar_en.price, 13)
        self.assertEqual(bar_en.quantity, 3)
        self.assertEqual(bar_en.description, '')
        
        # Create the form with an instance
        data2 = {'name': 'Changed', 'price': 43,
            'quantity': 22, 'description': 'Changed description',
        }
        form = BarFormWithFieldsSpecified(instance=bar_fr, data=data2)
        bar_fr = form.save()
        self.assertEqual(bar_fr._language, 'fr')
        self.assertEqual(bar_fr.name, 'Changed')
        self.assertEqual(bar_fr.price, 43)
        self.assertEqual(bar_fr.quantity, 22)
        self.assertEqual(bar_fr.description, 'Changed description')
        bar_en = bar_fr.get_translation('en')
        self.assertEqual(bar_en._language, 'en')
        self.assertEqual(bar_en.name, '')
        self.assertEqual(bar_en.price, 43)
        self.assertEqual(bar_en.quantity, 22)
        self.assertEqual(bar_en.description, '')


if django.VERSION[:3] >= (1, 1, 2): # The AdminTests only pass with django >= 1.1.2 (but compatibility is django >= 1.0.3)
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
            b1.create_translation(name="pomme", description="allo monde", language="fr")
            
            b2 = Bar.objects.create(name="computer", price=3, description="oh my god", quantity=3)
            b2.create_translation(name="ordinator", description="oh mon dieu", language="fr")
            
            url = reverse('admin:tests_bar_changelist')
            response = self.client.get(url)
            
            # Check that the correct language is being displayed
            self.assertContains(response, 'hello world')
            self.assertContains(response, 'oh my god')
            
            # Check the list filters
            self.assertContains(response, '?name=apple')
            self.assertContains(response, '?name=computer')
            
            # Check that the filtering works
            response = self.client.get(url, {'name':'computer'})
            self.assertContains(response, 'oh my god')
            self.assertNotContains(response, 'hello world')
            
            # Check the searching
            response = self.client.get(url, {'q':'world'})
            self.assertContains(response, 'hello world')
            self.assertNotContains(response, 'oh my god')


class TestsForUnupportedFeatures(object):#LinguoTests):

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
        b1.create_translation(name="pomme", description="allo monde", language="fr")
        
        b2 = Bar.objects.create(name="computer", price=3, description="oh my god", quantity=3)
        b2.create_translation(name="ordinator", description="oh mon dieu", language="fr")
        
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
        response = self.client.get(url, {'name':'ordinator'})
        self.assertContains(response, 'oh mon dieu')
        self.assertNotContains(response, 'allo monde')
        
        # Check the searching
        response = self.client.get(url, {'q':'monde'})
        self.assertContains(response, 'allo monde')
        self.assertNotContains(response, 'oh mon dieu')
