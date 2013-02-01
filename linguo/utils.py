from django.conf import settings
from django.utils import translation


def get_real_field_name(field_name, language):
    """
    Returns the field that stores the value of the given translation
    in the specified language.
    """
    lang_code = get_normalized_language(language)
    if lang_code == get_normalized_language(settings.LANGUAGES[0][0]):
        return field_name
    else:
        return '%s_%s' % (field_name, language)


def get_normalized_language(language_code):
    """
    Returns the actual language extracted from the given language code
    (ie. locale stripped off). For example, 'en-us' becomes 'en'.
    """
    return language_code.split('-')[0]


def get_current_language():
    """
    Wrapper around `translation.get_language` that returns the normalized
    language code.
    """
    return get_normalized_language(translation.get_language())
