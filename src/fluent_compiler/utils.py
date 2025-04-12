from __future__ import annotations

import builtins
import inspect
import keyword
import re
from typing import TYPE_CHECKING, Any, Callable, List, Tuple, Union

from fluent.syntax.ast import Attribute, Message, MessageReference, Span, Term, TermReference

from .compat import TypeAlias
from .errors import FluentFormatError

TERM_SIGIL = "-"
ATTRIBUTE_SEPARATOR = "."

if TYPE_CHECKING:
    from .codegen import FunctionCall, String, VariableReference2


class AnyArgType:
    pass


AnyArg = AnyArgType()


# From spec:
#    NamedArgument ::= Identifier blank? ":" blank? (StringLiteral | NumberLiteral)
#    Identifier ::= [a-zA-Z] [a-zA-Z0-9_-]*

NAMED_ARG_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9_-]*$")


def allowable_keyword_arg_name(name: str) -> re.Match | None:
    # We limit to what Fluent allows for NamedArgument - Python allows anything
    # if you use **kwarg call and receiving syntax.
    return NAMED_ARG_RE.match(name)


def ast_to_id(ast: Message | Term) -> str:
    """
    Returns a string reference for a Term or Message
    """
    if isinstance(ast, Term):
        return TERM_SIGIL + ast.id.name
    return ast.id.name


def attribute_ast_to_id(attribute: Attribute, parent_ast: Message | Term) -> str:
    """
    Returns a string reference for an Attribute, given Attribute and parent Term or Message
    """
    return "".join([ast_to_id(parent_ast), ATTRIBUTE_SEPARATOR, attribute.id.name])


def allowable_name(ident: str, for_method: bool = False, allow_builtin: bool = False):
    if keyword.iskeyword(ident):
        return False

    if not (for_method or allow_builtin):
        if ident in dir(builtins):
            return False

    if not ident.isidentifier():
        return False

    return True


FunctionArgSpec: TypeAlias = Tuple[Union[int, AnyArgType], Union[List[str], AnyArgType]]


def inspect_function_args(function: Callable, name: str, errors: list[Any]) -> FunctionArgSpec:
    """
    For a Python function, returns a 2 tuple containing:
    (number of positional args or Any,
    set of keyword args or Any)

    Keyword args are defined as those with default values.
    'Keyword only' args with no default values are not supported.
    """
    if hasattr(function, "ftl_arg_spec"):
        return sanitize_function_args(function.ftl_arg_spec, name, errors)
    sig = inspect.signature(function)
    parameters = list(sig.parameters.values())

    positional = (
        AnyArg
        if any(p.kind == inspect.Parameter.VAR_POSITIONAL for p in parameters)
        else len(
            list(
                p
                for p in parameters
                if p.default == inspect.Parameter.empty and p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD
            )
        )
    )

    keywords = (
        AnyArg
        if any(p.kind == inspect.Parameter.VAR_KEYWORD for p in parameters)
        else [p.name for p in parameters if p.default != inspect.Parameter.empty]
    )
    return sanitize_function_args((positional, keywords), name, errors)


def args_match(
    function_name: str,
    args: list[VariableReference2 | Any | FunctionCall | String],
    kwargs: dict[str, FunctionCall | String],
    arg_spec: FunctionArgSpec,
) -> Any:
    """
    Checks the passed in args/kwargs against the function arg_spec
    and returns data for calling the function correctly.

    Return value is a tuple

    (match, santized args, santized keyword args, errors)

    match is False if the function should not be called at all.

    """
    # For the errors returned, we try to match the TypeError raised by Python
    # when calling functions with wrong arguments, for the sake of something
    # recognisable.
    errors = []
    sanitized_kwargs = {}
    positional_arg_count, allowed_kwargs = arg_spec
    match = True
    for kwarg_name, kwarg_val in kwargs.items():
        if (allowed_kwargs is AnyArg and allowable_keyword_arg_name(kwarg_name)) or (
            allowed_kwargs is not AnyArg and kwarg_name in allowed_kwargs
        ):
            sanitized_kwargs[kwarg_name] = kwarg_val
        else:
            errors.append(TypeError(f"{function_name}() got an unexpected keyword argument '{kwarg_name}'"))
    if positional_arg_count is AnyArg:
        sanitized_args = args
    else:
        sanitized_args = tuple(args[0:positional_arg_count])
        len_args = len(args)
        if len_args > positional_arg_count:
            errors.append(
                TypeError(
                    f"{function_name}() takes {positional_arg_count} positional arguments but {len_args} were given"
                )
            )
        elif len_args < positional_arg_count:
            errors.append(
                TypeError(
                    f"{function_name}() takes {positional_arg_count} positional arguments but {len_args} were given"
                )
            )
            match = False

    return (match, sanitized_args, sanitized_kwargs, errors)


def reference_to_id(ref: TermReference | MessageReference, ignore_attributes: bool = False) -> str:
    """
    Returns a string reference for a MessageReference or TermReference
    AST node.

    e.g.
       message
       message.attr
       -term
       -term.attr
    """
    if isinstance(ref, TermReference):
        start = TERM_SIGIL + ref.id.name
    else:
        start = ref.id.name

    if not ignore_attributes and ref.attribute:
        return f"{start}{ATTRIBUTE_SEPARATOR}{ref.attribute.name}"
    return start


def sanitize_function_args(arg_spec: Any, name: str, errors: list[Any]) -> FunctionArgSpec:
    """
    Check function arg spec is legitimate, returning a cleaned
    up version, and adding any errors to errors list.
    """
    positional_args, keyword_args = arg_spec
    if keyword_args is AnyArg:
        cleaned_kwargs = keyword_args
    else:
        cleaned_kwargs = []
        for kw in keyword_args:
            if allowable_keyword_arg_name(kw):
                cleaned_kwargs.append(kw)
            else:
                errors.append(FluentFormatError(f"{name}() has invalid keyword argument name '{kw}'"))
    return (positional_args, cleaned_kwargs)


def span_to_position(span: Span, source_text: str) -> tuple[int, int]:
    start = span.start
    relevant = source_text[0:start]
    row = relevant.count("\n") + 1
    col = len(relevant) - relevant.rfind("\n")
    return row, col


def display_location(filename: str | None, position: tuple[int, int]) -> str:
    row, col = position
    return f"{filename if filename else '<string>'}:{row}:{col}"
