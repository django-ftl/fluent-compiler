Contributing to fluent_compiler
===============================

Issues
------

You can help by filing bugs on GitHub: https://github.com/django-ftl/fluent-compiler/issues

Please check existing issues before filing a new one.

Development environment
-----------------------

To contribute fixes and features, you'll need to get set up for development:

1. For ``fluent_compiler`` on github
2. Checkout a copy of the project using
3. Create a virtualenv for development (or your preferred mechanism
   for isolated Python environments)
4. Install the package in development mode::

     ./setup.py develop

5. Install test requirements::

     pip install -r requirements-test.txt

6. Run the tests::

     ./runtests.py

If all that is successful, you are in good shape to start developing!

You can also run tests with pytest::

  pip install pytest
  pytest


Fixes and features
------------------

Please submit fixes and features by:

1. First creating a branch for your changes
2. Sending us a PR on GitHub

For new features it is often better to open an issue first to see if we agree
that the feature is a good idea, before spending a lot of time implementing it.

Architecture
------------

The following is a brief, very high-level overview of what fluent-compiler does
and the various layers.

Our basic strategy is that we take an FTL file like this:

.. code-block::

   hello-user = Hello { $username }!

   -app-name = Acme CMS

   welcome = { hello-user } Welcome to { -app-name }.


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

Note a few things:

* Each message becomes a Python function.
* Message references are handled by calling other message functions.
* We do lots of optimizations at compile time to heavily simplify the
  expressions that are evaluated at runtime.
* Term references are inlined for performance.
* We have to handle possible errors in accordance with the Fluent philosophy.
  Where possible we detect errors at compile time.

We do not, in fact, generate Python code as a string, but instead generate AST
which we can convert to executable Python functions using the builtin functions
`compile <https://docs.python.org/3/library/functions.html#compile>`_ and `exec
<https://docs.python.org/3/library/functions.html#exec>`_.

Layers
~~~~~~

The main module that handles compilation, converting FTL expressions (i.e. FTL
AST nodes) into Python code is ``fluent_compiler.compiler``.

For generating Python code, it uses the classes provided by the
``fluent_compiler.codegen`` module. These are simplified versions of various
Python constructs, with an interface that makes it easy for the ``compiler``
module to construct correct code without worrying about lower level details.

The classes in the ``codegen`` module eventually need to produce AST objects
that can be passed to the builtin ``compile`` function. The stdlib ``ast``
module has incompatible differences between different Python versions, so we
abstract over these in ``fluent_compiler.ast_compat`` which allows the
``codegen`` module to almost entirely ignore the differences in AST for
different Python.

In addition to these modules, there are some runtime functions and types that
are needed by the generated Python code, found in ``fluent_compiler.runtime``.

The ``fluent_compiler.types`` module contains types for handling number/date
formatting - these are used directly by users of ``fluent_compiler``, as well as
internally for implementing things like the ``NUMBER`` and ``DATETIME`` builtin
FTL functions.

Very high level classes for the end user are provided in
``fluent_compiler.bundle`` and ``fluent_compiler.resource``.

Tests
~~~~~

The highest level tests are in ``tests/format/``. These are essentially
integration tests that ensures we produce correct output at runtime.

In addition we have many tests of the lower layers of code. These include
a lot of tests for our optimizations, many of which work at the level of
examining the generated Python code.

We also have benchmarking tests in ``tools``.
