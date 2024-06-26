import unittest
from types import SimpleNamespace

from markupsafe import Markup, escape

from fluent_compiler import codegen
from fluent_compiler.compiler import compile_messages
from fluent_compiler.errors import FluentCyclicReferenceError, FluentFormatError, FluentReferenceError
from fluent_compiler.resource import FtlResource

from .test_codegen import decompile_ast_list, normalize_python
from .utils import dedent_ftl

# Some TDD tests to help develop compiler. It should be possible to delete
# the tests here and still have complete test coverage of the compiler.py module, via
# the other FluentBundle.format tests.


def compile_messages_to_python(source, locale, use_isolating=False, functions=None, escapers=None, filename=None):
    # We use FluentBundle partially here, but then switch to
    # messages_to_module instead of compile_messages so that we can get the AST
    # back instead of a compiled function.
    resource = FtlResource(dedent_ftl(source), filename=filename)
    output = compile_messages(
        locale,
        [resource],
        use_isolating=use_isolating,
        functions=functions,
        escapers=escapers,
    )
    return decompile_ast_list([output.module_ast]), output.errors


class CompilerTestMixin:
    locale = "en_US"

    maxDiff = None

    def assertCodeEqual(self, code1, code2):
        self.assertEqual(normalize_python(code1), normalize_python(code2))


class UseConcatJoinMixin:
    # This is used so that we don't have to use different tests for different
    # Python versions.
    def setUp(self):
        super().setUp()
        self.default_StringJoin = codegen.StringJoin
        codegen.StringJoin = codegen.ConcatJoin

    def tearDown(self):
        codegen.StringJoin = self.default_StringJoin
        super().tearDown()


class TestCompiler(CompilerTestMixin, UseConcatJoinMixin, unittest.TestCase):
    def test_single_string_literal(self):
        code, errs = compile_messages_to_python(
            """
            foo = Foo
        """,
            self.locale,
        )
        self.assertCodeEqual(
            code,
            """
            def foo(message_args, errors):
                return 'Foo'
        """,
        )
        self.assertEqual(errs, [])

    def test_string_literal_in_placeable(self):
        code, errs = compile_messages_to_python(
            """
            foo = { "Foo" }
        """,
            self.locale,
        )
        self.assertCodeEqual(
            code,
            """
            def foo(message_args, errors):
                return 'Foo'
        """,
        )
        self.assertEqual(errs, [])

    def test_number_literal(self):
        code, errs = compile_messages_to_python(
            """
            foo = { 123 }
        """,
            self.locale,
        )
        self.assertCodeEqual(
            code,
            """
            def foo(message_args, errors):
                return NUMBER(123).format(locale)
        """,
        )
        self.assertEqual(errs, [])

    def test_interpolated_number(self):
        code, errs = compile_messages_to_python(
            """
            foo = x { 123 } y
        """,
            self.locale,
        )
        self.assertCodeEqual(
            code,
            """
            def foo(message_args, errors):
                return 'x ' + NUMBER(123).format(locale) + ' y'
        """,
        )
        self.assertEqual(errs, [])

    def test_message_reference_plus_string_literal(self):
        code, errs = compile_messages_to_python(
            """
            foo = Foo
            bar = X { foo }
        """,
            self.locale,
        )
        self.assertCodeEqual(
            code,
            """
            def foo(message_args, errors):
                return 'Foo'

            def bar(message_args, errors):
                return 'X ' + foo(message_args, errors)
        """,
        )
        self.assertEqual(errs, [])

    def test_single_message_reference(self):
        code, errs = compile_messages_to_python(
            """
            foo = Foo
            bar = { foo }
        """,
            self.locale,
        )
        self.assertCodeEqual(
            code,
            """
            def foo(message_args, errors):
                return 'Foo'

            def bar(message_args, errors):
                return foo(message_args, errors)
        """,
        )
        self.assertEqual(errs, [])

    def test_message_attr_reference(self):
        code, errs = compile_messages_to_python(
            """
            foo =
               .attr = Foo Attr
            bar = { foo.attr }
        """,
            self.locale,
        )
        self.assertCodeEqual(
            code,
            """
            def foo__attr(message_args, errors):
                return 'Foo Attr'

            def bar(message_args, errors):
                return foo__attr(message_args, errors)
        """,
        )
        self.assertEqual(errs, [])

    def test_single_message_reference_reversed_order(self):
        # We should cope with forward references
        code, errs = compile_messages_to_python(
            """
            bar = { foo }
            foo = Foo
        """,
            self.locale,
        )
        self.assertCodeEqual(
            code,
            """
            def bar(message_args, errors):
                return foo(message_args, errors)

            def foo(message_args, errors):
                return 'Foo'
        """,
        )
        self.assertEqual(errs, [])

    def test_single_message_bad_reference(self):
        code, errs = compile_messages_to_python(
            """
            bar = { foo }
        """,
            self.locale,
        )
        # We already know that foo does not exist, so we can hard code the error
        # into the function for the runtime error.
        self.assertCodeEqual(
            code,
            """
            def bar(message_args, errors):
                errors.append(FluentReferenceError('<string>:2:9: Unknown message: foo'))
                return 'foo'
        """,
        )
        # And we should get a compile time error:
        self.assertEqual(errs, [("bar", FluentReferenceError("<string>:2:9: Unknown message: foo"))])

    def test_name_collision_function_args(self):
        code, errs = compile_messages_to_python(
            """
            errors = Errors
        """,
            self.locale,
        )
        self.assertCodeEqual(
            code,
            """
            def errors2(message_args, errors):
                return 'Errors'
        """,
        )
        self.assertEqual(errs, [])

    def test_name_collision_builtins(self):
        code, errs = compile_messages_to_python(
            """
            zip = Zip
        """,
            self.locale,
        )
        self.assertCodeEqual(
            code,
            """
            def zip2(message_args, errors):
                return 'Zip'
        """,
        )
        self.assertEqual(errs, [])

    def test_name_collision_keyword(self):
        code, errs = compile_messages_to_python(
            """
            class = Class
        """,
            self.locale,
        )
        self.assertCodeEqual(
            code,
            """
            def class2(message_args, errors):
                return 'Class'
        """,
        )
        self.assertEqual(errs, [])

    def test_message_mapping_used(self):
        # Checking that we actually use message_mapping when looking up the name
        # of the message function to call.
        code, errs = compile_messages_to_python(
            """
            zip = Foo
            str = { zip }
        """,
            self.locale,
        )
        self.assertCodeEqual(
            code,
            """
            def zip2(message_args, errors):
                return 'Foo'

            def str2(message_args, errors):
                return zip2(message_args, errors)
        """,
        )
        self.assertEqual(errs, [])

    def test_name_collision_attrs(self):
        # Our method for suggesting function names produces collisions in some
        # cases. Check that it doesn't matter
        code, errs = compile_messages_to_python(
            """
            foo--bar = Foo Bar
                    .attr = Attr

            foo     = Foo
               .bar--attr = Bar Attr

            caller1 = { foo--bar.attr }
            caller2 = { foo.bar--attr }
        """,
            self.locale,
        )
        self.assertCodeEqual(
            code,
            """
            def foo__bar(message_args, errors):
                return 'Foo Bar'

            def foo__bar__attr(message_args, errors):
                return 'Attr'

            def foo(message_args, errors):
                return 'Foo'

            def foo__bar__attr2(message_args, errors):
                return 'Bar Attr'

            def caller1(message_args, errors):
                return foo__bar__attr(message_args, errors)

            def caller2(message_args, errors):
                return foo__bar__attr2(message_args, errors)
        """,
        )
        self.assertEqual(errs, [])

    def test_external_argument(self):
        code, errs = compile_messages_to_python(
            """
            with-arg = { $arg }
        """,
            self.locale,
        )
        self.assertCodeEqual(
            code,
            """
            def with_arg(message_args, errors):
                try:
                    _arg = message_args['arg']
                except (LookupError, TypeError):
                    errors.append(FluentReferenceError('<string>:2:14: Unknown external: arg'))
                    _arg = FluentNone('arg')
                    _arg_h = _arg
                else:
                    _arg_h = handle_argument(_arg, 'arg', locale, errors)
                return handle_output(_arg_h, locale, errors)
        """,
        )
        self.assertEqual(errs, [])

    def test_function_call(self):
        code, errs = compile_messages_to_python(
            """
            foo = { NUMBER(12345) }
        """,
            self.locale,
        )
        self.assertCodeEqual(
            code,
            """
            def foo(message_args, errors):
                return NUMBER(12345).format(locale)
        """,
        )
        self.assertEqual(errs, [])

    def test_function_call_external_arg(self):
        code, errs = compile_messages_to_python(
            """
            foo = { NUMBER($arg) }
        """,
            self.locale,
        )
        self.assertCodeEqual(
            code,
            """
            def foo(message_args, errors):
                try:
                    _arg = message_args['arg']
                except (LookupError, TypeError):
                    errors.append(FluentReferenceError('<string>:2:16: Unknown external: arg'))
                    _arg = FluentNone('arg')
                    _arg_h = _arg
                else:
                    _arg_h = handle_argument(_arg, 'arg', locale, errors)
                return NUMBER(_arg_h).format(locale)
        """,
        )
        self.assertEqual(errs, [])

    def test_function_call_kwargs(self):
        code, errs = compile_messages_to_python(
            """
            foo = { NUMBER(12345, useGrouping: 0) }
        """,
            self.locale,
        )
        self.assertCodeEqual(
            code,
            """
            def foo(message_args, errors):
                return NUMBER(12345, useGrouping=0).format(locale)
        """,
        )
        self.assertEqual(errs, [])

    def test_missing_function_call(self):
        code, errs = compile_messages_to_python(
            """
            foo = { MISSING(123) }
        """,
            self.locale,
        )
        self.assertCodeEqual(
            code,
            """
            def foo(message_args, errors):
                errors.append(FluentReferenceError('Unknown function: MISSING'))
                return 'MISSING()'
        """,
        ),
        self.assertEqual(errs, [("foo", FluentReferenceError("Unknown function: MISSING"))])

    def test_function_call_with_bad_keyword_arg(self):
        def MYFUNC(arg, kw1=None, kw2=None):
            return arg

        # Disallow 'kw2' arg
        MYFUNC.ftl_arg_spec = (1, ["kw1"])
        code, errs = compile_messages_to_python(
            """
            foo = { MYFUNC(123, kw2: 1) }
        """,
            self.locale,
            functions={"MYFUNC": MYFUNC},
        )
        self.assertCodeEqual(
            code,
            """
            def foo(message_args, errors):
                errors.append(TypeError('MYFUNC() got an unexpected keyword argument \\'kw2\\''))
                return handle_output(MYFUNC(NUMBER(123)), locale, errors)
        """,
        ),
        self.assertEqual(len(errs), 1)
        self.assertEqual(errs[0][0], "foo")
        self.assertEqual(type(errs[0][1]), TypeError)

    def test_function_call_with_bad_positional_arg(self):
        def MYFUNC():
            return ""

        code, errs = compile_messages_to_python(
            """
            foo = { MYFUNC(123) }
        """,
            self.locale,
            functions={"MYFUNC": MYFUNC},
        )
        self.assertCodeEqual(
            code,
            """
            def foo(message_args, errors):
                errors.append(TypeError('MYFUNC() takes 0 positional arguments but 1 were given'))
                return handle_output(MYFUNC(), locale, errors)
        """,
        ),
        self.assertEqual(len(errs), 1)
        self.assertEqual(errs[0][0], "foo")
        self.assertEqual(type(errs[0][1]), TypeError)

    def test_function_defined_with_bad_kwargs(self):
        def MYFUNC():
            return ""

        MYFUNC.ftl_arg_spec = (0, ["allowable-kwarg", "invalid kwarg name"])

        code, errs = compile_messages_to_python(
            """
            foo = { MYFUNC() }
        """,
            self.locale,
            functions={"MYFUNC": MYFUNC},
        )
        self.assertCodeEqual(
            code,
            """
            def foo(message_args, errors):
                return handle_output(MYFUNC(), locale, errors)
        """,
        ),
        self.assertEqual(
            errs,
            [
                (
                    None,
                    FluentFormatError("MYFUNC() has invalid keyword argument name 'invalid kwarg name'"),
                )
            ],
        )

    def test_function_called_with_disallowed_kwarg(self):
        def MYFUNC(arg=None):
            return ""

        MYFUNC.ftl_arg_spec = (0, ["arg"])

        code, errs = compile_messages_to_python(
            """
            foo = { MYFUNC(other: 123) }
        """,
            self.locale,
            functions={"MYFUNC": MYFUNC},
        )
        self.assertCodeEqual(
            code,
            """
            def foo(message_args, errors):
                errors.append(TypeError('MYFUNC() got an unexpected keyword argument \\'other\\''))
                return handle_output(MYFUNC(), locale, errors)
        """,
        ),
        self.assertEqual(len(errs), 1)
        self.assertEqual(type(errs[0][1]), TypeError)
        self.assertEqual(errs[0][1].args[0], "MYFUNC() got an unexpected keyword argument 'other'")

    def test_function_called_with_non_identifier_kwarg(self):
        def MYFUNC(**kwargs):
            return ""

        code, errs = compile_messages_to_python(
            """
            foo = { MYFUNC(non-identifier-name: "x") }
        """,
            self.locale,
            functions={"MYFUNC": MYFUNC},
        )
        self.assertCodeEqual(
            code,
            """
            def foo(message_args, errors):
                return handle_output(MYFUNC(**{'non-identifier-name': 'x'}), locale, errors)
        """,
        ),
        self.assertEqual(errs, [])

    def test_message_with_attrs(self):
        code, errs = compile_messages_to_python(
            """
            foo = Foo
               .attr-1 = Attr 1
               .attr-2 = Attr 2
        """,
            self.locale,
        )
        self.assertCodeEqual(
            code,
            """
            def foo(message_args, errors):
                return 'Foo'

            def foo__attr_1(message_args, errors):
                return 'Attr 1'

            def foo__attr_2(message_args, errors):
                return 'Attr 2'
        """,
        )
        self.assertEqual(errs, [])

    def test_term_inline(self):
        code, errs = compile_messages_to_python(
            """
           -term = Term
           message = Message { -term }
        """,
            self.locale,
        )
        self.assertCodeEqual(
            code,
            """
            def message(message_args, errors):
                return 'Message Term'
        """,
        )

    def test_select_string_runtime(self):
        code, errs = compile_messages_to_python(
            """
           foo = { $arg ->
                [a] A
               *[b] B
             }
        """,
            self.locale,
        )
        self.assertCodeEqual(
            code,
            """
            def foo(message_args, errors):
                try:
                    _arg = message_args['arg']
                except (LookupError, TypeError):
                    errors.append(FluentReferenceError('<string>:2:9: Unknown external: arg'))
                    _arg = FluentNone('arg')
                if _arg == 'a':
                    _ret = 'A'
                else:
                    _ret = 'B'
                return _ret
        """,
        )
        self.assertEqual(errs, [])

    def test_select_string_static(self):
        code, errs = compile_messages_to_python(
            """
           foo = { "a" ->
                [a] A
               *[b] B
             }
        """,
            self.locale,
        )
        self.assertCodeEqual(
            code,
            """
            def foo(message_args, errors):
                return 'A'
        """,
        )
        self.assertEqual(errs, [])

    def test_select_number_static(self):
        code, errs = compile_messages_to_python(
            """
           foo = { 1 ->
                [1] One
               *[2] Two
             }
        """,
            self.locale,
        )
        self.assertCodeEqual(
            code,
            """
            def foo(message_args, errors):
                return 'One'
        """,
        )
        self.assertEqual(errs, [])

    def test_select_number_runtime(self):
        code, errs = compile_messages_to_python(
            """
           foo = { $arg ->
                [1] One
               *[2] { 2 }
             }
        """,
            self.locale,
        )
        # We should not get 'NUMBER' calls in the select expression or
        # or the key comparisons, but we should get them for the select value
        # for { 2 }.
        self.assertCodeEqual(
            code,
            """
            def foo(message_args, errors):
                try:
                    _arg = message_args['arg']
                except (LookupError, TypeError):
                    errors.append(FluentReferenceError('<string>:2:9: Unknown external: arg'))
                    _arg = FluentNone('arg')
                if _arg == 1:
                    _ret = 'One'
                else:
                    _ret = NUMBER(2).format(locale)
                return _ret
        """,
        )
        self.assertEqual(errs, [])

    def test_select_plural_category_with_literal(self):
        code, errs = compile_messages_to_python(
            """
           foo = { 1 ->
                [one] One
               *[other] Other
             }
        """,
            self.locale,
        )
        self.assertCodeEqual(
            code,
            """
            def foo(message_args, errors):
                return 'One'
        """,
        )
        self.assertEqual(errs, [])

    def test_select_plural_category_with_arg(self):
        code, errs = compile_messages_to_python(
            """
           foo = { $count ->
                [0] You have nothing
                [one] You have one thing
               *[other] You have some things
             }
        """,
            self.locale,
        )
        self.assertCodeEqual(
            code,
            """
            def foo(message_args, errors):
                try:
                    _arg = message_args['count']
                except (LookupError, TypeError):
                    errors.append(FluentReferenceError('<string>:2:9: Unknown external: count'))
                    _arg = FluentNone('count')
                _plural_form = plural_form_for_number(_arg)
                if _arg == 0:
                    _ret = 'You have nothing'
                elif _arg == 'one' or _plural_form == 'one':
                    _ret = 'You have one thing'
                else:
                    _ret = 'You have some things'
                return _ret
        """,
        )
        self.assertEqual(errs, [])

    def test_combine_strings(self):
        code, errs = compile_messages_to_python(
            """
            foo = Start { "Middle" } End
        """,
            self.locale,
        )
        self.assertCodeEqual(
            code,
            """
            def foo(message_args, errors):
                return 'Start Middle End'
        """,
        )
        self.assertEqual(errs, [])

    def test_single_string_literal_isolating(self):
        code, errs = compile_messages_to_python(
            """
            foo = Foo
        """,
            self.locale,
            use_isolating=True,
        )
        # No isolating chars, because we have no placeables.
        self.assertCodeEqual(
            code,
            """
            def foo(message_args, errors):
                return 'Foo'
        """,
        )
        self.assertEqual(errs, [])

    def test_interpolation_isolating(self):
        code, errs = compile_messages_to_python(
            """
            foo = Foo { $arg } Bar
        """,
            self.locale,
            use_isolating=True,
        )
        self.assertCodeEqual(
            code,
            """
            def foo(message_args, errors):
                try:
                    _arg = message_args['arg']
                except (LookupError, TypeError):
                    errors.append(FluentReferenceError('<string>:2:13: Unknown external: arg'))
                    _arg = FluentNone('arg')
                    _arg_h = _arg
                else:
                    _arg_h = handle_argument(_arg, 'arg', locale, errors)
                return 'Foo \\u2068' + handle_output(_arg_h, locale, errors) + '\\u2069 Bar'
        """,
        )
        self.assertEqual(errs, [])

    def test_cycle_detection(self):
        code, errs = compile_messages_to_python(
            """
            foo = { foo }
        """,
            self.locale,
        )
        self.assertCodeEqual(
            code,
            """
            def foo(message_args, errors):
                errors.append(FluentCyclicReferenceError('<string>:2:1: Cyclic reference in foo'))
                return '???'
        """,
        )
        self.assertEqual(
            errs,
            [
                (
                    "foo",
                    FluentCyclicReferenceError("<string>:2:1: Cyclic reference in foo"),
                )
            ],
        )

    def test_cycle_detection_false_positive_1(self):
        # Test for a bug in early version of cycle detector
        code, errs = compile_messages_to_python(
            """
            foo = { -bar }{ -bar }
            -bar = Bar
        """,
            self.locale,
        )
        self.assertCodeEqual(
            code,
            """
            def foo(message_args, errors):
                return 'BarBar'
        """,
        )
        self.assertEqual(errs, [])

    def test_cycle_detection_with_attrs(self):
        code, errs = compile_messages_to_python(
            """
            foo =
               .attr1 = { bar.attr2 }

            bar =
               .attr2 = { foo.attr1 }
        """,
            self.locale,
        )
        self.assertCodeEqual(
            code,
            """
            def foo__attr1(message_args, errors):
                errors.append(FluentCyclicReferenceError('<string>:3:4: Cyclic reference in foo.attr1'))
                return '???'

            def bar__attr2(message_args, errors):
                errors.append(FluentCyclicReferenceError('<string>:6:4: Cyclic reference in bar.attr2'))
                return '???'
        """,
        )
        self.assertEqual(
            errs,
            [
                (
                    "foo.attr1",
                    FluentCyclicReferenceError("<string>:3:4: Cyclic reference in foo.attr1"),
                ),
                (
                    "bar.attr2",
                    FluentCyclicReferenceError("<string>:6:4: Cyclic reference in bar.attr2"),
                ),
            ],
        )

    def test_term_cycle_detection(self):
        code, errs = compile_messages_to_python(
            """
            -cyclic-term = { -cyclic-term }
            cyclic-term-message = { -cyclic-term }
        """,
            self.locale,
        )
        self.assertCodeEqual(
            code,
            """
            def cyclic_term_message(message_args, errors):
                errors.append(
                    FluentCyclicReferenceError('<string>:3:1: Cyclic reference in cyclic-term-message')
                )
                return '???'
        """,
        )
        self.assertEqual(
            errs,
            [
                (
                    "cyclic-term-message",
                    FluentCyclicReferenceError("<string>:3:1: Cyclic reference in cyclic-term-message"),
                ),
            ],
        )

    def test_cycle_detection_with_unknown_attr(self):
        # unknown attributes fall back to main message, which brings
        # another option for a cycle.
        code, errs = compile_messages_to_python(
            """
            foo = { bar.bad-attr }

            bar = { foo }
        """,
            self.locale,
        )
        self.assertCodeEqual(
            code,
            """
            def foo(message_args, errors):
                errors.append(FluentCyclicReferenceError('<string>:2:1: Cyclic reference in foo'))
                return '???'

            def bar(message_args, errors):
                errors.append(FluentCyclicReferenceError('<string>:4:1: Cyclic reference in bar'))
                return '???'
        """,
        )
        self.assertEqual(
            errs,
            [
                (
                    "foo",
                    FluentCyclicReferenceError("<string>:2:1: Cyclic reference in foo"),
                ),
                (
                    "bar",
                    FluentCyclicReferenceError("<string>:4:1: Cyclic reference in bar"),
                ),
            ],
        )

    def test_parameterized_terms_inlined_for_string(self):
        code, errs = compile_messages_to_python(
            """
            -thing = { $article ->
                  *[definite] the thing
                   [indefinite] a thing
            }
            the-thing = { -thing }
            a-thing = { -thing(article: "indefinite") }
        """,
            self.locale,
        )
        # select expression should be statically evaluated and inlined
        self.assertCodeEqual(
            code,
            """
             def the_thing(message_args, errors):
                 return 'the thing'

             def a_thing(message_args, errors):
                 return 'a thing'
        """,
        )

    def test_parameterized_terms_inlined_for_number(self):
        code, errs = compile_messages_to_python(
            """
            -thing = { $count ->
                   [1] a thing
                  *[2] some things
            }
            some-things = { -thing }
            a-thing = { -thing(count: 1) }
        """,
            self.locale,
        )
        # select expression should be statically evaluated and inlined
        self.assertCodeEqual(
            code,
            """
             def some_things(message_args, errors):
                 return 'some things'

             def a_thing(message_args, errors):
                 return 'a thing'
        """,
        )

    def test_parameterized_terms_inlined_with_complex_selector(self):
        code, errs = compile_messages_to_python(
            """
            -brand = Cool Thing
                .status = { $version ->
                    [v2]     available
                   *[v1]     deprecated
                }

            attr-with-arg = { -brand } is { -brand.status(version: "v2") ->
                 [available]   available, yay!
                *[deprecated]  deprecated, sorry
            }
        """,
            self.locale,
        )
        self.assertCodeEqual(
            code,
            """
            def attr_with_arg(message_args, errors):
                return 'Cool Thing is available, yay!'
        """,
        )

    def test_message_call_from_inside_term(self):
        # This might get removed sometime, but for now it is a corner case we
        # need to cover.
        code, errs = compile_messages_to_python(
            """
            outer-message = { -term(a: 1, b: "hello") }
            -term = Term { inner-message }
            inner-message = { $a } { $b }
        """,
            self.locale,
        )
        # outer-message should pass term args, not external args
        self.assertCodeEqual(
            code,
            """
            def outer_message(message_args, errors):
                return 'Term ' + inner_message({'a': NUMBER(1), 'b': 'hello'}, errors)

            def inner_message(message_args, errors):
                try:
                    _arg = message_args['a']
                except (LookupError, TypeError):
                    errors.append(FluentReferenceError('<string>:4:19: Unknown external: a'))
                    _arg = FluentNone('a')
                    _arg_h = _arg
                else:
                    _arg_h = handle_argument(_arg, 'a', locale, errors)
                try:
                    _arg2 = message_args['b']
                except (LookupError, TypeError):
                    errors.append(FluentReferenceError('<string>:4:26: Unknown external: b'))
                    _arg2 = FluentNone('b')
                    _arg_h2 = _arg2
                else:
                    _arg_h2 = handle_argument(_arg2, 'b', locale, errors)
                return handle_output(_arg_h, locale, errors) + ' ' + handle_output(_arg_h2, locale, errors)
        """,
        )

    def test_reuse_external_arguments(self):
        code, errs = compile_messages_to_python(
            """
           foo = { $arg ->
                [0] You have no items
                [1] You have one item
               *[2] You have { NUMBER($arg) } items
             }
        """,
            self.locale,
        )
        # We should re-use the work of getting $arg out of args and
        # not do that twice.
        self.assertCodeEqual(
            code,
            """
            def foo(message_args, errors):
                try:
                    _arg = message_args['arg']
                except (LookupError, TypeError):
                    errors.append(FluentReferenceError('<string>:2:9: Unknown external: arg'))
                    _arg = FluentNone('arg')
                if _arg == 0:
                    _ret = 'You have no items'
                elif _arg == 1:
                    _ret = 'You have one item'
                else:
                    _arg_h = handle_argument(_arg, 'arg', locale, errors)
                    _ret = 'You have ' + NUMBER(_arg_h).format(locale) + ' items'
                return _ret
        """,
        )
        self.assertEqual(errs, [])

    def test_reuse_external_arguments_multiple_branches(self):
        code, errs = compile_messages_to_python(
            """
            foo = { $lookup ->
                 [a]   { $arg }
                 [b]   B
                *[c]   { $arg }
             }
        """,
            self.locale,
        )
        # We should only do 'arg' lookup for first and last branch, for efficiency.
        # But we need to be aware that in last branch, we haven't already looked
        # up 'arg', despite the fact that we did it in an earlier branch.
        self.assertCodeEqual(
            code,
            """
            def foo(message_args, errors):
                try:
                    _arg = message_args['lookup']
                except (LookupError, TypeError):
                    errors.append(FluentReferenceError('<string>:2:9: Unknown external: lookup'))
                    _arg = FluentNone('lookup')
                if _arg == 'a':
                    try:
                        _arg2 = message_args['arg']
                    except (LookupError, TypeError):
                        errors.append(FluentReferenceError('<string>:3:14: Unknown external: arg'))
                        _arg2 = FluentNone('arg')
                        _arg_h = _arg2
                    else:
                        _arg_h = handle_argument(_arg2, 'arg', locale, errors)
                    _ret = handle_output(_arg_h, locale, errors)
                elif _arg == 'b':
                    _ret = 'B'
                else:
                    try:
                        _arg3 = message_args['arg']
                    except (LookupError, TypeError):
                        errors.append(FluentReferenceError('<string>:5:14: Unknown external: arg'))
                        _arg3 = FluentNone('arg')
                        _arg_h2 = _arg3
                    else:
                        _arg_h2 = handle_argument(_arg3, 'arg', locale, errors)
                    _ret = handle_output(_arg_h2, locale, errors)
                return _ret
        """,
        )
        self.assertEqual(errs, [])

    def test_variable_reuse_for_arg_lookup(self):
        code, errs = compile_messages_to_python(
            """
            example = My name is { $name ->
                [Peter] Peter11
               *[other] Jane11
              }
              My gender is { $name ->
                [Peter] Male
               *[other] Female
              }
              """,
            self.locale,
        )
        assert not errs
        # $name should only be looked up once
        self.assertCodeEqual(
            code,
            """
            def example(message_args, errors):
                try:
                    _arg = message_args['name']
                except (LookupError, TypeError):
                    errors.append(FluentReferenceError('<string>:2:24: Unknown external: name'))
                    _arg = FluentNone('name')
                _plural_form = plural_form_for_number(_arg)
                if _arg == 'Peter':
                    _ret = 'Peter11'
                else:
                    _ret = 'Jane11'
                _plural_form2 = plural_form_for_number(_arg)
                if _arg == 'Peter':
                    _ret2 = 'Male'
                else:
                    _ret2 = 'Female'
                return 'My name is ' + _ret + '\\nMy gender is ' + _ret2
        """,
        )

    # TODO - eliminate unused assignments e.g. `_plural_form = plural_form_for_number(_arg)` is unneeded
    # def test_unused_assignments(self):
    #     code, errs = compile_messages_to_python("""
    #         foo = { $arg ->
    #            [0]     Zero
    #           *[other] Other
    #          }
    #     """, self.locale)
    #     self.assertCodeEqual(code, """
    #         def foo(message_args, errors):
    #             try:
    #                 _arg = message_args['arg']
    #             except (LookupError, TypeError):
    #                 errors.append(FluentReferenceError('Unknown external: arg'))
    #                 _arg = FluentNone('arg')
    #             if _arg == 0:
    #                 _ret = 'Zero'
    #             else:
    #                 _ret = 'Other'
    #             return _ret
    #     """)


empty_markup = Markup("")

html_escaper = SimpleNamespace(
    select=lambda message_id=None, **hints: message_id.endswith("-html"),
    output_type=Markup,
    mark_escaped=Markup,
    escape=escape,
    join=empty_markup.join,
    name="html_escaper",
    use_isolating=False,
)


class TestCompilerEscaping(CompilerTestMixin, unittest.TestCase):
    escapers = [html_escaper]

    def compile_messages(self, code, **kwargs):
        return compile_messages_to_python(code, self.locale, escapers=self.escapers, **kwargs)

    def test_argument(self):
        code, errs = self.compile_messages(
            """
            foo-html = { $arg }
        """
        )
        self.assertCodeEqual(
            code,
            """
            def foo_html(message_args, errors):
                try:
                    _arg = message_args['arg']
                except (LookupError, TypeError):
                    errors.append(FluentReferenceError('<string>:2:14: Unknown external: arg'))
                    _arg = FluentNone('arg')
                    _arg_h = _arg
                else:
                    _arg_h = handle_argument_with_escaper(_arg, 'arg', escaper_0__output_type, locale, errors)
                return handle_output_with_escaper(
                    _arg_h,
                    escaper_0__output_type,
                    escaper_0__escape,
                    locale,
                    errors
                )
        """,
        )

    def test_single_text_element(self):
        code, errs = self.compile_messages(
            """
            foo-html = <b>Some HTML</b>
        """
        )
        self.assertCodeEqual(
            code,
            """
            def foo_html(message_args, errors):
                return escaper_0__mark_escaped('<b>Some HTML</b>')
        """,
        )

    def test_reference_to_same_escaper(self):
        # Test we eliminate the unnecessary escaper_0__escape call in the calling code
        code, errs = self.compile_messages(
            """
            foo-html = <b>Some HTML</b>
            bar-html = { foo-html }
        """
        )
        self.assertCodeEqual(
            code,
            """
            def foo_html(message_args, errors):
                return escaper_0__mark_escaped('<b>Some HTML</b>')

            def bar_html(message_args, errors):
                return foo_html(message_args, errors)
        """,
        )

    def test_reference_to_same_escaper_term(self):
        code, errs = self.compile_messages(
            """
            -term-html = <b>Some HTML</b>
            foo-html = { -term-html }
        """
        )
        self.assertCodeEqual(
            code,
            """
            def foo_html(message_args, errors):
                return escaper_0__mark_escaped('<b>Some HTML</b>')
        """,
        )

    def test_term_inlining_with_escaping(self):
        code, errs = self.compile_messages(
            """
            -term-html = <b>Some HTML</b>
            foo-html = Hello { -term-html }
        """
        )
        self.assertCodeEqual(
            code,
            """
            def foo_html(message_args, errors):
                return escaper_0__mark_escaped('Hello <b>Some HTML</b>')
        """,
        )

    def test_non_unique_escaper(self):
        self.assertRaises(
            ValueError,
            compile_messages_to_python,
            "foo = bar",
            self.locale,
            escapers=[html_escaper, html_escaper],
        )
