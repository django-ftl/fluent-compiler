fluent_compiler.compiler
------------------------

.. currentmodule:: fluent_compiler.compiler

This functions and classes documented for module represents the lower level
interface for compiling Fluent messages.

.. function:: compile_messages(locale, resources, use_isolating=True, functions=None, escapers=None)

   Compiles FTL resources to Python functions.

   :param locale:

      A BCP 47 locale string e.g. ``'en'``, ``'de-DE'``

   :param resources:

      A list of :class:`fluent_compiler.resource.FtlResource` objects containing
      the FTL to compile.

   :param use_isolating:

      An optional boolean indicating whether to use Unicode BDI isolation characters when
      interpolating external arguments, defaults to True.

   :param functions:

      An optional dictionary of custom functions to make available to Fluent messages.
      See :doc:`../functions` for more information.

   :param escapers:

      An optional list of escaper objects - see :doc:`../escaping` for more
      information.

   The return value is a :class:`CompiledFtl` object.

   The most basic usage would be:

   .. code-block:: python

      >>> compiled = compile_messages('en', FtlResource.from_string('''
      ... this-is-a-message = Hello, { $username }!
      ... ''')
      >>> errors = []
      >>> formatted_message = compiled.message_functions['this-is-a-message']({'user': 'Joe'}, errors)
      >>> formatted_message
      'Hello, Joe!'
      >>> errors
      []


.. class:: CompiledFtl

   .. attribute:: message_functions

      This is the most important part of `CompiledFtl`. It is a dictionary
      mapping each FTL message ID to a Python function.

      Messages with attributes are mapped to separate items in the dictionary,
      with the key being ``{message id}.{attr id}``. For example, this FTL file::

        my-message = Hello
                 .my-attr = Something

      will produce a dictionary with keys ``"my-message"`` and
      ``"my-message.my-attr"``.

      The contained Python functions have the following signature and pattern:

      .. code-block:: python

         def a_message(args, errors):
             return "The message"

      Each function takes a dictionary of external arguments and an errors list
      as arguments.

      The return value is the formatted message.

      Errors that occur while formatting the message are returned by appending
      to the passed in list. These errors will normally be appropriate Python
      exceptions. For example, for this FTL::

        your-balance = Your balance is { NUMBER($balance, currencDisplay:"code") }

      (where ``currencDisplay`` is a typo for ``currencyDisplay``), since
      ``NUMBER`` is a function, we get a ``TypeError``:

      .. code-block:: python

         TypeError("NUMBER() got an unexpected keyword argument 'currencDisplay'")

      Note that these errors may have been detected at compile-time, in which case the
      generated message function directly creates and returns the error, rather than it
      being the result of a try/except block that catches a real exception.

      On the other hand some error, like missing external arguments, may only be
      detected at run-time. See also :doc:`../errors`.

   .. attribute:: errors

      A list of compile-time errors. Each item in the list is a 2-tuple::

        (message id, exception object)

      For syntax errors that produce 'junk' that can't be parsed, the message ID
      could be ``None``. We currently don't guarantee the exact types or
      interface of exception objects that are returned, but the repr of the
      object should contain enough information to find the problem.

      Note that errors do not stop compilation in general. See :doc:`../errors`
      for more information about how ``fluent-compiler`` handles errors.

   .. attribute:: locale

      The locale string passed to ``compile_messages``

      ``CompiledFtl`` may have other attributes, but they are not considered
      stable or part of the interface yet.
