from __future__ import absolute_import, unicode_literals

import unittest

from fluent_compiler.bundle import FluentBundle
from fluent_compiler.errors import FluentReferenceError

from ..utils import dedent_ftl


class TestAttributesWithStringValues(unittest.TestCase):

    def setUp(self):
        self.bundle = FluentBundle.from_string('en-US', dedent_ftl("""
            foo = Foo
                .attr = Foo Attribute
            bar = { foo } Bar
                .attr = Bar Attribute
            ref-foo = { foo.attr }
            ref-bar = { bar.attr }
        """), use_isolating=True)

    def test_can_be_referenced_for_entities_with_string_values(self):
        val, errs = self.bundle.format('ref-foo', {})
        self.assertEqual(val, 'Foo Attribute')
        self.assertEqual(errs, [])

    def test_can_be_referenced_for_entities_with_pattern_values(self):
        val, errs = self.bundle.format('ref-bar', {})
        self.assertEqual(val, 'Bar Attribute')
        self.assertEqual(errs, [])

    def test_can_be_formatted_directly_for_entities_with_string_values(self):
        val, errs = self.bundle.format('foo.attr', {})
        self.assertEqual(val, 'Foo Attribute')
        self.assertEqual(errs, [])

    def test_can_be_formatted_directly_for_entities_with_pattern_values(self):
        val, errs = self.bundle.format('bar.attr', {})
        self.assertEqual(val, 'Bar Attribute')
        self.assertEqual(errs, [])


class TestAttributesWithSimplePatternValues(unittest.TestCase):

    def setUp(self):
        self.bundle = FluentBundle.from_string('en-US', dedent_ftl("""
            foo = Foo
            bar = Bar
                .attr = { foo } Attribute
            baz = { foo } Baz
                .attr = { foo } Attribute
            qux = Qux
                .attr = { qux } Attribute
            ref-bar = { bar.attr }
            ref-baz = { baz.attr }
            ref-qux = { qux.attr }
        """), use_isolating=False)

    def test_can_be_referenced_for_entities_with_string_values(self):
        val, errs = self.bundle.format('ref-bar', {})
        self.assertEqual(val, 'Foo Attribute')
        self.assertEqual(errs, [])

    def test_can_be_formatted_directly_for_entities_with_string_values(self):
        val, errs = self.bundle.format('bar.attr', {})
        self.assertEqual(val, 'Foo Attribute')
        self.assertEqual(errs, [])

    def test_can_be_referenced_for_entities_with_pattern_values(self):
        val, errs = self.bundle.format('ref-baz', {})
        self.assertEqual(val, 'Foo Attribute')
        self.assertEqual(errs, [])

    def test_can_be_formatted_directly_for_entities_with_pattern_values(self):
        val, errs = self.bundle.format('baz.attr', {})
        self.assertEqual(val, 'Foo Attribute')
        self.assertEqual(errs, [])

    def test_works_with_self_references(self):
        val, errs = self.bundle.format('ref-qux', {})
        self.assertEqual(val, 'Qux Attribute')
        self.assertEqual(errs, [])

    def test_works_with_self_references_direct(self):
        val, errs = self.bundle.format('qux.attr', {})
        self.assertEqual(val, 'Qux Attribute')
        self.assertEqual(errs, [])


class TestMissing(unittest.TestCase):
    def setUp(self):
        self.bundle = FluentBundle.from_string('en-US', dedent_ftl("""
            foo = Foo
            bar = Bar
                .attr = Bar Attribute
            baz = { foo } Baz
            qux = { foo } Qux
                .attr = Qux Attribute
            ref-foo = { foo.missing }
            ref-bar = { bar.missing }
            ref-baz = { baz.missing }
            ref-qux = { qux.missing }
            attr-only =
                     .attr  = Attr Only Attribute
            ref-double-missing = { missing.attr }
        """), use_isolating=False)

    def test_falls_back_for_msg_with_string_value_and_no_attributes(self):
        val, errs = self.bundle.format('ref-foo', {})
        self.assertEqual(val, 'Foo')
        self.assertEqual(errs,
                         [FluentReferenceError(
                             '<string>:8:13: Unknown attribute: foo.missing')])

    def test_falls_back_for_msg_with_string_value_and_other_attributes(self):
        val, errs = self.bundle.format('ref-bar', {})
        self.assertEqual(val, 'Bar')
        self.assertEqual(errs,
                         [FluentReferenceError(
                             '<string>:9:13: Unknown attribute: bar.missing')])

    def test_falls_back_for_msg_with_pattern_value_and_no_attributes(self):
        val, errs = self.bundle.format('ref-baz', {})
        self.assertEqual(val, 'Foo Baz')
        self.assertEqual(errs,
                         [FluentReferenceError(
                             '<string>:10:13: Unknown attribute: baz.missing')])

    def test_falls_back_for_msg_with_pattern_value_and_other_attributes(self):
        val, errs = self.bundle.format('ref-qux', {})
        self.assertEqual(val, 'Foo Qux')
        self.assertEqual(errs,
                         [FluentReferenceError(
                             '<string>:11:13: Unknown attribute: qux.missing')])

    def test_attr_only_main(self):
        # For reference, Javascript implementation returns null for this case.
        # For Python returning `None` doesn't seem appropriate, since this will
        # only blow up later if you attempt to add this to a string, so we raise
        # a LookupError instead, as per entirely missing messages.
        self.assertRaises(LookupError, self.bundle.format, 'attr-only', {})

    def test_attr_only_attribute(self):
        val, errs = self.bundle.format('attr-only.attr', {})
        self.assertEqual(val, 'Attr Only Attribute')
        self.assertEqual(errs, [])

    def test_missing_message_and_attribute(self):
        val, errs = self.bundle.format('ref-double-missing', {})
        self.assertEqual(val, 'missing.attr')
        self.assertEqual(errs, [FluentReferenceError('<string>:14:24: Unknown attribute: missing.attr')])
