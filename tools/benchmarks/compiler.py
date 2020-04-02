#!/usr/bin/env python

# Benchmarks for speed of compilation.

# This should be run using pytest, see end of file
from __future__ import unicode_literals

import os
import subprocess
import sys

from fluent_compiler.compiler import compile_messages
from fluent_compiler.resource import FtlResource

this_file = os.path.abspath(__file__)
this_dir = os.path.dirname(this_file)


def test_simple_message(benchmark):
    resources = [FtlResource('single-string-literal = Hello I am a single string literal')]
    benchmark(lambda: compile_messages('en', resources))


def test_term_inlining(benchmark):
    resources = [FtlResource("""
-my-brand = { $style ->
    *[lower]    foobar
     [upper]    FOOBAR
 }
my-message = This is a message from { -my-brand(style: "upper") }

""")]
    benchmark(lambda: compile_messages('en', resources))


def test_number_simplifying(benchmark):
    resources = [FtlResource("""
my-message = { NUMBER($count) ->
      [0]     None
      [1]     One
     *[other] NUMBER(NUMBER($count))
}
""")]
    benchmark(lambda: compile_messages('en', resources))


if __name__ == '__main__':
    # You can execute this file directly, and optionally add more py.test args
    # to the command line (e.g. -k for keyword matching certain tests).
    subprocess.check_call(["py.test", "--benchmark-warmup=on", "--benchmark-sort=name", this_file] + sys.argv[1:])
