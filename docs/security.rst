Security
--------

You should not pass un-trusted FTL code to ``FluentBundle.add_messages``. This
is because carefully constructed messages could potentially cause large resource
usage (CPU time and memory). The ``fluent.runtime`` implementation does have
some protection against these attacks, although it may not be foolproof, while
``fluent_compiler`` does not have any protection against these attacks, either
at compile time or run time.

``fluent_compiler`` works by compiling FTL messages to Python `ast
<https://docs.python.org/3/library/ast.html>`_, which is passed to `compile
<https://docs.python.org/3/library/functions.html#compile>`_ and then `exec
<https://docs.python.org/3/library/functions.html#exec>`_. The use of ``exec``
like this is an established technique for high performance Python code, used in
template engines like Mako, Jinja2 and Genshi.

However, there can understandably be some concerns around the use of ``exec``
which can open up remote execution vulnerabilities. If this is of paramount
concern to you, you should consider using ``fluent.runtime`` instead.

To reduce the possibility of our use of ``exec`` harbouring security issues, the
following things are in place:

1. We generate `ast <https://docs.python.org/3/library/ast.html>`_ objects and
   not strings. This greatly reduces the security problems, since there is no
   possibility of a vulnerability due to incorrect string interpolation.

2. We use ``exec`` only on AST derived from FTL files, never on "end user input"
   (such as the arguments passed into ``FluentBundle.format``). This reduces the
   attack vector to only the situation where the source of your FTL files is
   potentially malicious or compromised.

3. We employ defence-in-depth techniques in our code generation and compiler
   implementation to reduce the possibility of a cleverly crafted FTL code
   producing security holes, and ensure these techniques have full test
   coverage.
