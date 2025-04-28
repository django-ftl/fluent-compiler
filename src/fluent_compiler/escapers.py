from __future__ import annotations

from typing import TYPE_CHECKING, Callable, Final, Generic, Sequence, TypeVar

from attr import dataclass
from typing_extensions import Protocol, runtime_checkable

if TYPE_CHECKING:
    from .codegen import Expression
    from .compiler import CompilerEnvironment

from . import ast_compat as py_ast
from . import codegen


def identity(value):
    """
    Identity function.
    The function is also used as a sentinel value by the
    compiler for it to detect a no-op
    """
    return value


# Default string join function and sentinel value
def default_join(items: Sequence[str]) -> str:
    return "".join(items)


def select_always(message_id: str | None = None, **kwargs: object) -> bool:
    return True


T = TypeVar("T")


@runtime_checkable
class IsEscaper(Protocol[T]):
    output_type: Final[type[T]]
    name: Final[str]
    use_isolating: Final[bool | None]

    def select(self, message_id: str, **kwargs: object) -> bool:
        ...

    def escape(self, unescaped: str, /) -> T:
        ...

    def mark_escaped(self, value: str, /) -> T:
        ...

    def join(self, parts: Sequence[T], /) -> T:
        ...


@dataclass(frozen=True)
class Escaper(Generic[T]):
    select: Callable[..., bool]
    output_type: type[T]
    escape: Callable[[str], T]
    mark_escaped: Callable[[str], T]
    join: Callable[[Sequence[T]], T]
    name: str
    use_isolating: bool | None


class NullEscaper:
    # select = select_always
    # output_type = str
    # escape = identity
    # mark_escaped = identity
    # join = default_join
    def __init__(self) -> None:
        self.name = "null_escaper"
        self.use_isolating = None
        self.output_type = str

    def select(self, message_id: str, **kwargs: object) -> bool:
        return True

    def escape(self, unescaped: str) -> str:
        return unescaped

    def mark_escaped(self, value: str, /) -> str:
        return value

    def join(self, parts: Sequence[str], /) -> str:
        return "".join(parts)


null_escaper = NullEscaper()

# Some tests for the types above:
_1: IsEscaper[str] = NullEscaper()


_2: IsEscaper[str] = Escaper(
    name="x",
    use_isolating=None,
    select=lambda **kwargs: True,
    output_type=str,
    escape=lambda unescaped, /: unescaped,
    mark_escaped=lambda value, /: value,
    join="".join,
)


def escapers_compatible(
    outer_escaper: NullEscaper | RegisteredEscaper, inner_escaper: NullEscaper | RegisteredEscaper
) -> bool:
    # Messages with no escaper defined can always be used from other messages,
    # because the outer message will do the escaping, and the inner message will
    # always return a simple string which must be handle by all escapers.
    if inner_escaper.name == null_escaper.name:
        return True

    # Otherwise, however, since escapers could potentially build completely
    # different types of objects, we disallow any other mismatch.
    return outer_escaper.name == inner_escaper.name


def escaper_for_message(
    escapers: Sequence[RegisteredEscaper], message_id: str | None
) -> RegisteredEscaper | NullEscaper:
    for escaper in escapers:
        if escaper.select(message_id=message_id):
            return escaper

    return null_escaper


class RegisteredEscaper:
    """
    Escaper wrapper that encapsulates logic like knowing what the escaper
    functions are called in the compiler environment.
    """

    def __init__(self, escaper: IsEscaper, compiler_env: CompilerEnvironment):
        self._escaper = escaper
        self._compiler_env = compiler_env

    def __repr__(self):
        return f"<RegisteredEscaper {self.name}>"

    @property
    def select(self) -> Callable:
        return self._escaper.select

    @property
    def output_type(self) -> type:
        return self._escaper.output_type

    @property
    def escape(self) -> Callable:
        return self._escaper.escape

    @property
    def mark_escaped(self) -> Callable:
        return self._escaper.mark_escaped

    @property
    def join(self) -> Callable:
        return self._escaper.join

    @property
    def name(self) -> str:
        return self._escaper.name

    def get_reserved_names_with_properties(
        self,
    ) -> list[tuple[str, object, dict[str, object]]]:
        # escaper.output_type, escaper.mark_escaped, escaper.escape, escaper.join
        return [
            (self.output_type_name(), self._escaper.output_type, {}),
            (
                self.escape_name(),
                self._escaper.escape,
                {codegen.PROPERTY_RETURN_TYPE: self._escaper.output_type},
            ),
            (
                self.mark_escaped_name(),
                self._escaper.mark_escaped,
                {codegen.PROPERTY_RETURN_TYPE: self._escaper.output_type},
            ),
            (
                self.join_name(),
                self._escaper.join,
                {codegen.PROPERTY_RETURN_TYPE: self._escaper.output_type},
            ),
        ]

    def _prefix(self) -> str:
        idx = self._compiler_env.escapers.index(self)
        return f"escaper_{idx}_"

    def output_type_name(self) -> str:
        return f"{self._prefix()}_output_type"

    def mark_escaped_name(self) -> str:
        return f"{self._prefix()}_mark_escaped"

    def escape_name(self) -> str:
        return f"{self._prefix()}_escape"

    def join_name(self) -> str:
        return f"{self._prefix()}_join"

    @property
    def use_isolating(self) -> bool | None:
        return getattr(self._escaper, "use_isolating", None)


class EscaperJoin(codegen.StringJoinBase):
    def __init__(self, parts: Sequence[Expression], escaper: RegisteredEscaper, scope: codegen.Scope):
        super().__init__(parts)
        self.type = escaper.output_type
        self.escaper = escaper
        self.scope = scope

    def as_ast(self) -> py_ast.expr:
        if self.escaper.join is default_join:
            return super().as_ast()
        else:
            return codegen.FunctionCall(
                self.escaper.join_name(),
                [codegen.List(self.parts)],
                {},
                self.scope,
                expr_type=self.type,
            ).as_ast()

    @classmethod
    def build_with_escaper(
        cls, parts: Sequence[Expression], escaper: RegisteredEscaper | NullEscaper, scope: codegen.Scope
    ) -> codegen.CodeGenAst:
        if isinstance(escaper, NullEscaper):
            return codegen.StringJoin.build(parts)

        new_parts = []
        for part in parts:
            handled = False
            if len(new_parts) > 0:
                last_part = new_parts[-1]
                # Merge string literals wrapped in mark_escaped calls
                if (
                    isinstance(last_part, codegen.FunctionCall)
                    and last_part.function_name == escaper.mark_escaped_name()
                    and (isinstance(last_part_args0 := last_part.args[0], codegen.String))
                ) and (
                    isinstance(part, codegen.FunctionCall)
                    and part.function_name == escaper.mark_escaped_name()
                    and isinstance(part_args0 := part.args[0], codegen.String)
                ):
                    new_parts[-1] = codegen.FunctionCall(
                        last_part.function_name,
                        [codegen.String(last_part_args0.string_value + part_args0.string_value)],
                        {},
                        scope,
                    )
                    handled = True

            if not handled:
                new_parts.append(part)

        parts = new_parts
        if len(parts) == 1:
            return parts[0]

        return cls(parts, escaper, scope)
