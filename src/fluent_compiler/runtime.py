# Runtime functions for compiled messages
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Callable

from babel.core import Locale

from .errors import FluentCyclicReferenceError, FluentFormatError, FluentReferenceError
from .types import FluentNone, FluentType, fluent_date, fluent_number

__all__ = [
    "handle_argument_with_escaper",
    "handle_output_with_escaper",
    "handle_argument",
    "handle_output",
    "FluentCyclicReferenceError",
    "FluentReferenceError",
    "FluentFormatError",
    "FluentNone",
]


RETURN_TYPES = {
    "handle_argument": object,
    "handle_output": str,
    "FluentReferenceError": FluentReferenceError,
    "FluentFormatError": FluentFormatError,
    "FluentNone": FluentNone,
}


def handle_argument_with_escaper(
    arg: object,
    name: str,
    output_type: type,
    locale: Locale,
    errors: list[Exception],
) -> object:
    # This needs to be synced with resolver.handle_variable_reference
    if isinstance(arg, output_type):
        return arg
    if isinstance(arg, str):
        return arg
    elif isinstance(arg, (int, float, Decimal)):
        return fluent_number(arg)
    elif isinstance(arg, (date, datetime)):
        return fluent_date(arg)
    errors.append(TypeError(f"Unsupported external type: {name}, {type(arg)}"))
    return name


def handle_argument(arg: object, name: str, locale: Locale, errors: list[Exception]) -> object:
    # handle_argument_with_escaper specialized to null escaper
    # This needs to be synced with resolver.handle_variable_reference
    if isinstance(arg, str):
        return arg
    elif isinstance(arg, (int, float, Decimal)):
        return fluent_number(arg)
    elif isinstance(arg, (date, datetime)):
        return fluent_date(arg)
    errors.append(TypeError(f"Unsupported external type: {name}, {type(arg)}"))
    return name


def handle_output_with_escaper(
    val: object,
    output_type: type,
    escaper_escape: Callable,
    locale: Locale,
    errors: list[Exception],
) -> object:
    if isinstance(val, output_type):
        return val
    elif isinstance(val, str):
        return escaper_escape(val)
    elif isinstance(val, FluentType):
        return escaper_escape(val.format(locale))
    else:
        # The only way for this branch to run is whem functions return
        # objects of the wrong type.
        raise TypeError(f"Cannot handle object {val} of type {type(val).__name__}")


def handle_output(val: object, locale: Locale, errors: list[Exception]) -> str:
    # handle_output_with_escaper specialized to null_escaper
    if isinstance(val, str):
        return val
    elif isinstance(val, FluentType):
        return val.format(locale)
    else:
        # The only way for this branch to run is when functions return
        # objects of the wrong type.
        raise TypeError(f"Cannot handle object {val} of type {type(val).__name__}")
