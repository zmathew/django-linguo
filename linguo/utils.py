from django.conf import settings


def get_real_field_name(field_name, language):
    """
    Returns the field that stores the value of the given translatable
    in the specified language.
    """
    if language == settings.LANGUAGES[0][0]:
        return field_name
    else:
        return '%s_%s' % (field_name, language)
