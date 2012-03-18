import os

# Settings for running tests.

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(os.path.dirname(__file__), 'linguo.db'),
    }
}

# This is just for backwards compatibility
DATABASE_ENGINE = 'sqlite3'
DATABASE_NAME = DATABASES['default']['NAME']

USE_I18N = True

LANGUAGE_CODE = 'en'

gettext = lambda s: s
LANGUAGES = (
    ('en', gettext('English')),
    ('fr', gettext('French')),
)

ROOT_URLCONF = 'linguo.tests.urls'

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',

    'linguo',
    'linguo.tests',
)

LOCALE_PATHS = (
    os.path.realpath(os.path.dirname(__file__)) + '/locale/',
)

SECRET_KEY = 'M$kdhspl@#)*43cas<&dsjk'
