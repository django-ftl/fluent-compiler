fluent-compiler
===============

This is a Python implementation of Project Fluent, a localization
framework designed to unleash the entire expressive power of natural
language translations.

It provides a different implementation from the official
`fluent.runtime <https://github.com/projectfluent/python-fluent>`_
implementation, distinguished mainly by:

- strategy: we compile FTL files to Python code via AST and ``exec`` it (similar
  to the strategy used by projects like Mako, Jinja2 and Genshi.
- speed: as a result of the above, plus optimizations, we get blazing
  fast performance, especially when combined with PyPy which can
  further optimize.
- compile-time checking and error reporting.
- 'escapers' feature for handling things like HTML escaping/embedding correctly.



Installation
------------

To install::

    pip install fluent_compiler

Usage
-----

See the `docs folder
<https://github.com/django-ftl/fluent-compiler/tree/master/docs/>`_ or `read
them on readthedocs.org <https://fluent-compiler.readthedocs.io/en/latest/>`_.


Status
------

The package should be considered a 'beta'/'release candidate'. It has a very
thorough test suite and good docs, and has seen usage in production a dependency
of ``django-ftl`` for a long time, but without many users.

We are not planning major backwards incompatible changes to the interface, but
we're not guaranteeing stability yet. Also, the nature of the library is such
that we expect most users will want to create their own wrappers anyway, which
you are encouraged to do, it order to be able to absorb any backwards
incompatible changes easily.

See the `issues list <https://github.com/django-ftl/fluent-compiler/issues>`_
for planned features.

Background
----------

This code was originally developed as part of ``fluent.runtime``, as an
alternative implementation of ``FluentBundle``, but never got merged to the
master branch. It has now been pulled out as a separate package.
