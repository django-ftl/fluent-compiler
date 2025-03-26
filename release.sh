#!/bin/sh

set -x

pytest || exit 1


umask 000
rm -rf build dist
git ls-tree --full-tree --name-only -r HEAD | xargs chmod ugo+r
find src docs tests -type d | xargs chmod ugo+rx

uv build --sdist --wheel || exit 1
uv publish  || exit 1

VERSION=$(uv pip show fluent-compiler | grep 'Version: ' | cut -f 2 -d ' ' | tr -d '\n') || exit 1

git tag $VERSION || exit 1
git push || exit 1
git push --tags || exit 1
