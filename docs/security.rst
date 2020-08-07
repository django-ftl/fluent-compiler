Security
--------

You should not pass untrusted FTL code to ``FluentBundle``. This is because
carefully constructed messages could potentially cause large resource usage (CPU
time and memory). The ``fluent.runtime`` implementation does have some
protection against these attacks, although it may not be foolproof, while
``fluent_compiler`` does not currently have any protection against these
attacks, either at compile time or run time.

We do protect against infinite loops caused by cycles in message references, but
that is not enough to protect against things like the `billion laughs attack
<https://en.wikipedia.org/wiki/Billion_laughs_attack>`_ which have no loops.

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
   implementation to reduce the possibility of cleverly crafted FTL code
   producing security holes, and ensure these techniques have full test
   coverage. These include:

   * `blacklisting sensitive functions
     <https://github.com/django-ftl/fluent-compiler/blob/7ad0597923b127ea5a70c04863bd3b9953d3aea3/src/fluent_compiler/codegen.py#L55>`_
     in our function call code generation.

   * doing many assertions in our `codegen module
     <https://github.com/django-ftl/fluent-compiler/blob/master/src/fluent_compiler/codegen.py>`_
     and not assuming the higher level compiler code is using it correctly.

   * being careful to avoid aliasing `builtins
     <https://github.com/django-ftl/fluent-compiler/blob/7ad0597923b127ea5a70c04863bd3b9953d3aea3/src/fluent_compiler/compiler.py#L261>`_
     and `keywords
     <https://github.com/django-ftl/fluent-compiler/blob/7ad0597923b127ea5a70c04863bd3b9953d3aea3/src/fluent_compiler/codegen.py#L170>`_
     in generated names, at multiple levels.
