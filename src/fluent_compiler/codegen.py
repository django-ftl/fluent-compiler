"""
Utilities for doing Python code generation
"""
from __future__ import annotations

import decimal
import keyword
import platform
import re
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Callable, Iterable, Protocol, Sequence, Union, runtime_checkable

from . import ast_compat as py_ast
from .ast_compat import DEFAULT_AST_ARGS, DEFAULT_AST_ARGS_ADD, DEFAULT_AST_ARGS_ARGUMENTS, DEFAULT_AST_ARGS_MODULE
from .compat import TypeAlias
from .utils import allowable_keyword_arg_name, allowable_name

if TYPE_CHECKING:
    # TODO move FtlSource to its own module
    from .compiler import FtlSource


# This module provides simple utilities for building up Python source code. It
# implements only what is really needed by compiler.py, with a number of aims
# and constraints:
#
# 1. Performance.
#
#    The resulting Python code should do as little as possible, especially for
#    simple cases (which are by far the most common for .ftl files)
#
# 2. Correctness (obviously)
#
#    In particular, we should try to make it hard to generate code that is
#    syntactically correct and therefore compiles but doesn't work. We try to
#    make it hard to generate accidental name clashes, or use variables that are
#    not defined.
#
#    Correctness also has a security implication, since the result of this code
#    is 'exec'ed. To that end:
#     * We build up AST, rather than strings. This eliminates many
#       potential bugs caused by wrong escaping/interpolation.
#     * the `as_ast()` methods are paranoid about input, and do many asserts.
#       We do this even though other layers will usually have checked the
#       input, to allow us to reason locally when checking these methods. These
#       asserts must also have 100% code coverage.
#
# 3. Simplicity
#
#    The resulting Python code should be easy to read and understand.
#
# 4. Predictability
#
#    Since we want to test the resulting source code, we have made some design
#    decisions that aim to ensure things like function argument names are
#    consistent and so can be predicted easily.


PROPERTY_TYPE = "PROPERTY_TYPE"
PROPERTY_RETURN_TYPE = "PROPERTY_RETURN_TYPE"
# UNKNOWN_TYPE is just an alias for `object` for clarity.
UNKNOWN_TYPE: type = object
# It is important for our usage of it that UNKNOWN_TYPE is a `type`,
# and the most general `type`.
assert isinstance(UNKNOWN_TYPE, type)


SENSITIVE_FUNCTIONS = {
    # builtin functions that we should never be calling from our code
    # generation. This is a defense-in-depth mechansim to stop our code
    # generation becoming a code execution vulnerability. We also have
    # higher level code that ensures we are not generating calls
    # to arbitrary Python functions.
    # This is not a comprehensive list of functions we are not using, but
    # functions we definitely don't need and are most likely to be used to
    # execute remote code or to get around safety mechanisms.
    "__import__",
    "__build_class__",
    "apply",
    "compile",
    "eval",
    "exec",
    "execfile",
    "exit",
    "file",
    "globals",
    "locals",
    "open",
    "object",
    "reload",
    "type",
}


class CodeGenAst(ABC):
    """
    Base class representing a simplified Python AST (not the real one).
    Generates real `ast.*` nodes via `as_ast()` method.
    """

    @abstractmethod
    def as_ast(self) -> py_ast.AST:
        raise NotImplementedError(f"{self.__class__!r}.as_ast()")

    child_elements: list[str] = NotImplemented


class CodeGenAstList(ABC):
    """
    Alternative base class to CodeGenAst when we have code that wants to return a
    list of AST objects.
    """

    @abstractmethod
    def as_ast_list(self, allow_empty: bool = True) -> list[py_ast.stmt]:
        raise NotImplementedError(f"{self.__class__!r}.as_ast_list()")

    child_elements: list[str] = NotImplemented


CodeGenAstType: TypeAlias = Union[CodeGenAst, CodeGenAstList]


class Scope:
    def __init__(self, parent_scope: Scope | None = None):
        self.parent_scope = parent_scope
        self.names = set()
        self._function_arg_reserved_names = set()
        self._properties: dict[str, dict[str, object]] = {}
        self._assignments = {}

    def is_name_in_use(self, name: str) -> bool:
        if name in self.names:
            return True

        if self.parent_scope is None:
            return False

        return self.parent_scope.is_name_in_use(name)

    def is_name_reserved_function_arg(self, name: str) -> bool:
        if name in self._function_arg_reserved_names:
            return True

        if self.parent_scope is None:
            return False

        return self.parent_scope.is_name_reserved_function_arg(name)

    def is_name_reserved(self, name: str) -> bool:
        return self.is_name_in_use(name) or self.is_name_reserved_function_arg(name)

    def reserve_name(
        self,
        requested: str,
        function_arg: bool = False,
        is_builtin: bool = False,
        properties: dict[str, object] | None = None,
    ):
        """
        Reserve a name as being in use in a scope.

        Pass function_arg=True if this is a function argument.
        'properties' is an optional dict of additional properties
        (e.g. the type associated with a name)
        """

        def _add(final: str):
            self.names.add(final)
            self._properties[final] = properties or {}
            return final

        if function_arg:
            if self.is_name_reserved_function_arg(requested):
                assert not self.is_name_in_use(requested)
                return _add(requested)
            if self.is_name_reserved(requested):
                raise AssertionError(f"Cannot use '{requested}' as argument name as it is already in use")

        cleaned = cleanup_name(requested)

        attempt = cleaned
        count = 2  # instance without suffix is regarded as 1
        # To avoid shadowing of global names in local scope, we
        # take into account parent scope when assigning names.

        def _is_name_allowed(name: str) -> bool:
            # We need to also protect against using keywords ('class', 'def' etc.)
            # i.e. count all keywords as 'used'.
            # However, some builtins are also keywords (e.g. 'None'), and so
            # if a builtin is being reserved, don't check against the keyword list
            if (not is_builtin) and keyword.iskeyword(name):
                return False

            return not self.is_name_reserved(name)

        while not _is_name_allowed(attempt):
            attempt = cleaned + str(count)
            count += 1

        return _add(attempt)

    def reserve_function_arg_name(self, name: str):
        """
        Reserve a name for *later* use as a function argument. This does not result
        in that name being considered 'in use' in the current scope, but will
        avoid the name being assigned for any use other than as a function argument.
        """
        # To keep things simple, and the generated code predictable, we reserve
        # names for all function arguments in a separate scope, and insist on
        # the exact names
        if self.is_name_reserved(name):
            raise AssertionError(f"Can't reserve '{name}' as function arg name as it is already reserved")
        self._function_arg_reserved_names.add(name)

    def get_name_properties(self, name) -> dict[str, object]:
        """
        Gets a dictionary of properties for the name.
        Raises exception if the name is not reserved in this scope or parent
        """
        if name in self._properties:
            return self._properties[name]
        if self.parent_scope is None:
            raise LookupError(f"{name} not found in properties")
        return self.parent_scope.get_name_properties(name)

    def set_name_properties(self, name: str, props: dict[str, object]):
        """
        Sets a dictionary of properties for the name.
        Raises exception if the name is not reserved in this scope or parent.
        """
        scope = self
        while True:
            if scope is None:
                raise LookupError(f"{name} not found in properties")
            if name in scope._properties:
                scope._properties[name].update(props)
                break
            else:
                scope = scope.parent_scope

    def find_names_by_property(self, prop_name: str, prop_val: object) -> list[str]:
        """
        Retrieve all names that match the supplied property name and value
        """
        return [
            name
            for name, props in self._properties.items()
            for k, v in props.items()
            if k == prop_name and v == prop_val
        ]

    def has_assignment(self, name: str) -> bool:
        return name in self._assignments

    def register_assignment(self, name: str) -> None:
        self._assignments[name] = None

    def variable(self, name: str) -> VariableReference:
        # Convenience utility for returning a VariableReference
        return VariableReference(name, self)


_IDENTIFIER_SANITIZER_RE = re.compile("[^a-zA-Z0-9_]")
_IDENTIFIER_START_RE = re.compile("^[a-zA-Z_]")


def cleanup_name(name: str) -> str:
    """
    Convert name to a allowable identifier
    """
    # See https://docs.python.org/2/reference/lexical_analysis.html#grammar-token-identifier
    name = _IDENTIFIER_SANITIZER_RE.sub("", name)
    if not _IDENTIFIER_START_RE.match(name):
        name = "n" + name
    return name


class Statement(CodeGenAst):
    pass


@runtime_checkable
class SupportsNameAssignment(Protocol):
    def has_assignment_for_name(self, name: str) -> bool:
        ...


class _Assignment(Statement):
    child_elements = ["value"]

    def __init__(self, name: str, value: Expression):
        self.name = name
        self.value = value

    def as_ast(self):
        if not allowable_name(self.name):
            raise AssertionError(f"Expected {self.name} to be a valid Python identifier")
        return py_ast.Assign(
            targets=[py_ast.Name(id=self.name, ctx=py_ast.Store(), **DEFAULT_AST_ARGS)],
            value=self.value.as_ast(),
            **DEFAULT_AST_ARGS,
        )

    def has_assignment_for_name(self, name: str) -> bool:
        return self.name == name


class Block(CodeGenAstList):
    child_elements = ["statements"]

    def __init__(self, scope: Scope, parent_block: Block | None = None):
        self.scope = scope
        # We all `Expression` here for things like MethodCall which
        # are bare expressions that are still useful for side effects
        self.statements: list[Block | Statement | Expression] = []
        self.parent_block = parent_block

    def as_ast_list(self, allow_empty: bool = True) -> list[py_ast.stmt]:
        retval = []
        for s in self.statements:
            if isinstance(s, CodeGenAstList):
                retval.extend(s.as_ast_list(allow_empty=True))
            else:
                if isinstance(s, Statement):
                    retval.append(s.as_ast())
                else:
                    # Things like bare function/method calls need to be wrapped
                    # in `Expr` to match the way Python parses.
                    retval.append(py_ast.Expr(s.as_ast(), **DEFAULT_AST_ARGS))

        if len(retval) == 0 and not allow_empty:
            return [py_ast.Pass(**DEFAULT_AST_ARGS)]
        return retval

    def add_statement(self, statement: Statement | Block | Expression) -> None:
        self.statements.append(statement)
        if isinstance(statement, Block):
            if statement.parent_block is None:
                statement.parent_block = self
            else:
                if statement.parent_block != self:
                    raise AssertionError(
                        f"Block {statement} is already child of {statement.parent_block}, can't reassign to {self}"
                    )

    # Safe alternatives to Block.statements being manipulated directly:
    def add_assignment(self, name: str, value: Expression, allow_multiple: bool = False):
        """
        Adds an assigment of the form:

           x = value
        """
        if not self.scope.is_name_in_use(name):
            raise AssertionError(f"Cannot assign to unreserved name '{name}'")

        if self.scope.has_assignment(name):
            if not allow_multiple:
                raise AssertionError(f"Have already assigned to '{name}' in this scope")
        else:
            self.scope.register_assignment(name)

        self.add_statement(_Assignment(name, value))

    def add_function(self, func_name: str, func: Function) -> None:
        assert func.func_name == func_name
        self.add_statement(func)

    def add_return(self, value: Expression) -> None:
        self.add_statement(Return(value))

    def has_assignment_for_name(self, name: str) -> bool:
        for s in self.statements:
            if isinstance(s, SupportsNameAssignment) and s.has_assignment_for_name(name):
                return True
        if self.parent_block is not None:
            return self.parent_block.has_assignment_for_name(name)
        return False


class Module(Block, CodeGenAst):
    def __init__(self):
        scope = Scope(parent_scope=None)
        Block.__init__(self, scope)

    def as_ast(self) -> py_ast.Module:
        return py_ast.Module(body=self.as_ast_list(), type_ignores=[], **DEFAULT_AST_ARGS_MODULE)

    def as_multiple_module_ast(self) -> Iterable[py_ast.Module]:
        retval: list[py_ast.Module] = []
        for item in self.as_ast_list():
            mod = py_ast.Module(body=[item], type_ignores=[], **DEFAULT_AST_ARGS_MODULE)
            if hasattr(item, "filename"):
                # For use by compile_messages
                mod.filename = item.filename
            retval.append(mod)
        return retval


class Function(Scope, Statement):
    child_elements = ["body"]

    def __init__(
        self,
        name: str,
        args: Sequence[str] | None = None,
        parent_scope: Scope | None = None,
        source: FtlSource | None = None,
    ):
        super().__init__(parent_scope=parent_scope)
        self.body = Block(self)
        self.func_name = name
        if args is None:
            args = ()
        for arg in args:
            if self.is_name_in_use(arg):
                raise AssertionError(f"Can't use '{arg}' as function argument name because it shadows other names")
            self.reserve_name(arg, function_arg=True)
        self.args = args
        self.source = source

    def as_ast(self) -> py_ast.stmt:
        if not allowable_name(self.func_name):
            raise AssertionError(f"Expected '{self.func_name}' to be a valid Python identifier")
        for arg in self.args:
            if not allowable_name(arg):
                raise AssertionError(f"Expected '{arg}' to be a valid Python identifier")

        func_def = py_ast.FunctionDef(
            name=self.func_name,
            args=py_ast.arguments(
                posonlyargs=[],
                args=([py_ast.arg(arg=arg_name, annotation=None, **DEFAULT_AST_ARGS) for arg_name in self.args]),
                vararg=None,
                kwonlyargs=[],
                kw_defaults=[],
                kwarg=None,
                defaults=[],
                **DEFAULT_AST_ARGS_ARGUMENTS,
            ),
            body=self.body.as_ast_list(allow_empty=False),
            decorator_list=[],
            type_params=[],  # ast_decompiler compat
            returns=None,  # ast_decompiler compat
            **DEFAULT_AST_ARGS,
        )
        if (source := self.source) is not None and source.filename is not None:
            func_def.filename = source.filename  # See Module.as_multiple_module_ast

            # It's hard to get good line numbers for all AST objects, but
            # if we put the FTL line number of the main message on all nodes
            # this gets us a lot of the benefit for a smallish cost
            def add_lineno(node: py_ast.AST):
                node.lineno = source.row

            traverse(func_def, add_lineno)
        return func_def

    def add_return(self, value: Expression):
        self.body.add_return(value)


class Return(Statement):
    child_elements = ["value"]

    def __init__(self, value: Expression):
        self.value = value

    def as_ast(self):
        return py_ast.Return(self.value.as_ast(), **DEFAULT_AST_ARGS)

    def __repr__(self):
        return f"Return({repr(self.value)}"


class If(Statement):
    child_elements = ["if_blocks", "conditions", "else_block"]

    def __init__(self, parent_scope: Scope, parent_block: Block | None = None):
        # We model a "compound if statement" as a list of if blocks
        # (if/elif/elif etc), each with their own condition, with a final else
        # block. Note this is quite different from Python's AST for the same
        # thing, so conversion to AST is more complex because of this.
        self.if_blocks: list[Block] = []
        self.conditions: list[Expression] = []
        self._parent_block = parent_block
        self.else_block = Block(parent_scope, parent_block=self._parent_block)
        self._parent_scope = parent_scope

    def add_if(self, condition):
        new_if = Block(self._parent_scope, parent_block=self._parent_block)
        self.if_blocks.append(new_if)
        self.conditions.append(condition)
        return new_if

    def finalize(self) -> Block | Statement:
        if not self.if_blocks:
            # Unusual case of no conditions, only default case, but it
            # simplifies other code to be able to handle this uniformly. We can
            # replace this if statement with a single unconditional block.
            return self.else_block
        return self

    def as_ast(self) -> py_ast.If:
        if len(self.if_blocks) == 0:
            raise AssertionError("Should have called `finalize` on If")
        if_ast = empty_If()
        current_if = if_ast
        previous_if = None
        for condition, if_block in zip(self.conditions, self.if_blocks):
            current_if.test = condition.as_ast()
            current_if.body = if_block.as_ast_list()
            if previous_if is not None:
                previous_if.orelse.append(current_if)

            previous_if = current_if
            current_if = empty_If()

        if self.else_block.statements:
            assert previous_if is not None
            previous_if.orelse = self.else_block.as_ast_list()

        return if_ast


class Try(Statement):
    child_elements = ["catch_exceptions", "try_block", "except_block", "else_block"]

    def __init__(self, catch_exceptions: Sequence[Expression], parent_scope: Scope):
        self.catch_exceptions = catch_exceptions
        self.try_block = Block(parent_scope)
        self.except_block = Block(parent_scope)
        self.else_block = Block(parent_scope)

    def as_ast(self) -> py_ast.Try:
        return py_ast.Try(
            body=self.try_block.as_ast_list(allow_empty=False),
            handlers=[
                py_ast.ExceptHandler(
                    type=(
                        self.catch_exceptions[0].as_ast()
                        if len(self.catch_exceptions) == 1
                        else py_ast.Tuple(
                            elts=[e.as_ast() for e in self.catch_exceptions],
                            ctx=py_ast.Load(),
                            **DEFAULT_AST_ARGS,
                        )
                    ),
                    name=None,
                    body=self.except_block.as_ast_list(allow_empty=False),
                    **DEFAULT_AST_ARGS,
                )
            ],
            orelse=self.else_block.as_ast_list(allow_empty=True),
            finalbody=[],
            **DEFAULT_AST_ARGS,
        )

    def has_assignment_for_name(self, name: str) -> bool:
        if (
            self.try_block.has_assignment_for_name(name) or self.else_block.has_assignment_for_name(name)
        ) and self.except_block.has_assignment_for_name(name):
            return True
        return False


class Expression(CodeGenAst):
    # type represents the Python type this expression will produce,
    # if we know it (UNKNOWN_TYPE otherwise).
    type: type = UNKNOWN_TYPE

    @abstractmethod
    def as_ast(self) -> py_ast.expr:
        raise NotImplementedError()


class String(Expression):
    child_elements = []

    type = str

    def __init__(self, string_value: str):
        self.string_value = string_value

    def as_ast(self) -> py_ast.expr:
        return py_ast.Constant(
            self.string_value,
            kind=None,  # 3.8, indicates no prefix, needed only for tests
            **DEFAULT_AST_ARGS,
        )

    def __repr__(self):
        return f"String({repr(self.string_value)})"

    def __eq__(self, other: object):
        return isinstance(other, String) and other.string_value == self.string_value


class Number(Expression):
    child_elements = []

    def __init__(self, number: int | float | decimal.Decimal):
        self.number = number
        self.type = type(number)

    def as_ast(self) -> py_ast.expr:
        return py_ast.Constant(self.number, **DEFAULT_AST_ARGS)

    def __repr__(self):
        return f"Number({repr(self.number)})"


class List(Expression):
    child_elements = ["items"]

    def __init__(self, items):
        self.items = items
        self.type = list

    def as_ast(self) -> py_ast.expr:
        return py_ast.List(elts=[i.as_ast() for i in self.items], ctx=py_ast.Load(), **DEFAULT_AST_ARGS)


class Dict(Expression):
    child_elements = ["pairs"]

    def __init__(self, pairs: Sequence[tuple[Expression, Expression]]):
        self.pairs = pairs
        self.type = dict

    def as_ast(self) -> py_ast.expr:
        return py_ast.Dict(
            keys=[k.as_ast() for k, _ in self.pairs],
            values=[v.as_ast() for _, v in self.pairs],
            **DEFAULT_AST_ARGS,
        )


class StringJoinBase(Expression):
    child_elements = ["parts"]

    type = str

    def __init__(self, parts: Sequence[Expression]):
        self.parts = parts

    def __repr__(self):
        return f"{self.__class__.__name__}([{', '.join(repr(p) for p in self.parts)}])"

    @classmethod
    def build(cls: type[StringJoinBase], parts: Sequence[Expression]) -> StringJoinBase | Expression:
        """
        Build a string join operation, but return a simpler expression if possible.
        """
        # Merge adjacent String objects.
        new_parts: list[Expression] = []
        for part in parts:
            if len(new_parts) > 0 and isinstance(new_parts[-1], String) and isinstance(part, String):
                new_parts[-1] = String(new_parts[-1].string_value + part.string_value)
            else:
                new_parts.append(part)
        parts = new_parts

        # See if we can eliminate the StringJoin altogether
        if len(parts) == 0:
            return String("")
        if len(parts) == 1:
            return parts[0]
        return cls(parts)


class FStringJoin(StringJoinBase):
    def as_ast(self) -> py_ast.expr:
        # f-strings
        values: list[py_ast.expr] = []
        for part in self.parts:
            if isinstance(part, String):
                values.append(part.as_ast())
            else:
                values.append(
                    py_ast.FormattedValue(
                        value=part.as_ast(),
                        conversion=-1,
                        format_spec=None,
                        **DEFAULT_AST_ARGS,
                    )
                )
        return py_ast.JoinedStr(values=values, **DEFAULT_AST_ARGS)


class ConcatJoin(StringJoinBase):
    def as_ast(self) -> py_ast.expr:
        # Concatenate with +
        left = self.parts[0].as_ast()
        for part in self.parts[1:]:
            right = part.as_ast()
            left = py_ast.BinOp(
                left=left,
                op=py_ast.Add(**DEFAULT_AST_ARGS_ADD),
                right=right,
                **DEFAULT_AST_ARGS,
            )
        return left


# For CPython, f-strings give a measurable improvement over concatenation
# (about 5% for `test_single_interpolation_fluent_compiler` benchmark). For all
# versions of PyPy tested it has significantly worse performance (more than
# 10%). We'll assume other non-CPython implementations are like PyPy.

if platform.python_implementation() == "CPython":
    StringJoin = FStringJoin
else:
    StringJoin = ConcatJoin


class VariableReference(Expression):
    child_elements = []

    def __init__(self, name: str, scope: Scope):
        if not scope.is_name_in_use(name):
            raise AssertionError(f"Cannot refer to undefined variable '{name}'")
        self.name = name
        looked_up_type = scope.get_name_properties(name).get(PROPERTY_TYPE, UNKNOWN_TYPE)
        assert isinstance(looked_up_type, type)
        self.type = looked_up_type

    def as_ast(self) -> py_ast.expr:
        if not allowable_name(self.name, allow_builtin=True):
            raise AssertionError(f"Expected {self.name} to be a valid Python identifier")
        return py_ast.Name(id=self.name, ctx=py_ast.Load(), **DEFAULT_AST_ARGS)

    def __eq__(self, other):
        return type(other) is type(self) and other.name == self.name

    def __repr__(self):
        return f"VariableReference({repr(self.name)})"


class FunctionCall(Expression):
    child_elements = ["args", "kwargs"]

    def __init__(
        self,
        function_name: str,
        args: Sequence[Expression],
        kwargs: dict[str, Expression],
        scope: Scope,
        expr_type: type = UNKNOWN_TYPE,
    ):
        if not scope.is_name_in_use(function_name):
            raise AssertionError(f"Cannot call unknown function '{function_name}'")
        self.function_name = function_name
        self.args = list(args)
        self.kwargs = kwargs
        if expr_type is UNKNOWN_TYPE:
            # Try to find out automatically
            looked_up_return_type = scope.get_name_properties(function_name).get(PROPERTY_RETURN_TYPE, expr_type)
            assert isinstance(looked_up_return_type, type)
            expr_type = looked_up_return_type
        self.type = expr_type

    def as_ast(self) -> py_ast.expr:
        if not allowable_name(self.function_name, allow_builtin=True):
            raise AssertionError(f"Expected {self.function_name} to be a valid Python identifier or builtin")

        if self.function_name in SENSITIVE_FUNCTIONS:
            raise AssertionError(f"Disallowing call to '{self.function_name}'")

        for name in self.kwargs.keys():
            if not allowable_keyword_arg_name(name):
                raise AssertionError(f"Expected {name} to be a valid Fluent NamedArgument name")

        if any(not allowable_name(name) for name in self.kwargs.keys()):
            # This branch covers function arg names like 'foo-bar', which are
            # allowable in Fluent, but not normally in Python. We work around
            # this using `my_function(**{'foo-bar': baz})` syntax.

            # (In fact, that's not true. It seems that this branch is not
            # actually necessary, since it is the Python parser that disallows
            # `foo-bar` as an identifier, and we are by-passing that by
            # generating AST directly. The functional test in
            # tests/format/test_functions.py
            # (test_non_identifier_python_keyword_args) passes without this
            # branch. However, to be on the safe side, and to produce AST that
            # decompiles to something more recognisably correct, we pretend this
            # is necessary).
            kwarg_pairs = list(sorted(self.kwargs.items()))
            kwarg_names, kwarg_values = [k for k, _ in kwarg_pairs], [v for _, v in kwarg_pairs]
            return py_ast.Call(
                func=py_ast.Name(id=self.function_name, ctx=py_ast.Load(), **DEFAULT_AST_ARGS),
                args=[arg.as_ast() for arg in self.args],
                keywords=[
                    py_ast.keyword(
                        arg=None,
                        value=py_ast.Dict(
                            keys=[py_ast.Constant(k, kind=None, **DEFAULT_AST_ARGS) for k in kwarg_names],
                            values=[v.as_ast() for v in kwarg_values],
                            **DEFAULT_AST_ARGS,
                        ),
                        **DEFAULT_AST_ARGS,
                    )
                ],
                **DEFAULT_AST_ARGS,
            )

        # Normal `my_function(foo=bar)` syntax
        return py_ast.Call(
            func=py_ast.Name(id=self.function_name, ctx=py_ast.Load(), **DEFAULT_AST_ARGS),
            args=[arg.as_ast() for arg in self.args],
            keywords=[
                py_ast.keyword(arg=name, value=value.as_ast(), **DEFAULT_AST_ARGS)
                for name, value in self.kwargs.items()
            ],
            **DEFAULT_AST_ARGS,
        )

    def __repr__(self):
        return f"FunctionCall({self.function_name}, {self.args}, {self.kwargs})"


class MethodCall(Expression):
    child_elements = ["obj", "args"]

    def __init__(self, obj: Expression, method_name: str, args: Sequence[Expression], expr_type: type = UNKNOWN_TYPE):
        # We can't check method_name because we don't know the type of obj yet.
        self.obj = obj
        self.method_name = method_name
        self.args = args
        self.type = expr_type

    def as_ast(self) -> py_ast.expr:
        if not allowable_name(self.method_name, for_method=True):
            raise AssertionError(f"Expected {self.method_name} to be a valid Python identifier")
        return py_ast.Call(
            func=py_ast.Attribute(
                value=self.obj.as_ast(),
                attr=self.method_name,
                ctx=py_ast.Load(),
                **DEFAULT_AST_ARGS,
            ),
            args=[arg.as_ast() for arg in self.args],
            keywords=[],
            **DEFAULT_AST_ARGS,
        )

    def __repr__(self):
        return f"MethodCall({repr(self.obj)}, {repr(self.method_name)}, {repr(self.args)})"


class DictLookup(Expression):
    child_elements = ["lookup_obj", "lookup_arg"]

    def __init__(self, lookup_obj: Expression, lookup_arg: Expression, expr_type: type = UNKNOWN_TYPE):
        self.lookup_obj = lookup_obj
        self.lookup_arg = lookup_arg
        self.type = expr_type

    def as_ast(self) -> py_ast.expr:
        return py_ast.Subscript(
            value=self.lookup_obj.as_ast(),
            slice=py_ast.subscript_slice_object(self.lookup_arg.as_ast()),
            ctx=py_ast.Load(),
            **DEFAULT_AST_ARGS,
        )


ObjectCreation = FunctionCall


class NoneExpr(Expression):
    type = type(None)

    def as_ast(self) -> py_ast.expr:
        return py_ast.Constant(value=None, **DEFAULT_AST_ARGS)


class BinaryOperator(Expression):
    child_elements = ["left", "right"]

    def __init__(self, left: Expression, right: Expression):
        self.left = left
        self.right = right


class Equals(BinaryOperator):
    type = bool

    def as_ast(self) -> py_ast.expr:
        return py_ast.Compare(
            left=self.left.as_ast(),
            comparators=[self.right.as_ast()],
            ops=[py_ast.Eq()],
            **DEFAULT_AST_ARGS,
        )


class BoolOp(BinaryOperator):
    type = bool
    op = NotImplemented

    def as_ast(self) -> py_ast.expr:
        return py_ast.BoolOp(
            op=self.op(),
            values=[self.left.as_ast(), self.right.as_ast()],
            **DEFAULT_AST_ARGS,
        )


class Or(BoolOp):
    op = py_ast.Or


def traverse(ast_node: py_ast.AST, func: Callable[[py_ast.AST], None]):
    """
    Apply 'func' to ast_node (which is `ast.*` object)
    """
    for node in py_ast.walk(ast_node):
        func(node)


def simplify(codegen_ast: CodeGenAst, simplifier: Callable[[CodeGenAst, list[bool]], CodeGenAst]):
    changes = [True]

    # Wrap `simplifier` (which takes additional `changes` arg)
    # into function that take just `node`, as required by rewriting_traverse
    def rewriter(node):
        return simplifier(node, changes)

    while any(changes):
        changes[:] = []
        rewriting_traverse(codegen_ast, rewriter)
    return codegen_ast


def rewriting_traverse(
    node: CodeGenAstType | list | tuple | dict,
    func: Callable[[CodeGenAstType], CodeGenAstType],
):
    """
    Apply 'func' to node and all sub CodeGenAst nodes
    """
    if isinstance(node, (CodeGenAst, CodeGenAstList)):
        new_node = func(node)
        if new_node is not node:
            morph_into(node, new_node)
        for k in node.child_elements:
            rewriting_traverse(getattr(node, k), func)
    elif isinstance(node, (list, tuple)):
        for i in node:
            rewriting_traverse(i, func)
    elif isinstance(node, dict):
        for k, v in node.items():
            rewriting_traverse(k, func)
            rewriting_traverse(v, func)


def morph_into(item: object, new_item: object) -> None:
    # This naughty little function allows us to make `item` behave like
    # `new_item` in every way, except it maintains the identity of `item`, so
    # that we don't have to rewrite a tree of objects with new objects.
    item.__class__ = new_item.__class__
    item.__dict__ = new_item.__dict__


def empty_If() -> py_ast.If:
    """
    Create an empty If ast node. The `test` attribute
    must be added later.
    """
    return py_ast.If(test=None, orelse=[], **DEFAULT_AST_ARGS)  # type: ignore[reportArgumentType]
