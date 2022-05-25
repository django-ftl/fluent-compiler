#!/bin/sh

set -x

check-manifest || exit 1
pytest || exit 1


umask 000
rm -rf build dist
git ls-tree --full-tree --name-only -r HEAD | xargs chmod ugo+r
find src docs tests -type d | xargs chmod ugo+rx

./setup.py sdist || exit 1

python3 setup.py bdist_wheel --python-tag=py3 || exit 1

VERSION=$(./setup.py --version) || exit 1
twine upload dist/fluent_compiler-$VERSION.tar.gz dist/fluent_compiler-$VERSION-py3-none-any.whl || exit 1
