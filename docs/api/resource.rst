fluent_compiler.resource
------------------------

.. currentmodule:: fluent_compiler.resource

.. class:: FtlResource(text, filename=None)

   Represents the contents and (optional) name of a FTL resource e.g. a
   ``messages.ftl`` file. If you are using
   :class:`~fluent_compiler.bundle.FluentBundle` you can often avoid using this
   directly by using the convenience methods on that class.

   The filename is optional and used only for error messages. You could use any
   convenient identifier (e.g. a URL). Without this identifier, however, it may
   be hard to locate the source of any generated errors - you will get a line
   and column number, but not a filename!

   There are two convenience constructors:

   .. method:: from_string(text)
      :classmethod:

      Create an ``FtlResource`` from FTL source text.

   .. method:: from_file(filename, encoding='utf-8')
      :classmethod:

      Create an ``FtlResource`` from a filename, by opening and reading the
      file. UTF-8 encoding is assumed, but can be overridden.
