Changelog
=========

fluent_compiler 1.2 (unreleased)
--------------------------------

* Dropped Python 3.7 support
* Compiler performance improvements - thanks `@leamingrad <https://github.com/leamingrad>`_.
* Switched from `attrs <https://www.attrs.org/en/stable/index.html>`_ to stdlib
  `dataclasses <https://docs.python.org/3/library/dataclasses.html>`_, and added
  lots of type signatures and cleaned up internally.
  * The documented API is still exactly the same as it was. However, if you were
    depending on implementation details, like the fact that ``CompiledFtl`` was
    an attrs dataclass when it is now a stdlib dataclass, there may be some
    small backwards incompatibilities. In addition if you are running a type
    checker, you may notice some differences as more things will be checked.

fluent_compiler 1.1 (2024-04-02)
--------------------------------

* Fixed crasher with variable re-use when looking up the same argument more than
  once. Thanks @ggindinson for bug report and PR.
* Dropped Python 3.6 support

fluent_compiler 1.0 (2023-04-18)
--------------------------------

* Tested against latest Python 3.11, and 3.12 alpha

fluent_compiler 0.4 (2023-02-16)
--------------------------------

* Dropped support for Python 2.7 and Python < 3.6
* Lots of code style cleanups using black etc.
* Compiler actually respects documented ``use_isolating`` attribute of escapers

fluent_compiler 0.3 (2020-11-18)
--------------------------------

* Fixed test suite on Python 3.8
* Performance improvements
* Made ``fluent_number`` obey format specifiers for currencies

fluent_compiler 0.2 (2020-04-02)
--------------------------------
* New :class:`fluent_compiler.bundle.FluentBundle` API - **backwards
  incompatible**. In this release, we are diverging from the ``fluent.runtime``
  0.1 interface to make something that better suits both our implementation and
  our target audience to come up with better APIs. The changes are especially
  driven by the needs of the ``django-ftl`` package, without being tied to
  Django in any way.

  It should be relatively straightforward to convert. Instead of doing::

    bundle = FluentBundle(locale_list, options)
    bundle.add_messages(...)

  You now do::

     bundle = FluentBundle.from_string(locale, string)

  or::

     bundle = FluentBundle.from_files(locale, ['file1.ftl', 'file2.ftl'])

* New :func:`fluent_compiler.compiler.compile_messages` function which is
  slightly lower level than ``FluentBundle``.


fluent_compiler 0.1.1 (2020-03-24)
----------------------------------
* Small packaging improvements


fluent_compiler 0.1 (2020-03-22)
--------------------------------

* Separated this package off from a branch of ``fluent.runtime``
* First release to PyPI of ``fluent_compiler``.
* This release contains a ``FluentBundle`` implementation that can generate
  translations from FTL messages, compatible with ``FluentBundle`` from
  ``fluent.runtime`` 0.1.
* Targets the `Fluent 1.0 spec
  <https://github.com/projectfluent/fluent/releases/tag/v1.0.0>`_.
