from __future__ import absolute_import, unicode_literals

from collections import OrderedDict

import attr
import babel
import babel.numbers
import babel.plural
from fluent.syntax import FluentParser
from fluent.syntax.ast import Junk, Message, Term

from .builtins import BUILTINS
from .compiler import compile_messages
from .errors import FluentDuplicateMessageId, FluentJunkFound
from .utils import ATTRIBUTE_SEPARATOR, TERM_SIGIL, ast_to_id, display_location, span_to_position


class FluentBundle(object):
    """
    Message bundles are single-language stores of translations.  They are
    responsible for parsing translation resources in the Fluent syntax and can
    format translation units (entities) to strings.

    Always use `FluentBundle.format` to retrieve translation units from
    a context.  Translations can contain references to other entities or
    external arguments, conditional logic in form of select expressions, traits
    which describe their grammatical features, and can use Fluent builtins.
    See the documentation of the Fluent syntax for more information.
    """
    def __init__(self, locale, resources, functions=None, use_isolating=True, escapers=None):
        self.locale = locale
        _functions = BUILTINS.copy()
        if functions:
            _functions.update(functions)
        self._functions = _functions
        self.use_isolating = use_isolating
        self._parsing_issues = []
        self._babel_locale = self._get_babel_locale()
        self._plural_form = babel.plural.to_python(self._babel_locale.plural_form)
        self._messages_and_terms = OrderedDict()
        for resource in resources:
            self._add_resource(resource)
        self._compiled_messages, self._compilation_errors = compile_messages(
            self._messages_and_terms,
            self._babel_locale,
            use_isolating=self.use_isolating,
            functions=self._functions,
            escapers=escapers)

    @classmethod
    def from_string(cls, locale, text, functions=None, use_isolating=True, escapers=None):
        return cls(
            locale,
            [FtlResource(text)],
            use_isolating=use_isolating,
            functions=functions,
            escapers=escapers
        )

    @classmethod
    def from_files(cls, locale, filenames, functions=None, use_isolating=True, escapers=None):
        return cls(
            locale,
            [FtlResource.from_file(f) for f in filenames],
            use_isolating=use_isolating,
            functions=functions,
            escapers=escapers
        )

    def _add_resource(self, ftl_resource):
        parser = FluentParser()
        resource = parser.parse(ftl_resource.text)
        for item in resource.body:
            if isinstance(item, (Message, Term)):
                full_id = ast_to_id(item)
                if full_id in self._messages_and_terms:
                    self._parsing_issues.append((full_id, FluentDuplicateMessageId(
                        "Additional definition for '{0}' discarded.".format(full_id))))
                else:
                    # Decorate with ftl_resource for better error messages later
                    item.ftl_resource = ftl_resource
                    for attribute in item.attributes:
                        attribute.ftl_resource = ftl_resource
                    self._messages_and_terms[full_id] = item
            elif isinstance(item, Junk):
                self._parsing_issues.append(
                    (None, FluentJunkFound("Junk found:\n" +
                                           '\n'.join('  {0}: {1}'.format(
                                               display_location(
                                                   ftl_resource.filename,
                                                   span_to_position(a.span, ftl_resource.text)
                                               ), a.message)
                                                     for a in item.annotations),
                                           item.annotations)))

    def has_message(self, message_id):
        if message_id.startswith(TERM_SIGIL) or ATTRIBUTE_SEPARATOR in message_id:
            return False
        return message_id in self._messages_and_terms

    def _get_babel_locale(self):
        for l in self.locale.split(','):
            try:
                return babel.Locale.parse(l.replace('-', '_'))
            except babel.UnknownLocaleError:
                continue
        # TODO - log error
        return babel.Locale.default()

    def format(self, message_id, args=None):
        errors = []
        return self._compiled_messages[message_id](args, errors), errors

    def check_messages(self):
        return self._parsing_issues + self._compilation_errors


@attr.s
class FtlResource(object):
    '''
    Represents an (unparsed) FTL file (contents and optional filename)
    '''
    text = attr.ib()
    filename = attr.ib(default=None)

    @classmethod
    def from_file(cls, filename):
        return cls(text=open(filename).read(), filename=filename)
