fluent-compiler
===================

This is a Python implementation of Project Fluent, a localization framework
designed to unleash the entire expressive power of natural language
translations.

It provides a different implementation from the official
[fluent.runtime](https://github.com/projectfluent/python-fluent) implementation,
distinguished mainly by:

- strategy: we compile FTL files to Python AST
- speed: as a result of the above, plus optimizations, we get blazing fast
  performance, especially when combined with PyPy which can further optimize.
- compile-time checking and error reporting
- 'escapers' feature for handling things like HTML escaping/embedding correctly.

Status
-------

This code was originally developed as part of `fluent.runtime`, as an
alternative implementation of `FluentBundle`, but never got merged to the master
branch. We are in the process of pulling it out as a separate package.

It has seen usage in production a dependency of `django-ftl` for a long time.
However, now that we don't need full compatibility with `fluent.runtime` it will
be modified further in terms of interface.

Installation
------------

To install:

    pip install fluent_compiler

(Hopefully soon!)

Usage
-----

See the [docs folder](docs) or [read them on
readthedocs.org](https://fluent-compiler.readthedocs.io/en/latest/).
