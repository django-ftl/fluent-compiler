Other implementations and comparisons
=====================================

``fluent.runtime`` 0.1 also has an implementation of ``FluentBundle``, which
implements an interpreter for the FTL Abstract Syntax Tree.

``fluent_compiler``, by contrast, works by compiling a set of FTL messages to a
set of Python functions using Python `ast
<https://docs.python.org/3/library/ast.html>`_. This results in very good
performance (see below for more info).

There are some differences to note:

* Our usage API is different from that in ``fluent.runtime``.
  ``fluent_compiler`` 0.1 had a ``FluentBundle`` API compatible with
  ``fluent.runtime.FluentBundle`` 0.1, but after that point both APIs have
  changed in slightly different directions.

* ``fluent.runtime`` has some protection against malicious FTL input which could
  attempt things like a `billion laughs attack
  <https://en.wikipedia.org/wiki/Billion_laughs_attack>`_ to consume a large
  amount of memory or CPU time. For the sake of performance, ``fluent_compiler``
  does not have these protections.

  It should be noted that both implementations are able to detect and stop
  infinite recursion errors (``fluent_compiler`` does this at compile time),
  which is important to stop infinite loops and memory exhaustion which could
  otherwise occur due to accidental cyclic references in messages.

* ``fluent_compiler`` has the concept of compile-time static error checking,
  while ``fluent.runtime`` basically only has syntax and run-time checking. This
  allows us to report some errors earlier - although mostly the same types of
  errors will be reported.

* When errors occur (e.g. a missing value in the arguments dictionary, or a
  cyclic reference, or a string is passed to ``NUMBER()`` builtin), the exact
  errors returned by ``format`` may be different between the two
  implementations.

  Also, when an error occurs, in some cases (such as a cyclic reference), the
  error string embedded into the returned formatted message may be different.
  For cases where there is no error, the output is identical (or should be).

* ``fluent_compiler`` includes support for :doc:`escaping`.

* ``fluent_compiler`` does additional checking on custom functions (see
  :doc:`functions`) and has a more clearly defined error handling strategy for
  custom functions.

Performance
-----------

Due to the strategy of compiling to Python, along with some aggressive
optimizations, ``fluent_compiler`` has very good performance, especially for the
simple common cases. The ``tools/benchmark/runtime.py`` script includes some
benchmarks that compare speed to GNU gettext as a reference. Below is a rough
summary:

For the simple but very common case of a message defining a static string,
``FluentBundle.format`` is very close to GNU gettext, or much faster, depending
on your Python version and implementation (e.g. CPython or PyPy). (The worst
case we found was 7% slower than gettext on CPython 3.9, and the best case was
about 3.5 times faster for PyPy3.6 7.3.0). For cases of substituting a single
string into a message, ``FluentBundle.format`` was between 7% slower and 3.4
times faster than an equivalent implementation using GNU gettext and Python
``%`` interpolation.

For message where plural rules are involved, currently ``fluent_compiler``
can be significantly slower than using GNU gettext, partly because it uses
plural rules from CLDR that can be much more complex (and correct) than the ones
that gettext normally does. Further work could be done to optimize some of these
cases though.

For more complex operations (for example, using locale-aware date and number
formatting), formatting messages can take a lot longer. Comparisons to GNU
gettext fall down at this point, because it doesn't include a lot of this
functionality. However, usually these types of messages make up a small fraction
of the number of internationalized strings in an application.

Some of the advanced features of Fluent, such as `terms and parameterised terms
<https://projectfluent.org/fluent/guide/terms.html>`_, often come at zero
run-time penalty, because we are usually able to inline them and `entirely
compile these away to static strings
<https://github.com/django-ftl/fluent-compiler/blob/e62c1fad7cd6b0ecf3531a19e3fdff91e43bdf36/tests/test_compiler.py#L649>`_.
We're also careful with our generated code so that our advanced features such as
escaping add zero run-time cost if you are not using them.

The implementation in ``fluent.runtime`` is generally significantly slower than
the one in ``fluent_compiler``, although the performance of the former is
improving. In cases where there are a large number of messages,
``fluent_compiler`` will probably be slower to format the first message because
it first compiles all the messages, whereas ``fluent.runtime`` does not have
this compilation step, and tries to reduce any up-front work to a minimum
(sometimes at the cost of run-time performance).
