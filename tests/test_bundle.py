# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

import traceback
import unittest

from fluent_compiler.bundle import FluentBundle, FtlResource
from fluent_compiler.errors import FluentDuplicateMessageId, FluentJunkFound, FluentReferenceError
from fluent_compiler.types import FluentNumber

from .utils import dedent_ftl


class TestFluentBundle(unittest.TestCase):
    def test_has_message(self):
        bundle = FluentBundle.from_string('en-US', dedent_ftl("""
            foo = Foo
            -term = Term
        """))

        self.assertTrue(bundle.has_message('foo'))
        self.assertFalse(bundle.has_message('bar'))

    def test_has_message_for_term(self):
        bundle = FluentBundle.from_string('en-US', dedent_ftl("""
            -foo = Foo
        """))

        self.assertFalse(bundle.has_message('-foo'))

    def test_has_message_with_attribute(self):
        bundle = FluentBundle.from_string('en-US', dedent_ftl("""
            foo = Foo
                .attr = Foo Attribute
        """))

        self.assertTrue(bundle.has_message('foo'))
        self.assertFalse(bundle.has_message('foo.attr'))
        self.assertFalse(bundle.has_message('foo.other-attribute'))

    def test_format_args(self):
        bundle = FluentBundle.from_string('en-US', 'foo = Foo')
        val, errs = bundle.format('foo')
        self.assertEqual(val, 'Foo')

        val, errs = bundle.format('foo', {})
        self.assertEqual(val, 'Foo')

    def test_format_missing(self):
        bundle = FluentBundle.from_string('en-US', '')
        self.assertRaises(LookupError,
                          bundle.format,
                          'a-missing-message')

    def test_format_term(self):
        bundle = FluentBundle.from_string('en-US', dedent_ftl("""
            -foo = Foo
        """))
        self.assertRaises(LookupError,
                          bundle.format,
                          '-foo')
        self.assertRaises(LookupError,
                          bundle.format,
                          'foo')

    def test_message_and_term_separate(self):
        bundle = FluentBundle.from_string('en-US', dedent_ftl("""
            foo = Refers to { -foo }
            -foo = Foo
        """))
        val, errs = bundle.format('foo', {})
        self.assertEqual(val, 'Refers to \u2068Foo\u2069')
        self.assertEqual(errs, [])

    def test_check_messages_duplicate(self):
        bundle = FluentBundle.from_string(
            'en-US',
            "foo = Foo\n"
            "foo = Bar\n")
        checks = bundle.check_messages()
        self.assertEqual(checks,
                         [('foo', FluentDuplicateMessageId("Additional definition for 'foo' discarded."))])
        # Earlier takes precedence
        self.assertEqual(bundle.format('foo')[0], 'Foo')

    def test_check_messages_junk(self):
        bundle = FluentBundle('en-US', [FtlResource("unfinished", filename='myfile.ftl')])
        checks = bundle.check_messages()
        self.assertEqual(len(checks), 1)
        check1_name, check1_error = checks[0]
        self.assertEqual(check1_name, None)
        self.assertEqual(type(check1_error), FluentJunkFound)
        self.assertEqual(check1_error.message, 'Junk found:\n  myfile.ftl:1:11: Expected token: "="')
        self.assertEqual(check1_error.annotations[0].message, 'Expected token: "="')

    def test_check_messages_compile_errors(self):
        bundle = FluentBundle('en-US', [FtlResource(dedent_ftl('''
        foo = { -missing }
            .bar = { -missing }
        '''), filename='myfile.ftl')])
        checks = bundle.check_messages()
        self.assertEqual(len(checks), 2)
        check1_name, check1_error = checks[0]
        self.assertEqual(check1_name, 'foo')
        self.assertEqual(type(check1_error), FluentReferenceError)
        self.assertEqual(check1_error.args[0], 'myfile.ftl:2:9: Unknown term: -missing')

        check2_name, check2_error = checks[1]
        self.assertEqual(check2_name, 'foo.bar')
        self.assertEqual(type(check2_error), FluentReferenceError)
        self.assertEqual(check2_error.args[0], 'myfile.ftl:3:14: Unknown term: -missing')

    def test_tracebacks_for_exceptions(self):
        bundle = FluentBundle('en-US', [
            FtlResource(dedent_ftl('''
            foo = { $arg }
            '''), filename='firstfile.ftl'),
            FtlResource(dedent_ftl('''

            bar = { $arg }
            '''), filename='secondfile.ftl')
        ])
        # Check what our tracebacks produce if we have an error. This is hard to
        # do, since we catch most errors, so we construct a special value that
        # will blow up despite our best efforts.

        class BadType(FluentNumber, int):
            def format(self, locale):
                1 / 0

        for filename, msg_id, line_number in [
                ("firstfile.ftl", "foo", 2),
                ("secondfile.ftl", "bar", 3)
        ]:
            try:
                val, errs = bundle.format(msg_id, {'arg': BadType(0)})
            except ZeroDivisionError:
                tb = traceback.format_exc()
                # We don't get line numbers, but we can at least display the
                # source FTL file and function name
                self.assertIn('File "{0}", line {1}, in {2}'.format(filename, line_number, msg_id), tb)
            else:
                self.fail('Expected ZeroDivisionError')
