Changelog
=========

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
