Release process
===============

* Tests, including flake8, isort and check-manifest

* Update CHANGELOG.rst, removing "(in development)" and adding date

* Update the version number, removing the ``-dev1`` part

  * setup.py
  * docs/conf.py

* Commit

* Release to PyPI::

    ./release.sh

* Tag the release e.g.::

    git tag v0.1.0

* Update the version numbers again, moving to the next release, and adding "-dev1"

* Add new section to HISTORY.rst

* ``git push --tags``
