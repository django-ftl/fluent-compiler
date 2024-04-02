Release process
===============

* Tests, including linters

* Update CHANGELOG.rst, removing "(in development)" and adding date

* Update the version number, removing the ``-dev1`` part

  * src/fluent_compiler/__init__.py
  * docs/conf.py

* Commit

* Release to PyPI::

    ./release.sh

* Update the version numbers again, moving to the next release, and adding "-dev1"

* Add new section to HISTORY.rst
