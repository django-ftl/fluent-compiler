fluent_compiler.bundle
----------------------

.. currentmodule:: fluent_compiler.bundle

.. class:: FluentBundle(locale, resources, use_isolating=True, functions=None, escapers=None)

   A bundle of compiled FTL resources for a specific locale, ready to format
   messages.

   :param locale:

      A BCP 47 locale string e.g. ``'en'``, ``'de-DE'``

   :param resources:

      A list of :class:`fluent_compiler.resource.FtlResource` objects containing
      the FTL to compile. See :meth:`from_string` and :meth:`from_files` for
      convenient alternative constructors.

   The remainder of the parameters are the same as for
   :func:`~fluent_compiler.compiler.compile_messages`.

   .. method:: from_string(locale, text, use_isolation=True, functions=None, escapers=None)
      :classmethod:

      Create a bundle from FTL text. This is convenience constructor to avoid
      having to create a :class:`~fluent_compiler.resource.FtlResource`
      manually.

   .. method:: from_files(locale, filenames, use_isolation=True, functions=None, escapers=None)
      :classmethod:

      Create a bundle from a list of FTL filenames. This is convenience
      constructor to avoid having to create a
      :class:`~fluent_compiler.resource.FtlResource` manually.

   .. method:: format(message_id, args=None)

      Generates a translation of the message specified by the message ID,
      returning the formatted message and list of formatting errors, as per
      :attr:`fluent_compiler.compiler.CompiledFtl.message_functions` docs.

      ``message_id`` can be a string like ``my-message-id``, and attributes can
      be referred to using dot notation like ``my-message-id.my-attributes``.

      ``args`` is an optional dictionary of parameters for the message. These
      can be strings, numbers or date/datetimes, as described in :ref:`formatting-messages`.

      Example:

      .. code-block::

         >>> bundle = FluentBundle.from_string('en', '''
         ... hello-user = Hello, { $username }!
         ... ''')
         >>> value, errors = bundle.format('hello-user', {'username': 'Jane'})
         >>> val
         "Hello, Jane!"
         >>> errors
         []

      See :attr:`~fluent_compiler.compiler.CompiledFtl.errors` for a description
      of the returned errors list.

   .. method:: check_messages()

      Returns a list of compilation errors, as per
      :attr:`fluent_compiler.compiler.CompiledFtl.errors`.
