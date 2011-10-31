from django.db import models
from django.db.models.fields.related import RelatedField
from django.conf import settings
from django.utils.translation import get_language

from linguo.utils import get_real_field_name


def rewrite_lookup_key(model, lookup_key):
    from linguo.models import MultilingualModel # to avoid circular import
    if issubclass(model, MultilingualModel):
        pieces = lookup_key.split('__')
        # If we are doing a lookup on a translatable field, we want to rewrite it to the actual field name
        # For example, we want to rewrite "name__startswith" to "name_fr__startswith"
        if pieces[0] in model._meta.translatable_fields:
            lookup_key = get_real_field_name(pieces[0], get_language().split('-')[0])

            remaining_lookup = '__'.join(pieces[1:])
            if remaining_lookup:
                lookup_key = '%s__%s' % (lookup_key, remaining_lookup)
        elif pieces[0] in map(lambda field: '%s_%s' % (field, settings.LANGUAGES[0][0]), model._meta.translatable_fields):
            # If the lookup field explicitly refers to the primary langauge (eg. "name_en"),
            # we want to rewrite that to point to the actual field name.
            lookup_key = pieces[0][:-3] # Strip out the language suffix
            remaining_lookup = '__'.join(pieces[1:])
            if remaining_lookup:
                lookup_key = '%s__%s' % (lookup_key, remaining_lookup)

    pieces = lookup_key.split('__')
    if len(pieces) > 1:
        # Check if we are doing a lookup to a related trans model
        fields_to_trans_models = get_fields_to_translatable_models(model)
        for field_to_trans, transmodel in fields_to_trans_models:
            if pieces[0] == field_to_trans:
                sub_lookup =  '__'.join(pieces[1:])
                if sub_lookup:
                    sub_lookup = rewrite_lookup_key(transmodel, sub_lookup)
                    lookup_key = '%s__%s' % (pieces[0], sub_lookup)
                break

    return lookup_key


def get_fields_to_translatable_models(model):
    results = []
    from linguo.models import MultilingualModel # to avoid circular import

    for field_name in model._meta.get_all_field_names():
        field_object, modelclass, direct, m2m = model._meta.get_field_by_name(field_name)
        if direct and isinstance(field_object, RelatedField):
            if issubclass(field_object.related.parent_model, MultilingualModel):
                results.append((field_name, field_object.related.parent_model))
    return results


class MultilingualQuerySet(models.query.QuerySet):
    
    def __init__(self, *args, **kwargs):
        super(MultilingualQuerySet, self).__init__(*args, **kwargs)
        if self.model and (not self.query.order_by):
            if self.model._meta.ordering:
                # If we have default ordering specified on the model, set it now so that
                # it can be rewritten. Otherwise sql.compiler will grab it directly from _meta
                ordering = []
                for key in self.model._meta.ordering:
                    ordering.append(rewrite_lookup_key(self.model, key))
                self.query.add_ordering(*ordering)
    
    def _filter_or_exclude(self, negate, *args, **kwargs):
        for key, val in kwargs.items():
            new_key = rewrite_lookup_key(self.model, key)
            del kwargs[key]
            kwargs[new_key] = val

        return super(MultilingualQuerySet, self)._filter_or_exclude(negate, *args, **kwargs)

    def order_by(self, *field_names):
        new_args = []
        for key in field_names:
            new_args.append(rewrite_lookup_key(self.model, key))
        return super(MultilingualQuerySet, self).order_by(*new_args)


class MultilingualManager(models.Manager):
    use_for_related_fields = True

    def get_query_set(self):
        return MultilingualQuerySet(self.model)

