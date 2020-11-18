#!/usr/bin/env python
import sys

from setuptools import find_packages, setup

if sys.version_info < (3, 4):
    old_python_requires = ['singledispatch>=3.4']
else:
    # functools.singledispatch is in stdlib from Python 3.4 onwards.
    old_python_requires = []

setup(name='fluent_compiler',
      version='0.3',
      description='Blazing fast implementation of Fluent localization language.',
      long_description=open('README.rst').read() +
      '\n\nSee https://github.com/django-ftl/fluent-compiler/ for more info.',
      long_description_content_type='text/x-rst',
      author='Luke Plant',
      author_email='L.Plant.98@cantab.net',
      license='APL 2',
      url='https://github.com/django-ftl/fluent-compiler',
      keywords=['fluent', 'localization', 'l10n', 'compiler'],
      classifiers=[
          'Development Status :: 4 - Beta',
          'Intended Audience :: Developers',
          'License :: OSI Approved :: Apache Software License',
          'Programming Language :: Python :: 2.7',
          'Programming Language :: Python :: 3.5',
          'Programming Language :: Python :: 3.6',
          'Programming Language :: Python :: 3.7',
          'Programming Language :: Python :: 3.8',
      ],
      packages=find_packages('src'),
      package_dir={'': 'src'},
      # These should also be duplicated in tox.ini and ../.travis.yml
      install_requires=[
          'fluent.syntax>=0.14',
          'attrs>=19.3.0',
          'babel>=2.8.0',
          'pytz',
          'six',
      ] + old_python_requires,
      )
