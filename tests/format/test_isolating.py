from __future__ import absolute_import, unicode_literals

import unittest

from fluent_compiler.bundle import FluentBundle

from ..utils import dedent_ftl

# Unicode bidi isolation characters.
FSI = '\u2068'
PDI = '\u2069'


class TestUseIsolating(unittest.TestCase):

    def setUp(self):
        self.bundle = FluentBundle.from_string('en-US', dedent_ftl("""
            foo = Foo
            bar = { foo } Bar
            baz = { $arg } Baz
            qux = { bar } { baz }
        """))

    def test_isolates_interpolated_message_references(self):
        val, errs = self.bundle.format('bar', {})
        self.assertEqual(val, FSI + "Foo" + PDI + " Bar")
        self.assertEqual(errs, [])

    def test_isolates_interpolated_string_typed_variable_references(self):
        val, errs = self.bundle.format('baz', {'arg': 'Arg'})
        self.assertEqual(val, FSI + "Arg" + PDI + " Baz")
        self.assertEqual(errs, [])

    def test_isolates_interpolated_number_typed_variable_references(self):
        val, errs = self.bundle.format('baz', {'arg': 1})
        self.assertEqual(val, FSI + "1" + PDI + " Baz")
        self.assertEqual(errs, [])

    def test_isolates_complex_interpolations(self):
        val, errs = self.bundle.format('qux', {'arg': 'Arg'})
        expected_bar = FSI + FSI + "Foo" + PDI + " Bar" + PDI
        expected_baz = FSI + FSI + "Arg" + PDI + " Baz" + PDI
        self.assertEqual(val, expected_bar + " " + expected_baz)
        self.assertEqual(errs, [])


class TestSkipIsolating(unittest.TestCase):

    def setUp(self):
        self.bundle = FluentBundle.from_string('en-US', dedent_ftl("""
            -brand-short-name = Amaya
            foo = { -brand-short-name }
            with-arg = { $arg }
        """))

    def test_skip_isolating_chars_if_just_one_message_ref(self):
        val, errs = self.bundle.format('foo', {})
        self.assertEqual(val, 'Amaya')
        self.assertEqual(errs, [])

    def test_skip_isolating_chars_if_just_one_placeable_arg(self):
        val, errs = self.bundle.format('with-arg', {'arg': 'Arg'})
        self.assertEqual(val, 'Arg')
        self.assertEqual(errs, [])
