Other implementations and comparisons
=====================================

``fluent.runtime`` 0.1 also has an implementation of ``FluentBundle``, which
implements an interpreter for the FTL Abstract Syntax Tree.

``fluent_compiler``, by contrast, works by compiling a set of FTL messages to a
set of Python functions using Python `ast
<https://docs.python.org/3/library/ast.html>`_. This results in very good
performance (see below for more info).

There are some differences to note:

* ``fluent.runtime``has some protection against malicious FTL input which could
  attempt things like a `billion laughs attack
  <https://en.wikipedia.org/wiki/Billion_laughs_attack>`_ to consume a large
  amount of memory or CPU time. For the sake of performance,
  ``fluent_compiler`` does not have these protections.

  It should be noted that both implementations are able to detect and stop
  infinite recursion errors (``fluent_compiler`` does this at compile time),
  which is important to stop infinite loops and memory exhaustion which could
  otherwise occur due to accidental cyclic references in messages.

* While the error handling strategy for both implementations is the same, when
  errors occur (e.g. a missing value in the arguments dictionary, or a cyclic
  reference, or a string is passed to ``NUMBER()`` builtin), the exact errors
  returned by ``format`` may be different between the two implementations.

  Also, when an error occurs, in some cases (such as a cyclic reference), the
  error string embedded into the returned formatted message may be different.
  For cases where there is no error, the output is identical (or should be).

* ``fluent_compiler`` includes support for :doc:`escaping`.

* ``fluent_compiler`` has does additional checking on for custom functions (see
  :doc:`functions`).

Performance
-----------

Due to the strategy of compiling to Python, ``fluent_compiler`` has very good
performance, especially for the simple common cases. The
``tools/benchmark/gettext_comparisons.py`` script includes some benchmarks that
compare speed to GNU gettext as a reference. Below is a rough summary:

For the simple but very common case of a message defining a static string,
``FluentBundle.format`` is very close to GNU gettext, or much faster,
depending on whether you are using Python 2 or 3, and your Python implementation
(e.g. CPython or PyPy). (The worst case we found was 5% faster than gettext on
CPython 2.7, and the best case was about 3.5 times faster for PyPy2 5.1.2). For
cases of substituting a single string into a message,
``FluentBundle.format`` is between 30% slower and 70% faster than an
equivalent implementation using GNU gettext and Python ``%`` interpolation.

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

The ``FluentBundle`` implementation from ``fluent.runtime`` is much slower tham
the one in ``fluent_compiler``, often by a factor of 10, as you would expect. In
cases where there are a large number of messages, ``fluent_compiler`` will be a
slower to format the first message because it first compiles all the messages,
whereas ``fluent.runtime`` does not have this compilation step, and tries to
reduce any up-front work to a minimum (sometimes at the cost of runtime
performance).
