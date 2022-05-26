import builtins
import inspect
import keyword
import re

from fluent.syntax.ast import Term, TermReference

from .errors import FluentFormatError

TERM_SIGIL = "-"
ATTRIBUTE_SEPARATOR = "."


class Any:
    pass


Any = Any()


# On Python 3 we could get away with just using a class, but on Python 2
# functions defined in the class body get wrapped with UnboundMethod, which
# causes problems.

try:
    from types import SimpleNamespace
except ImportError:
    # Python 2 fallback
    class SimpleNamespace:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

        def __repr__(self):
            keys = sorted(self.__dict__)
            items = (f"{k}={self.__dict__[k]!r}" for k in keys)
            return f"{type(self).__name__}({', '.join(items)})"

        def __eq__(self, other):
            return self.__dict__ == other.__dict__


# From spec:
#    NamedArgument ::= Identifier blank? ":" blank? (StringLiteral | NumberLiteral)
#    Identifier ::= [a-zA-Z] [a-zA-Z0-9_-]*

NAMED_ARG_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9_-]*$")


def allowable_keyword_arg_name(name):
    # We limit to what Fluent allows for NamedArgument - Python allows anything
    # if you use **kwarg call and receiving syntax.
    return NAMED_ARG_RE.match(name)


def ast_to_id(ast):
    """
    Returns a string reference for a Term or Message
    """
    if isinstance(ast, Term):
        return TERM_SIGIL + ast.id.name
    return ast.id.name


def attribute_ast_to_id(attribute, parent_ast):
    """
    Returns a string reference for an Attribute, given Attribute and parent Term or Message
    """
    return "".join([ast_to_id(parent_ast), ATTRIBUTE_SEPARATOR, attribute.id.name])


def allowable_name(ident, for_method=False, allow_builtin=False):

    if keyword.iskeyword(ident):
        return False

    if not (for_method or allow_builtin):
        if ident in dir(builtins):
            return False

    if not ident.isidentifier():
        return False

    return True


def inspect_function_args(function, name, errors):
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
        Any
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
        Any
        if any(p.kind == inspect.Parameter.VAR_KEYWORD for p in parameters)
        else [p.name for p in parameters if p.default != inspect.Parameter.empty]
    )
    return sanitize_function_args((positional, keywords), name, errors)


def args_match(function_name, args, kwargs, arg_spec):
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
        if (allowed_kwargs is Any and allowable_keyword_arg_name(kwarg_name)) or (
            allowed_kwargs is not Any and kwarg_name in allowed_kwargs
        ):
            sanitized_kwargs[kwarg_name] = kwarg_val
        else:
            errors.append(TypeError(f"{function_name}() got an unexpected keyword argument '{kwarg_name}'"))
    if positional_arg_count is Any:
        sanitized_args = args
    else:
        sanitized_args = tuple(args[0:positional_arg_count])
        len_args = len(args)
        if len_args > positional_arg_count:
            errors.append(
                TypeError(
                    "{}() takes {} positional arguments but {} were given".format(
                        function_name, positional_arg_count, len_args
                    )
                )
            )
        elif len_args < positional_arg_count:
            errors.append(
                TypeError(
                    "{}() takes {} positional arguments but {} were given".format(
                        function_name, positional_arg_count, len_args
                    )
                )
            )
            match = False

    return (match, sanitized_args, sanitized_kwargs, errors)


def reference_to_id(ref, ignore_attributes=False):
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
        return "".join([start, ATTRIBUTE_SEPARATOR, ref.attribute.name])
    return start


def sanitize_function_args(arg_spec, name, errors):
    """
    Check function arg spec is legitimate, returning a cleaned
    up version, and adding any errors to errors list.
    """
    positional_args, keyword_args = arg_spec
    if keyword_args is Any:
        cleaned_kwargs = keyword_args
    else:
        cleaned_kwargs = []
        for kw in keyword_args:
            if allowable_keyword_arg_name(kw):
                cleaned_kwargs.append(kw)
            else:
                errors.append(FluentFormatError(f"{name}() has invalid keyword argument name '{kw}'"))
    return (positional_args, cleaned_kwargs)


def span_to_position(span, source_text):
    start = span.start
    relevant = source_text[0:start]
    row = relevant.count("\n") + 1
    col = len(relevant) - relevant.rfind("\n")
    return row, col


def display_location(filename, position):
    row, col = position
    return f"{filename if filename else '<string>'}:{row}:{col}"
