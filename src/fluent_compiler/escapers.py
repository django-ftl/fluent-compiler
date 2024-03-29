from types import SimpleNamespace

from . import codegen


def identity(value):
    """
    Identity function.
    The function is also used as a sentinel value by the
    compiler for it to detect a no-op
    """
    return value


# Default string join function and sentinel value
default_join = "".join


def select_always(message_id=None, **kwargs):
    return True


null_escaper = SimpleNamespace(
    select=select_always,
    output_type=str,
    escape=identity,
    mark_escaped=identity,
    join=default_join,
    name="null_escaper",
    use_isolating=None,
)


def escapers_compatible(outer_escaper, inner_escaper):
    # Messages with no escaper defined can always be used from other messages,
    # because the outer message will do the escaping, and the inner message will
    # always return a simple string which must be handle by all escapers.
    if inner_escaper.name == null_escaper.name:
        return True

    # Otherwise, however, since escapers could potentially build completely
    # different types of objects, we disallow any other mismatch.
    return outer_escaper.name == inner_escaper.name


def escaper_for_message(escapers, message_id):
    if escapers is not None:
        for escaper in escapers:
            if escaper.select(message_id=message_id):
                return escaper

    return null_escaper


class RegisteredEscaper:
    """
    Escaper wrapper that encapsulates logic like knowing what the escaper
    functions are called in the compiler environment.
    """

    def __init__(self, escaper, compiler_env):
        self._escaper = escaper
        self._compiler_env = compiler_env

    def __repr__(self):
        return f"<RegisteredEscaper {self.name}>"

    @property
    def select(self):
        return self._escaper.select

    @property
    def output_type(self):
        return self._escaper.output_type

    @property
    def escape(self):
        return self._escaper.escape

    @property
    def mark_escaped(self):
        return self._escaper.mark_escaped

    @property
    def join(self):
        return self._escaper.join

    @property
    def name(self):
        return self._escaper.name

    def get_reserved_names_with_properties(self):
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

    def _prefix(self):
        idx = self._compiler_env.escapers.index(self)
        return f"escaper_{idx}_"

    def output_type_name(self):
        return f"{self._prefix()}_output_type"

    def mark_escaped_name(self):
        return f"{self._prefix()}_mark_escaped"

    def escape_name(self):
        return f"{self._prefix()}_escape"

    def join_name(self):
        return f"{self._prefix()}_join"

    @property
    def use_isolating(self):
        return getattr(self._escaper, "use_isolating", None)


class EscaperJoin(codegen.StringJoin):
    def __init__(self, parts, escaper, scope):
        super().__init__(parts)
        self.type = escaper.output_type
        self.escaper = escaper
        self.scope = scope

    def as_ast(self):
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
    def build(cls, parts, escaper, scope):
        if escaper.name == null_escaper.name:
            return codegen.StringJoin.build(parts)

        new_parts = []
        for part in parts:
            handled = False
            if len(new_parts) > 0:
                last_part = new_parts[-1]
                # Merge string literals wrapped in mark_escaped calls
                if all(
                    (
                        isinstance(p, codegen.FunctionCall)
                        and p.function_name == escaper.mark_escaped_name()
                        and isinstance(p.args[0], codegen.String)
                    )
                    for p in [last_part, part]
                ):
                    new_parts[-1] = codegen.FunctionCall(
                        last_part.function_name,
                        [codegen.String(last_part.args[0].string_value + part.args[0].string_value)],
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
