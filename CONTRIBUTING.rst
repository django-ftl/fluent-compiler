Contributing to fluent-compiler
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

     pytest

If all that is successful, you are in good shape to start developing!

We also have several linters and code formatters that we require use of,
including `flake8 <http://flake8.pycqa.org/en/latest/>`_, `isort
<https://github.com/timothycrosley/isort#readme>`_ and `black
<https://github.com/psf/black>`_. These are most easily add by using `pre-commit
<https://pre-commit.com/>`_:

* Install pre-commit globally e.g. ``pipx install pre-commit`` if you already
  have `pipx <https://github.com/pypa/pipx>`_.

* Do ``pre-commit install`` in the repo.

Now all the linters will run when you commit changes.

To run tests on multiple Python versions locally you can also install and use
``tox``.


Fixes and features
------------------

Please submit fixes and features by:

1. First creating a branch for your changes
2. Sending us a PR on GitHub

For new features it is often better to open an issue first to see if we agree
that the feature is a good idea, before spending a lot of time implementing it.
