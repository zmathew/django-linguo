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
        return '%s_%s' % (field_name, lang_code)


def get_normalized_language(language_code):
    """
    Return normalized language (ie. just like locale). For example, 'en-us'
    becomes 'en_us'.
    """
    return language_code.replace('-', '_')


def get_current_language():
    """
    Wrapper around `translation.get_language` that returns the normalized
    language code.
    """
    return get_normalized_language(translation.get_language())
