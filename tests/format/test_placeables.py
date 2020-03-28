from __future__ import absolute_import, unicode_literals

import unittest

from fluent_compiler.bundle import FluentBundle
from fluent_compiler.errors import FluentCyclicReferenceError, FluentReferenceError

from ..utils import dedent_ftl


class TestPlaceables(unittest.TestCase):
    def setUp(self):
        self.bundle = FluentBundle.from_string('en-US', dedent_ftl("""
            message = Message
                    .attr = Message Attribute
            -term = Term
                  .attr = Term Attribute
            -term2 = {
               *[variant1] Term Variant 1
                [variant2] Term Variant 2
             }

            uses-message = { message }
            uses-message-attr = { message.attr }
            uses-term = { -term }

            bad-message-ref = Text { not-a-message }
            bad-message-attr-ref = Text { message.not-an-attr }
            bad-term-ref = Text { -not-a-term }

            self-referencing-message = Text { self-referencing-message }
            cyclic-msg1 = Text1 { cyclic-msg2 }
            cyclic-msg2 = Text2 { cyclic-msg1 }
            self-cyclic-message = Parent { self-cyclic-message.attr }
                                .attr = Attribute { self-cyclic-message }

            self-attribute-ref-ok = Parent { self-attribute-ref-ok.attr }
                                  .attr = Attribute
            self-parent-ref-ok = Parent
                               .attr =  Attribute { self-parent-ref-ok }
            -cyclic-term = { -cyclic-term }
            cyclic-term-message = { -cyclic-term }
        """), use_isolating=False)

    def test_placeable_message(self):
        val, errs = self.bundle.format('uses-message', {})
        self.assertEqual(val, 'Message')
        self.assertEqual(errs, [])

    def test_placeable_message_attr(self):
        val, errs = self.bundle.format('uses-message-attr', {})
        self.assertEqual(val, 'Message Attribute')
        self.assertEqual(errs, [])

    def test_placeable_term(self):
        val, errs = self.bundle.format('uses-term', {})
        self.assertEqual(val, 'Term')
        self.assertEqual(errs, [])

    def test_placeable_bad_message(self):
        val, errs = self.bundle.format('bad-message-ref', {})
        self.assertEqual(val, 'Text not-a-message')
        self.assertEqual(len(errs), 1)
        self.assertEqual(
            errs,
            [FluentReferenceError("<string>:15:26: Unknown message: not-a-message")])

    def test_placeable_bad_message_attr(self):
        val, errs = self.bundle.format('bad-message-attr-ref', {})
        self.assertEqual(val, 'Text Message')
        self.assertEqual(len(errs), 1)
        self.assertEqual(
            errs,
            [FluentReferenceError("<string>:16:31: Unknown attribute: message.not-an-attr")])

    def test_placeable_bad_term(self):
        val, errs = self.bundle.format('bad-term-ref', {})
        self.assertEqual(val, 'Text -not-a-term')
        self.assertEqual(len(errs), 1)
        self.assertEqual(
            errs,
            [FluentReferenceError("<string>:17:23: Unknown term: -not-a-term")])

    def test_cycle_detection(self):
        val, errs = self.bundle.format('self-referencing-message', {})
        self.assertIn('???', val)
        self.assertEqual(len(errs), 1)
        self.assertEqual(type(errs[0]), FluentCyclicReferenceError)

    def test_mutual_cycle_detection(self):
        val, errs = self.bundle.format('cyclic-msg1', {})
        self.assertIn('???', val)
        self.assertEqual(len(errs), 1)
        self.assertEqual(type(errs[0]), FluentCyclicReferenceError)

    def test_term_cycle_detection(self):
        val, errs = self.bundle.format('cyclic-term-message', {})
        self.assertIn('???', val)
        self.assertEqual(len(errs), 1)
        self.assertEqual(type(errs[0]), FluentCyclicReferenceError)

    def test_allowed_self_reference(self):
        val, errs = self.bundle.format('self-attribute-ref-ok', {})
        self.assertEqual(val, 'Parent Attribute')
        self.assertEqual(errs, [])
        val, errs = self.bundle.format('self-parent-ref-ok.attr', {})
        self.assertEqual(val, 'Attribute Parent')
        self.assertEqual(errs, [])


class TestSingleElementPattern(unittest.TestCase):
    def test_single_literal_number_isolating(self):
        bundle = FluentBundle.from_string('en-US', 'foo = { 1 }', use_isolating=True)
        val, errs = bundle.format('foo')
        self.assertEqual(val, '1')
        self.assertEqual(errs, [])

    def test_single_literal_number_non_isolating(self):
        bundle = FluentBundle.from_string('en-US', 'foo = { 1 }', use_isolating=False)
        val, errs = bundle.format('foo')
        self.assertEqual(val, '1')
        self.assertEqual(errs, [])

    def test_single_arg_number_isolating(self):
        bundle = FluentBundle.from_string('en-US', 'foo = { $arg }', use_isolating=True)
        val, errs = bundle.format('foo', {'arg': 1})
        self.assertEqual(val, '1')
        self.assertEqual(errs, [])

    def test_single_arg_number_non_isolating(self):
        bundle = FluentBundle.from_string('en-US', 'foo = { $arg }', use_isolating=False)
        val, errs = bundle.format('foo', {'arg': 1})
        self.assertEqual(val, '1')
        self.assertEqual(errs, [])

    def test_single_arg_missing_isolating(self):
        bundle = FluentBundle.from_string('en-US', 'foo = { $arg }', use_isolating=True)
        val, errs = bundle.format('foo')
        self.assertEqual(val, 'arg')
        self.assertEqual(len(errs), 1)

    def test_single_arg_missing_non_isolating(self):
        bundle = FluentBundle.from_string('en-US', 'foo = { $arg }', use_isolating=True)
        val, errs = bundle.format('foo')
        self.assertEqual(val, 'arg')
        self.assertEqual(len(errs), 1)
