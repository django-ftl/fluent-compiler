from typing import Any, Callable, Dict, List, Optional

from fluent_compiler.escapers import Escaper

from .compiler import CompilationErrorItem, compile_messages
from .resource import FtlResource
from .utils import ATTRIBUTE_SEPARATOR, TERM_SIGIL


class FluentBundle:
    """
    A FluentBundle is a single-language store of translations.  It can
    format translation units (entities) to strings.

    Use `FluentBundle.format` to retrieve translation units from a context.
    Translations can contain references to other entities or external arguments,
    conditional logic in form of select expressions, traits which describe their
    grammatical features, and can use Fluent builtins. See the documentation of
    the Fluent syntax for more information.

    """

    def __init__(
        self,
        locale: str,
        resources: List[FtlResource],
        functions: Optional[Dict[str, Callable]] = None,
        use_isolating: bool = True,
        escapers: Optional[List[Escaper]] = None,
    ):
        self.locale = locale
        compiled_ftl = compile_messages(
            locale,
            resources,
            use_isolating=use_isolating,
            functions=functions,
            escapers=escapers,
        )
        self._compiled_messages = compiled_ftl.message_functions
        self._compilation_errors = compiled_ftl.errors

    @classmethod
    def from_string(
        cls,
        locale: str,
        text: str,
        functions: Optional[Dict[str, Callable]] = None,
        use_isolating: bool = True,
        escapers: Optional[List[Escaper]] = None,
    ) -> "FluentBundle":
        return cls(
            locale,
            [FtlResource.from_string(text)],
            use_isolating=use_isolating,
            functions=functions,
            escapers=escapers,
        )

    @classmethod
    def from_files(cls, locale, filenames, functions=None, use_isolating=True, escapers=None):
        return cls(
            locale,
            [FtlResource.from_file(f) for f in filenames],
            use_isolating=use_isolating,
            functions=functions,
            escapers=escapers,
        )

    def has_message(self, message_id: str) -> bool:
        if message_id.startswith(TERM_SIGIL) or ATTRIBUTE_SEPARATOR in message_id:
            return False
        return message_id in self._compiled_messages

    def format(self, message_id: str, args: Optional[Any] = None) -> Any:
        errors = []
        return self._compiled_messages[message_id](args, errors), errors

    def check_messages(self) -> List[CompilationErrorItem]:
        return self._compilation_errors
