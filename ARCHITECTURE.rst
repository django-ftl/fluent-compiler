Architecture of fluent-compiler
-------------------------------

The following is a brief, very high-level overview of what fluent-compiler does
and the various layers.

Our basic strategy is that we take an FTL file like this::

   hello-user = Hello { $username }!

   welcome = { hello-user } Welcome to { -app-name }.

   -app-name = Acme CMS


and compile it to Python functions, something roughly like this:

.. code-block:: python

   def hello_user(args, errors):
       try:
           username = args['username']
       except KeyError:
           username = "username"
           errors.append(FluentReferenceError("Unknown external: username"))
       return f"Hello {username}"


   def welcome(args, errors):
       return f"{hello_user(args, errors)} Welcome to Acme CMS."


We then need to store these message functions in some dictionary-like object,
to allow us to call them.

.. code-block:: python

   message_functions = {
       'hello-user': hello_user,
       'welcome': welcome,
   }

To actually format a message we have to do something like:

.. code-block:: python

   errors = []
   formatted_message = message_functions['hello-user']({'username': 'guest'}, errors)
   return formatted_message, errors

Note a few things:

* Each message becomes a Python function.
* Message references are handled by calling other message functions.
* We do lots of optimizations at compile time to heavily simplify the
  expressions that are evaluated at runtime, including things like inlining
  terms.
* We have to handle possible errors in accordance with the Fluent philosophy.
  Where possible we detect errors at compile time, in addition to the runtime
  handling shown above.

We do not, in fact, generate Python code as a string, but instead generate AST
which we can convert to executable Python functions using the builtin functions
`compile <https://docs.python.org/3/library/functions.html#compile>`__ and `exec
<https://docs.python.org/3/library/functions.html#exec>`_.

Layers
~~~~~~

The highest level code, which can be used as an entry point by users, is in
``fluent_compiler.bundle``. The interface provided here, however, is meant
mainly for demonstration purposes, since it is expected that in many
circumstances the next level down will be used. For example, `django-ftl
<https://github.com/django-ftl/django-ftl>`_ by-passes this module and uses the
next layer down.

The next layer is ``fluent_compiler.compiler``, which handles actual
compilation, converting FTL expressions (i.e. FTL AST nodes) into Python code.
The bulk of the FTL specific logic is found here. See especially the comments
on ``compile_expr``.

For generating Python code, it uses the classes provided by the
``fluent_compiler.codegen`` module. These are simplified versions of various
Python constructs, with an interface that makes it easy for the ``compiler``
module to construct correct code without worrying about lower level details.

The classes in the ``codegen`` module eventually need to produce AST objects
that can be passed to Python’s builtin `compile
<https://docs.python.org/3/library/functions.html?highlight=compile#compile>`__
function. The stdlib `ast <https://docs.python.org/3/library/ast.html>`_ module
has incompatible differences between different Python versions, so we abstract
over these in ``fluent_compiler.ast_compat`` which allows the ``codegen`` module
to almost entirely ignore the differences in AST for different Python.

In addition to these modules, there are some runtime functions and types that
are needed by the generated Python code, found in ``fluent_compiler.runtime``.

The ``fluent_compiler.types`` module contains types for handling number/date
formatting - these are used directly by users of ``fluent_compiler``, as well as
internally for implementing things like the ``NUMBER`` and ``DATETIME`` builtin
FTL functions.

Other related level classes for the user are provided in
``fluent_compiler.resource`` and ``fluent_compiler.escapers``.

Tests
~~~~~

The highest level tests are in ``tests/format/``. These are essentially
functional tests that ensure we produce correct output at runtime.

In addition we have many tests of the lower layers of code. These include
a lot of tests for our optimizations, many of which work at the level of
examining the generated Python code.

We also have benchmarking tests in ``tools``.
