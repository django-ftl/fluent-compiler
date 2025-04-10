import unittest

from fluent_compiler.errors import FluentFormatError
from fluent_compiler.utils import AnyArg, inspect_function_args


class TestInspectFunctionArgs(unittest.TestCase):
    def test_inspect_function_args_positional(self):
        self.assertEqual(inspect_function_args(lambda: None, "name", []), (0, []))
        self.assertEqual(inspect_function_args(lambda x: None, "name", []), (1, []))
        self.assertEqual(inspect_function_args(lambda x, y: None, "name", []), (2, []))

    def test_inspect_function_args_var_positional(self):
        self.assertEqual(inspect_function_args(lambda *args: None, "name", []), (AnyArg, []))

    def test_inspect_function_args_keywords(self):
        self.assertEqual(inspect_function_args(lambda x, y=1, z=2: None, "name", []), (1, ["y", "z"]))

    def test_inspect_function_args_var_keywords(self):
        self.assertEqual(inspect_function_args(lambda x, **kwargs: None, "name", []), (1, AnyArg))

    def test_inspect_function_args_var_positional_plus_keywords(self):
        self.assertEqual(inspect_function_args(lambda x, y=1, *args: None, "name", []), (AnyArg, ["y"]))

    def test_inspect_function_args_bad_keyword_args(self):
        def foo():
            pass

        foo.ftl_arg_spec = (0, ["bad kwarg", "good", "this-is-fine-too"])
        errors = []
        self.assertEqual(inspect_function_args(foo, "FOO", errors), (0, ["good", "this-is-fine-too"]))
        self.assertEqual(
            errors,
            [FluentFormatError("FOO() has invalid keyword argument name 'bad kwarg'")],
        )
