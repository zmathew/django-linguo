from distutils.core import setup

import linguo


setup(
    name='django-linguo',
    packages=['linguo', 'linguo.tests'],
    package_data={'linguo': ['tests/locale/*/LC_MESSAGES/*']},
    version=linguo.__version__,
    description=linguo.__doc__,
    long_description=open('README.txt').read(),
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Topic :: Internet :: WWW/HTTP :: Indexing/Search',
        'Framework :: Django',
    ],
    author='Zach Mathew',
    url='http://github.com/zmathew/django-linguo',
    license='BSD',
)
