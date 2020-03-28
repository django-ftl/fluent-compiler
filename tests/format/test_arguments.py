from __future__ import absolute_import, unicode_literals

import unittest

from fluent_compiler.bundle import FluentBundle
from fluent_compiler.errors import FluentReferenceError

from ..utils import dedent_ftl


class TestNumbersInValues(unittest.TestCase):
    def setUp(self):
        self.bundle = FluentBundle.from_string('en-US', dedent_ftl("""
            foo = Foo { $num }
            bar = { foo }
            baz =
                .attr = Baz Attribute { $num }
            qux = { "a" ->
               *[a]     Baz Variant A { $num }
             }
        """), use_isolating=False)

    def test_can_be_used_in_the_message_value(self):
        val, errs = self.bundle.format('foo', {'num': 3})
        self.assertEqual(val, 'Foo 3')
        self.assertEqual(errs, [])

    def test_can_be_used_in_the_message_value_which_is_referenced(self):
        val, errs = self.bundle.format('bar', {'num': 3})
        self.assertEqual(val, 'Foo 3')
        self.assertEqual(errs, [])

    def test_can_be_used_in_an_attribute(self):
        val, errs = self.bundle.format('baz.attr', {'num': 3})
        self.assertEqual(val, 'Baz Attribute 3')
        self.assertEqual(errs, [])

    def test_can_be_used_in_a_variant(self):
        val, errs = self.bundle.format('qux', {'num': 3})
        self.assertEqual(val, 'Baz Variant A 3')
        self.assertEqual(errs, [])


class TestStrings(unittest.TestCase):
    def setUp(self):
        self.bundle = FluentBundle.from_string('en-US', dedent_ftl("""
            foo = { $arg }
        """), use_isolating=True)

    def test_can_be_a_string(self):
        val, errs = self.bundle.format('foo', {'arg': 'Argument'})
        self.assertEqual(val, 'Argument')
        self.assertEqual(errs, [])


class TestMissing(unittest.TestCase):
    def setUp(self):
        self.bundle = FluentBundle.from_string('en-US', dedent_ftl("""
            foo = { $arg }
        """), use_isolating=True)

    def test_missing_with_empty_args_dict(self):
        val, errs = self.bundle.format('foo', {})
        self.assertEqual(val, 'arg')
        self.assertEqual(errs, [FluentReferenceError('<string>:2:9: Unknown external: arg')])

    def test_missing_with_no_args_dict(self):
        val, errs = self.bundle.format('foo')
        self.assertEqual(val, 'arg')
        self.assertEqual(errs, [FluentReferenceError('<string>:2:9: Unknown external: arg')])
