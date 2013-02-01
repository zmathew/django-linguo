from django import forms
from django.conf import settings

from linguo.utils import get_normalized_language


class MultilingualModelForm(forms.ModelForm):
    def __init__(self, data=None, files=None, instance=None, **kwargs):
        # We force the language to the primary, temporarily disabling the
        # routing based on current active language.
        # This allows all field values to be extracted from the model in super's init()
        # as it populates self.initial)

        if instance is not None:
            old_force_language = instance._force_language
            instance._force_language = get_normalized_language(settings.LANGUAGES[0][0])
        else:
            old_force_language = None

        super(MultilingualModelForm, self).__init__(
            data=data, files=files, instance=instance, **kwargs
        )
        self.instance._force_language = old_force_language

    def _post_clean(self):
        # We force the language to the primary, temporarily disabling the
        # routing based on current active language.
        # This allows all fields to be assigned to the corresponding language
        old_force_language = self.instance._force_language
        self.instance._force_language = get_normalized_language(settings.LANGUAGES[0][0])
        super(MultilingualModelForm, self)._post_clean()
        self.instance._force_language = old_force_language
