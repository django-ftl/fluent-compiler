#!/usr/bin/env python
from setuptools import setup

import sys
if sys.version_info < (3, 4):
    old_python_requires = ['singledispatch>=3.4']
else:
    # functools.singledispatch is in stdlib from Python 3.4 onwards.
    old_python_requires = []

tests_requires = ['ast_decompiler>=0.3.2', 'beautifulsoup4>=4.7.1', 'hypothesis>=4.9.0',
                  'Markdown>=3.0.1', 'MarkupSafe>=1.1.1']

setup(name='fluent_compiler',
      version='0.1',
      description='Blazing fast implementation of Fluent localization language.',
      long_description='See https://github.com/django-ftl/fluent-compiler/ for more info.',
      author='Luke Plant',
      author_email='L.Plant.98@cantab.net',
      license='APL 2',
      url='https://github.com/django-ftl/fluent-compiler',
      keywords=['fluent', 'localization', 'l10n', 'compiler'],
      classifiers=[
          'Development Status :: 3 - Alpha',
          'Intended Audience :: Developers',
          'License :: OSI Approved :: Apache Software License',
          'Programming Language :: Python :: 2.7',
          'Programming Language :: Python :: 3.5',
          'Programming Language :: Python :: 3.6',
      ],
      packages=['fluent_compiler'],
      package_dir={'': 'src'},
      # These should also be duplicated in tox.ini and ../.travis.yml
      install_requires=[
          'fluent.syntax>=0.14,<=0.16',
          'attrs',
          'babel',
          'pytz',
          'six',
      ] + old_python_requires,
      test_suite='tests',
      tests_require=tests_requires,  # for 'setup.py test'
      extras_require={
          'develop': tests_requires,  # for 'pip install fluent_compiler[develop]'
      },
      )
