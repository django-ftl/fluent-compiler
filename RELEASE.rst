Release process
===============

* Tests, including linters and check-manifest

* Update CHANGELOG.rst, removing "(in development)" and adding date

* Update the version number, removing the ``-dev1`` part

  * src/fluent_compiler/__init__.py
  * docs/conf.py

* Commit

* Release to PyPI::

    ./release.sh

* Tag the release e.g.::

    git tag v0.3

* Update the version numbers again, moving to the next release, and adding "-dev1"

* Add new section to HISTORY.rst

* ``git push --tags``
