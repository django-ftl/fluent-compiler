Contributing to fluent-compiler
===============================

Issues
------

You can help by filing bugs on GitHub:
https://github.com/django-ftl/fluent-compiler/issues.

Please check existing issues before filing a new one.


Development environment
-----------------------

To contribute fixes and features, you'll need to get set up for
development:

1. Fork ``fluent_compiler`` on GitHub.
2. Clone and go to the forked repository.
3. Set up a venv for development. We use `uv <https://docs.astral.sh/uv/>`_ and
   recommend you do the same. With uv, the setup instructions are::

     uv sync

  This will use your default Python version. If you want to use a different
  Python version, instead of the above do this e.g.::

     uv python install 3.10
     uv venv --python 3.10
     uv sync

4. Run the tests::

     pytest

If all that is successful, you are in good shape to start developing!

We also have several linters and code formatters that we require use of,
including `ruff <https://github.com/astral-sh/ruff>`_ and `black
<https://github.com/psf/black>`_. These are most easily added by using
`pre-commit <https://pre-commit.com/>`_:

* Do ``pre-commit install`` in the repo.

Now all the linters will run when you commit changes.

To run tests on multiple Python versions locally you can also use ``tox``.


Fixes and features
------------------

Please submit fixes and features by:

1. First creating a branch for your changes.
2. Sending us a PR on GitHub.

For new features it is often better to open an issue first to see if we
agree that the feature is a good idea, before spending a lot of time
implementing it.
