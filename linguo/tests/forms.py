from django import forms

from linguo.forms import MultilingualModelForm
from linguo.tests.models import Bar


class BarForm(forms.ModelForm):
    class Meta:
        model = Bar
        if hasattr(forms, 'ALL_FIELDS'):  # For Django < 1.6 compatibility
            fields = forms.ALL_FIELDS


class BarFormWithFieldsSpecified(forms.ModelForm):
    class Meta:
        model = Bar
        fields = ('name', 'price', 'description', 'quantity',)


class BarFormWithFieldsExcluded(forms.ModelForm):
    class Meta:
        model = Bar
        exclude = ('categories', 'name',)


class BarFormWithCustomField(BarFormWithFieldsSpecified):
    custom_field = forms.CharField()


class MultilingualBarFormAllFields(MultilingualModelForm):
    class Meta:
        model = Bar
        if hasattr(forms, 'ALL_FIELDS'):  # For Django < 1.6 compatibility
            fields = forms.ALL_FIELDS
