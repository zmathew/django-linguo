import copy

from django.db import models
from django.db.models.base import ModelBase
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _
from django.utils.translation import get_language

from linguo.exceptions import InvalidActionError, MultilingualFieldError
from linguo.managers import MultilingualManager
from linguo.utils import get_real_field_name


class MultilingualModelBase(ModelBase):

    def __new__(cls, name, bases, attrs):
        local_trans_fields, inherited_trans_fields = \
            MultilingualModelBase.get_trans_fields(name, bases, attrs)

        if ('Meta' in attrs) and hasattr(attrs['Meta'], 'translate'):
            delattr(attrs['Meta'], 'translate')

        attrs = MultilingualModelBase.rewrite_trans_fields(local_trans_fields, attrs)
        attrs = MultilingualModelBase.rewrite_unique_together(local_trans_fields, attrs)

        new_obj = super(MultilingualModelBase, cls).__new__(cls, name, bases, attrs)
        new_obj._meta.translatable_fields = inherited_trans_fields + local_trans_fields
        
        # Add a property that masks the translatable fields
        for field_name in local_trans_fields:
            # Some fields add a descriptor (ie. FileField), we want to keep that
            if field_name in new_obj.__dict__:
                primary_lang_field_name = '%s_%s' % (field_name, settings.LANGUAGES[0][0])
                setattr(new_obj, primary_lang_field_name, new_obj.__dict__[field_name])
            
            getter = MultilingualModelBase.generate_field_getter(field_name)
            setter = MultilingualModelBase.generate_field_setter(field_name)
            setattr(new_obj, field_name, property(getter, setter))
        
        return new_obj

    @classmethod
    def get_trans_fields(cls, name, bases, attrs):
        local_trans_fields = []
        inherited_trans_fields = []

        if ('Meta' in attrs) and hasattr(attrs['Meta'], 'translate'):
            local_trans_fields = list(attrs['Meta'].translate)

        # Check for translatable fields in parent classes
        for base in bases:
            if hasattr(base, '_meta') and hasattr(base._meta, 'translatable_fields'):
                inherited_trans_fields.extend(list(base._meta.translatable_fields))

        # Validate the local_trans_fields
        for field in local_trans_fields:
            if field not in attrs:
                raise MultilingualFieldError(
                   '`%s` cannot be translated because it'
                     ' is not a field on the model %s' % (field, name)
                )

        return (local_trans_fields, inherited_trans_fields)

    @classmethod
    def rewrite_trans_fields(cls, local_trans_fields, attrs):
        """Create copies of the local translatable fields for each language"""
        for field in local_trans_fields:

            for lang in settings.LANGUAGES[1:]:
                lang_code = lang[0]

                lang_field = copy.copy(attrs[field])
                # The new field cannot have the same creation_counter (else the ordering will be arbitrary)
                # We increment by a decimal point because we don't want to have
                # to adjust the creation_counter of ALL other subsequent fields
                lang_field.creation_counter += 0.0001 # Limitation this trick: only supports upto 10,000 languages
                lang_fieldname = get_real_field_name(field, lang_code)
                lang_field.name = lang_fieldname
                
                if lang_field.verbose_name is not None:
                    # This is to extract the original value that was passed into ugettext_lazy
                    # We do this so that we avoid evaluating the lazy object.
                    raw_verbose_name = lang_field.verbose_name._proxy____args[0]
                else:
                    raw_verbose_name = field.replace('-', ' ')
                lang_field.verbose_name = _(u'%s (%s)'% (raw_verbose_name, lang[1]))
                
                attrs[lang_fieldname] = lang_field


        return attrs
    
    @classmethod
    def generate_field_getter(cls, field):
        # Property that masks the getter of a translatable field
        def getter(self_reference):
            attrname = '%s_%s' % (field, self_reference._language)
            return getattr(self_reference, attrname)
        return getter
    
    @classmethod
    def generate_field_setter(cls, field):
        # Property that masks a setter of the translatable field
        def setter(self_reference, value):
            attrname = '%s_%s' % (field, self_reference._language)
            setattr(self_reference, attrname, value)
        return setter

    @classmethod
    def rewrite_unique_together(cls, local_trans_fields, attrs):
        if ('Meta' not in attrs) or not hasattr(attrs['Meta'], 'unique_together'):
            return attrs

        # unique_together can be either a tuple of tuples, or a single
        # tuple of two strings. Normalize it to a tuple of tuples.
        ut = attrs['Meta'].unique_together
        if ut and not isinstance(ut[0], (tuple, list)):
            ut = (ut,)

        # Determine which constraints need to be rewritten
        new_ut = []
        constraints_to_rewrite = []
        for constraint in ut:
            needs_rewriting = False
            for field in constraint:
                if field in local_trans_fields:
                    needs_rewriting = True
                    break
            if needs_rewriting:
                constraints_to_rewrite.append(constraint)
            else:
                new_ut.append(constraint)

        # Now perform the rewritting
        for constraint in constraints_to_rewrite:
            for lang in settings.LANGUAGES:
                language = lang[0]
                new_constraint = []
                for field in constraint:
                    if field in local_trans_fields:
                        field = get_real_field_name(field, language)
                    new_constraint.append(field)

                new_ut.append(tuple(new_constraint))

        attrs['Meta'].unique_together = tuple(new_ut)
        return attrs


class MultilingualModel(models.Model):
    __metaclass__ = MultilingualModelBase

    objects = MultilingualManager()

    class Meta:
        abstract = True

    def __init__(self, *args, **kwargs):
        # Set the language for this instance
        if 'language' in kwargs:
            lang_codes = [lang[0] for lang in settings.LANGUAGES]
            if kwargs['language'] not in lang_codes:
                raise ValidationError(u"'%(language)s' is not a valid language." % {'language': kwargs['language']})
            
            self._language = kwargs['language']
            if 'language' not in self._meta.get_all_field_names():
                del kwargs['language']
        else:
            self._language = get_language().split('-')[0]
        # Rewrite any keyword arguments for translatable fields
        for field in self._meta.translatable_fields:
            if field in kwargs.keys():
                attrname = get_real_field_name(field, self._language)
                if attrname != field:
                    kwargs[attrname] = kwargs[field]
                    del kwargs[field]

        # We have to switch to the primary language before initializing
        # or else the wrong value will be set for the non-primary language if activated
        language = self._language
        self._language = settings.LANGUAGES[0][0]
        super(MultilingualModel, self).__init__(*args, **kwargs)
        self._language = language
    
    def save(self, *args, **kwargs):
        # We have to switch to the primary language before saving
        # or else our masking property will return the wrong value for the primary language field
        language = self._language
        self._language = settings.LANGUAGES[0][0]
        super(MultilingualModel, self).save(*args, **kwargs)
        # Now we can switch back
        self._language = language
    
    def get_translation(self, language):
        obj = self._default_manager.get(pk=self.pk)
        obj._language = language
        return obj

    def create_translation(self, language, **kwargs):
        if not self.pk:
            raise InvalidActionError(
                'Cannot create a translation of an unsaved object.'
            )

        trans_obj = self.get_translation(language)
        
        for key, val in kwargs.iteritems():
            setattr(trans_obj, key, val)
        
        trans_obj.save()
        return trans_obj
