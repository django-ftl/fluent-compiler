#!/usr/bin/env python

# This should be run using pytest, see end of file
from __future__ import unicode_literals

import subprocess
import sys
import os


from fluent_compiler import FluentBundle

this_file = os.path.abspath(__file__)
this_dir = os.path.dirname(this_file)


def test_simple_message(benchmark):
    b = FluentBundle(['en'])
    b.add_messages("""
single-string-literal = Hello I am a single string literal in Polish
""")
    benchmark(b._compile)


def test_term_inlining(benchmark):
    b = FluentBundle(['en'])
    b.add_messages("""
-my-brand = { $style ->
    *[lower]    foobar
     [upper]    FOOBAR
 }
my-message = This is a message from { -my-brand(style: "upper") }

""")
    benchmark(b._compile)


def test_number_simplifying(benchmark):
    b = FluentBundle(['en'])
    b.add_messages("""
my-message = { NUMBER($count) ->
      [0]     None
      [1]     One
     *[other] NUMBER(NUMBER($count))
}
""")
    benchmark(b._compile)


if __name__ == '__main__':
    # You can execute this file directly, and optionally add more py.test args
    # to the command line (e.g. -k for keyword matching certain tests).
    subprocess.check_call(["py.test", "--benchmark-warmup=on", "--benchmark-sort=name", this_file] + sys.argv[1:])
