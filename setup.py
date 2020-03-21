#!/usr/bin/env python
from setuptools import find_packages, setup

import sys
if sys.version_info < (3, 4):
    old_python_requires = ['singledispatch>=3.4']
else:
    # functools.singledispatch is in stdlib from Python 3.4 onwards.
    old_python_requires = []

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
          'Programming Language :: Python :: 3.7',
      ],
      packages=find_packages('src'),
      package_dir={'': 'src'},
      # These should also be duplicated in tox.ini and ../.travis.yml
      install_requires=[
          'fluent.syntax>=0.14,<=0.16',
          'attrs>=19.3.0',
          'babel>=2.8.0',
          'pytz',
          'six',
      ] + old_python_requires,
      )
