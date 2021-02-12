fluent-compiler
===============

.. image:: https://badge.fury.io/py/fluent-compiler.svg
    :target: https://badge.fury.io/py/fluent-compiler

.. image:: https://readthedocs.org/projects/fluent-compiler/badge/?version=latest&style=flat
    :target: https://fluent-compiler.readthedocs.io

.. image:: https://github.com/django-ftl/fluent-compiler/workflows/Python%20package/badge.svg
    :target: https://github.com/django-ftl/fluent-compiler/actions?query=workflow%3A%22Python+package%22 

This is a Python implementation of `Project Fluent <https://www.projectfluent.org/>`_, a localization
framework designed to unleash the entire expressive power of natural
language translations.

It provides a different implementation from the official
`fluent.runtime <https://github.com/projectfluent/python-fluent>`_
implementation, distinguished mainly by:

- strategy: we compile FTL files to Python bytecode via AST and use ``exec`` (similar
  to the strategy used by projects like Mako, Jinja2 and Genshi).
- speed: as a result of the above, plus static analysis, we get blazing
  fast performance, even more so when combined with PyPy which can
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

See `history <https://fluent-compiler.readthedocs.io/en/latest/history.html>` for a CHANGELOG.

Status
------

The package should be considered a 'beta'/'release candidate'. It has a very
thorough test suite and good docs, and has seen usage in production as a dependency
of ``django-ftl`` for a long time, but without many users.

We are not planning major backwards incompatible changes to the interface, but
we're also not guaranteeing stability yet. Also, the nature of the library is such
that we expect most users will want to create their own wrappers anyway, which
you are encouraged to do, in order to be able to absorb any backwards
incompatible changes easily.

See the `issues list <https://github.com/django-ftl/fluent-compiler/issues>`_
for planned features, and `CONTRIBUTING.rst <CONTRIBUTING.rst>`_ for information
about how to contribute.

Background
----------

This code was originally developed as part of ``fluent.runtime``, as an
alternative implementation of ``FluentBundle``, but never got merged to the
master branch. It has now been pulled out as a separate package. This is why
the repo's history contains `fluent.syntax` and early versions of `fluent.runtime`,
but the parts that are left in this repo all derive from the original version
of `fluent.runtime` contributed by @spookylukey from `a540993a085e36a9679e12f1ee7317ddc1ece5ad <https://github.com/django-ftl/fluent-compiler/commit/a540993a085e36a9679e12f1ee7317ddc1ece5ad>`_ onwards and the new compiler implementation in `d1481d61e0bc1a28a228a4b6d5258350d436e765 <https://github.com/django-ftl/fluent-compiler/commit/d1481d61e0bc1a28a228a4b6d5258350d436e765>`_ (which is squashed version of work done over a much longer period). Thats why
we also `corrected <https://github.com/django-ftl/fluent-compiler/commit/33c1b5b586858132d3ab7af749c2bde1bb5205b5>`_ 
the copyright notice from Mozilla to Luke Plant.
