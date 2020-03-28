from __future__ import absolute_import, unicode_literals

import unittest

from fluent_compiler.bundle import FluentBundle
from fluent_compiler.errors import FluentReferenceError

from ..utils import dedent_ftl


class TestSelectExpressionWithStrings(unittest.TestCase):

    def test_with_a_matching_selector(self):
        bundle = FluentBundle.from_string('en-US', dedent_ftl("""
            foo = { "a" ->
                [a] A
               *[b] B
             }
        """))
        val, errs = bundle.format('foo', {})
        self.assertEqual(val, "A")
        self.assertEqual(errs, [])

    def test_with_a_non_matching_selector(self):
        bundle = FluentBundle.from_string('en-US', dedent_ftl("""
            foo = { "c" ->
                [a] A
               *[b] B
             }
        """))
        val, errs = bundle.format('foo', {})
        self.assertEqual(val, "B")
        self.assertEqual(errs, [])

    def test_with_a_missing_selector(self):
        bundle = FluentBundle.from_string('en-US', dedent_ftl("""
            foo = { $none ->
                [a] A
               *[b] B
             }
        """))
        val, errs = bundle.format('foo', {})
        self.assertEqual(val, "B")
        self.assertEqual(errs,
                         [FluentReferenceError("<string>:2:9: Unknown external: none")])

    def test_with_argument_expression(self):
        bundle = FluentBundle.from_string('en-US', dedent_ftl("""
            foo = { $arg ->
                [a] A
               *[b] B
             }
        """))
        val, errs = bundle.format('foo', {'arg': 'a'})
        self.assertEqual(val, "A")

    def test_string_selector_with_plural_categories(self):
        bundle = FluentBundle.from_string('en-US', dedent_ftl("""
            foo = { $arg ->
                [something] A
               *[other] B
             }
        """))
        # Even though 'other' matches a CLDR plural, this is not a plural
        # category match, and should work without errors when we pass
        # a string.

        val, errs = bundle.format('foo', {'arg': 'something'})
        self.assertEqual(val, "A")
        self.assertEqual(errs, [])

        val2, errs2 = bundle.format('foo', {'arg': 'other'})
        self.assertEqual(val2, "B")
        self.assertEqual(errs2, [])

        val3, errs3 = bundle.format('foo', {'arg': 'not listed'})
        self.assertEqual(val3, "B")
        self.assertEqual(errs3, [])


class TestSelectExpressionWithNumbers(unittest.TestCase):

    def setUp(self):
        self.bundle = FluentBundle.from_string('en-US', dedent_ftl("""
            foo = { 1 ->
               *[0] A
                [1] B
             }

            bar = { 2 ->
               *[0] A
                [1] B
             }

            baz = { $num ->
               *[0] A
                [1] B
             }

            qux = { 1.0 ->
               *[0] A
                [1] B
             }
        """), use_isolating=False)

    def test_selects_the_right_variant(self):
        val, errs = self.bundle.format('foo', {})
        self.assertEqual(val, "B")
        self.assertEqual(errs, [])

    def test_with_a_non_matching_selector(self):
        val, errs = self.bundle.format('bar', {})
        self.assertEqual(val, "A")
        self.assertEqual(errs, [])

    def test_with_a_missing_selector(self):
        val, errs = self.bundle.format('baz', {})
        self.assertEqual(val, "A")
        self.assertEqual(errs,
                         [FluentReferenceError("<string>:12:9: Unknown external: num")])

    def test_with_argument_int(self):
        val, errs = self.bundle.format('baz', {'num': 1})
        self.assertEqual(val, "B")

    def test_with_argument_float(self):
        val, errs = self.bundle.format('baz', {'num': 1.0})
        self.assertEqual(val, "B")

    def test_with_float(self):
        val, errs = self.bundle.format('qux', {})
        self.assertEqual(val, "B")


class TestSelectExpressionWithPlaceables(unittest.TestCase):

    def test_external_arguments_in_variants(self):
        # We are testing several things:
        # - that [b] variant doesn't trigger 'Unknown external: arg'
        # - some logic in compiler implementation regarding when variables are looked up,
        #   so that [a] and [c] variants both can find 'arg'.
        bundle = FluentBundle.from_string('en-US', dedent_ftl("""
            foo = { $lookup ->
                 [a]    { $arg }
                 [b]    B
                *[c]    { $arg }
             }
        """))
        # No args:
        val1, errs1 = bundle.format('foo', {})
        self.assertEqual(val1, "arg")
        self.assertEqual(errs1,
                         [
                             FluentReferenceError("<string>:2:9: Unknown external: lookup"),
                             FluentReferenceError("<string>:5:15: Unknown external: arg"),
                          ])

        # [a] branch, arg supplied
        val2, errs2 = bundle.format('foo', {'lookup': 'a', 'arg': 'A'})
        self.assertEqual(val2, "A")
        self.assertEqual(errs2, [])

        # [a] branch, arg not supplied
        val3, errs3 = bundle.format('foo', {'lookup': 'a'})
        self.assertEqual(val3, "arg")
        self.assertEqual(errs3, [FluentReferenceError("<string>:3:15: Unknown external: arg")])

        # [b] branch
        val4, errs4 = bundle.format('foo', {'lookup': 'b'})
        self.assertEqual(val4, "B")
        self.assertEqual(errs4, [])

        # [c] branch, arg supplied
        val5, errs5 = bundle.format('foo', {'lookup': 'c', 'arg': 'C'})
        self.assertEqual(val5, "C")
        self.assertEqual(errs5, [])

        # [c] branch, arg not supplied
        val6, errs6 = bundle.format('foo', {'lookup': 'c'})
        self.assertEqual(val6, "arg")
        self.assertEqual(errs6, [FluentReferenceError("<string>:5:15: Unknown external: arg")])


class TestSelectExpressionWithPluralCategories(unittest.TestCase):

    def setUp(self):
        self.bundle = FluentBundle.from_string('en-US', dedent_ftl("""
            foo = { 1 ->
                [one] A
               *[other] B
             }

            foo-arg = { $count ->
                [one] A
               *[other] B
             }

            bar = { 1 ->
                [1] A
               *[other] B
             }

            bar-arg = { $count ->
                [1] A
               *[other] B
             }

            baz = { "not a number" ->
                [one] A
               *[other] B
             }

            baz-arg = { $count ->
                [one] A
               *[other] B
             }

            qux = { 1.0 ->
                [1] A
               *[other] B
             }

        """), use_isolating=False)

    def test_selects_the_right_category_with_integer_static(self):
        val, errs = self.bundle.format('foo', {})
        self.assertEqual(val, "A")
        self.assertEqual(errs, [])

    def test_selects_the_right_category_with_integer_runtime(self):
        val, errs = self.bundle.format('foo-arg', {'count': 1})
        self.assertEqual(val, "A")
        self.assertEqual(errs, [])

        val, errs = self.bundle.format('foo-arg', {'count': 2})
        self.assertEqual(val, "B")
        self.assertEqual(errs, [])

    def test_selects_the_right_category_with_float_static(self):
        val, errs = self.bundle.format('qux', {})
        self.assertEqual(val, "A")
        self.assertEqual(errs, [])

    def test_selects_the_right_category_with_float_runtime(self):
        val, errs = self.bundle.format('foo-arg', {'count': 1.0})
        self.assertEqual(val, "A")
        self.assertEqual(errs, [])

    def test_selects_exact_match_static(self):
        val, errs = self.bundle.format('bar', {})
        self.assertEqual(val, "A")
        self.assertEqual(errs, [])

    def test_selects_exact_match_runtime(self):
        val, errs = self.bundle.format('bar-arg', {'count': 1})
        self.assertEqual(val, "A")
        self.assertEqual(errs, [])

    def test_selects_default_with_invalid_selector_static(self):
        val, errs = self.bundle.format('baz', {})
        self.assertEqual(val, "B")
        self.assertEqual(errs, [])

    def test_selects_default_with_invalid_selector_runtime(self):
        val, errs = self.bundle.format('baz-arg', {'count': 'not a number'})
        self.assertEqual(val, "B")
        self.assertEqual(errs, [])

    def test_with_a_missing_selector(self):
        val, errs = self.bundle.format('foo-arg', {})
        self.assertEqual(val, "B")
        self.assertEqual(errs,
                         [FluentReferenceError("<string>:7:13: Unknown external: count")])


class TestSelectExpressionWithTerms(unittest.TestCase):

    def setUp(self):
        self.bundle = FluentBundle.from_string('en-US', dedent_ftl("""
            -my-term = term
                 .attr = termattribute

            ref-term-attr = { -my-term.attr ->
                    [termattribute]   Term Attribute
                   *[other]           Other
            }

            ref-term-attr-other = { -my-term.attr ->
                    [x]      Term Attribute
                   *[other]  Other
            }

            ref-term-attr-missing = { -my-term.missing ->
                    [x]      Term Attribute
                   *[other]  Other
            }
        """), use_isolating=False)

    def test_ref_term_attribute(self):
        val, errs = self.bundle.format('ref-term-attr')
        self.assertEqual(val, "Term Attribute")
        self.assertEqual(errs, [])

    def test_ref_term_attribute_fallback(self):
        val, errs = self.bundle.format('ref-term-attr-other')
        self.assertEqual(val, "Other")
        self.assertEqual(errs, [])

    def test_ref_term_attribute_missing(self):
        val, errs = self.bundle.format('ref-term-attr-missing')
        self.assertEqual(val, "Other")
        self.assertEqual(len(errs), 1)
        self.assertEqual(errs,
                         [FluentReferenceError('<string>:15:27: Unknown attribute: -my-term.missing')])
