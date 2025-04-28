import operator
from functools import reduce
from typing import Sequence

import pytest
from bs4 import BeautifulSoup
from markdown import markdown
from markupsafe import Markup, escape

from fluent_compiler.bundle import FluentBundle
from fluent_compiler.escapers import IsEscaper

from ..utils import dedent_ftl


def assertTypeAndValueEqual(val1, val2):
    assert val1 == val2
    assert type(val1) is type(val2)


# An escaper for MarkupSafe with instrumentation so we can check behaviour
class HtmlEscaper:
    name = "HtmlEscaper"
    output_type = Markup
    use_isolating = False

    def select(self, message_id: str, **kwargs: object):
        return message_id.endswith("-html")

    def mark_escaped(self, escaped: str) -> Markup:
        assert type(escaped) is str
        return Markup(escaped)

    def escape(self, unescaped: str) -> Markup:
        return escape(unescaped)

    def join(self, parts: Sequence[Markup]) -> Markup:
        for p in parts:
            assert type(p) is Markup
        return Markup("").join(parts)


# A very basic Markdown 'escaper'. The main point of this implementation is
# that, unlike HtmlEscaper above, the output type is not a subclass of
# str, in order to test the implementation handles this properly.


# We also test whether the implementation can handle subclasses
class Markdown:
    def __init__(self, text):
        if isinstance(text, Markdown):
            self.text = text.text
        else:
            self.text = text

    def __eq__(self, other):
        return isinstance(other, Markdown) and self.text == other.text

    def __add__(self, other):
        assert isinstance(other, Markdown)
        return Markdown(self.text + other.text)

    def __repr__(self):
        return f"Markdown({repr(self.text)})"


class LiteralMarkdown(Markdown):
    pass


class StrippedMarkdown(Markdown):
    def __init__(self, text):
        if isinstance(text, StrippedMarkdown):
            self.text = text.text
        else:
            super().__init__(text)
            self.text = BeautifulSoup(markdown(self.text), "html.parser").get_text()


empty_markdown = Markdown("")


class MarkdownEscaper:
    name = "MarkdownEscaper"
    output_type = Markdown
    use_isolating = False

    def select(self, message_id: str, **kwargs: object):
        return message_id.endswith("-md")

    def mark_escaped(self, escaped):
        assert type(escaped) is str
        return LiteralMarkdown(escaped)

    def escape(self, unescaped):
        # We don't do escaping, just stripping
        if isinstance(unescaped, Markdown):
            return unescaped
        return StrippedMarkdown(unescaped)

    def join(self, parts):
        for p in parts:
            assert isinstance(p, Markdown)
        return reduce(operator.add, parts, empty_markdown)


@pytest.fixture(scope="session")
def html_escaping_bundle() -> FluentBundle:
    escaper: IsEscaper[Markup] = HtmlEscaper()

    # A function that outputs '> ' that needs to be escaped. Part of the
    # point of this is to ensure that escaping is being done at the correct
    # point - it is no good to escape string input when it enters, it has to
    # be done at the end of the formatting process.
    def QUOTE(arg):
        return "\n" + "\n".join(f"> {line}" for line in arg.split("\n"))

    return FluentBundle.from_string(
        "en-US",
        dedent_ftl(
            """
        not-html-message = x < y

        simple-html =  This is <b>great</b>.

        argument-html = This <b>thing</b> is called { $arg }.

        -term-html = <b>Jack &amp; Jill</b>

        -term-plain = Jack & Jill

        references-html-term-html = { -term-html } are <b>great!</b>

        references-plain-term-html = { -term-plain } are <b>great!</b>

        references-html-term-plain = { -term-html } are great!

        attribute-argument-html = A <a href="{ $url }">link to { $place }</a>

        compound-message-html = A message about { $arg }. { argument-html }

        function-html = You said: { QUOTE($text) }

        parent-plain = Some stuff
             .attr-html = Some <b>HTML</b> stuff
             .attr-plain = This & That

        references-html-message-plain = Plain. { simple-html }

        references-html-message-attr-plain = Plain. { parent-plain.attr-html }

        references-html-message-attr-html = <b>HTML</b>. { parent-plain.attr-html }

        references-plain-message-attr-html = <b>HTML</b>. { parent-plain.attr-plain }

        -brand-plain = { $variant ->
             [short] A&B
            *[long]  A & B
         }

        -brand-html = { $variant ->
             [superscript] CoolBrand<sup>2</sup>
            *[normal]      CoolBrand2
         }

        references-html-variant-plain = { -brand-html(variant: "superscript") } is cool

        references-html-variant-html = { -brand-html(variant: "superscript") } is cool

        references-plain-variant-plain = { -brand-plain(variant: "short") } is awesome

        references-plain-variant-html = { -brand-plain(variant: "short") } is awesome
        """
        ),
        use_isolating=True,
        functions={"QUOTE": QUOTE},
        escapers=[escaper],
    )


def test_html_select_false(html_escaping_bundle: FluentBundle):
    val, errs = html_escaping_bundle.format("not-html-message")
    assertTypeAndValueEqual(val, "x < y")


def test_html_simple(html_escaping_bundle: FluentBundle):
    val, errs = html_escaping_bundle.format("simple-html")
    assertTypeAndValueEqual(val, Markup("This is <b>great</b>."))
    assert errs == []


def test_html_argument_is_escaped(html_escaping_bundle: FluentBundle):
    val, errs = html_escaping_bundle.format("argument-html", {"arg": "Jack & Jill"})
    assertTypeAndValueEqual(val, Markup("This <b>thing</b> is called Jack &amp; Jill."))
    assert errs == []


def test_html_argument_already_escaped(html_escaping_bundle: FluentBundle):
    val, errs = html_escaping_bundle.format("argument-html", {"arg": Markup("<b>Jack</b>")})
    assertTypeAndValueEqual(val, Markup("This <b>thing</b> is called <b>Jack</b>."))
    assert errs == []


def test_included_html_term(html_escaping_bundle: FluentBundle):
    val, errs = html_escaping_bundle.format("references-html-term-html")
    assertTypeAndValueEqual(val, Markup("<b>Jack &amp; Jill</b> are <b>great!</b>"))
    assert errs == []


def test_included_plain_term(html_escaping_bundle: FluentBundle):
    val, errs = html_escaping_bundle.format("references-plain-term-html")
    assertTypeAndValueEqual(val, Markup("Jack &amp; Jill are <b>great!</b>"))
    assert errs == []


def test_included_html_term_from_plain(html_escaping_bundle: FluentBundle):
    val, errs = html_escaping_bundle.format("references-html-term-plain")
    assertTypeAndValueEqual(val, "\u2068-term-html\u2069 are great!")
    assert type(errs[0]) is TypeError


def test_html_compound_message(html_escaping_bundle: FluentBundle):
    val, errs = html_escaping_bundle.format("compound-message-html", {"arg": "Jack & Jill"})
    assertTypeAndValueEqual(
        val,
        Markup("A message about Jack &amp; Jill. " "This <b>thing</b> is called Jack &amp; Jill."),
    )
    assert errs == []


def test_html_function(html_escaping_bundle: FluentBundle):
    val, errs = html_escaping_bundle.format("function-html", {"text": "Jack & Jill"})
    assertTypeAndValueEqual(val, Markup("You said: \n&gt; Jack &amp; Jill"))
    assert errs == []


def test_html_plain_parent(html_escaping_bundle: FluentBundle):
    val, errs = html_escaping_bundle.format("parent-plain")
    assertTypeAndValueEqual(val, "Some stuff")
    assert errs == []


def test_html_attribute(html_escaping_bundle: FluentBundle):
    val, errs = html_escaping_bundle.format("parent-plain.attr-html")
    assertTypeAndValueEqual(val, Markup("Some <b>HTML</b> stuff"))
    assert errs == []


def test_html_message_reference_from_plain(html_escaping_bundle: FluentBundle):
    val, errs = html_escaping_bundle.format("references-html-message-plain")
    assertTypeAndValueEqual(val, "Plain. \u2068simple-html\u2069")
    assert len(errs) == 1
    assert type(errs[0]) is TypeError


# Message attr references
def test_html_message_attr_reference_from_plain(html_escaping_bundle: FluentBundle):
    val, errs = html_escaping_bundle.format("references-html-message-attr-plain")
    assertTypeAndValueEqual(val, "Plain. \u2068parent-plain.attr-html\u2069")
    assert len(errs) == 1
    assert type(errs[0]) is TypeError


def test_html_message_attr_reference_from_html(html_escaping_bundle: FluentBundle):
    val, errs = html_escaping_bundle.format("references-html-message-attr-html")
    assertTypeAndValueEqual(val, Markup("<b>HTML</b>. Some <b>HTML</b> stuff"))
    assert errs == []


def test_plain_message_attr_reference_from_html(html_escaping_bundle: FluentBundle):
    val, errs = html_escaping_bundle.format("references-plain-message-attr-html")
    assertTypeAndValueEqual(val, Markup("<b>HTML</b>. This &amp; That"))
    assert errs == []


# Term variant references
def test_html_variant_from_plain(html_escaping_bundle: FluentBundle):
    val, errs = html_escaping_bundle.format("references-html-variant-plain")
    assertTypeAndValueEqual(val, "\u2068-brand-html\u2069 is cool")
    assert len(errs) == 1
    assert type(errs[0]) is TypeError


def test_html_variant_from_html(html_escaping_bundle: FluentBundle):
    val, errs = html_escaping_bundle.format("references-html-variant-html")
    assertTypeAndValueEqual(val, Markup("CoolBrand<sup>2</sup> is cool"))
    assert errs == []


def test_html_plain_variant_from_plain(html_escaping_bundle: FluentBundle):
    val, errs = html_escaping_bundle.format("references-plain-variant-plain")
    assertTypeAndValueEqual(val, "\u2068A&B\u2069 is awesome")
    assert errs == []


def test_plain_variant_from_html(html_escaping_bundle: FluentBundle):
    val, errs = html_escaping_bundle.format("references-plain-variant-html")
    assertTypeAndValueEqual(val, Markup("A&amp;B is awesome"))
    assert errs == []


def test_use_isolating(html_escaping_bundle: FluentBundle):
    val, errs = html_escaping_bundle.format(
        "attribute-argument-html", {"url": "http://example.com", "place": "A Place"}
    )
    assertTypeAndValueEqual(val, Markup('A <a href="http://example.com">link to A Place</a>'))


@pytest.fixture(scope="session")
def markdown_escaping_bundle() -> FluentBundle:
    escaper: IsEscaper[Markdown] = MarkdownEscaper()

    # This QUOTE function outputs Markdown that should not be removed.
    def QUOTE(arg):
        return Markdown("\n" + "\n".join(f"> {line}" for line in arg.split("\n")))

    return FluentBundle.from_string(
        "en-US",
        dedent_ftl(
            """
        not-md-message = **some text**

        simple-md =  This is **great**

        argument-md = This **thing** is called { $arg }.

        -term-md = **Jack** & __Jill__

        -term-plain = **Jack & Jill**

        term-md-ref-md = { -term-md } are **great!**

        term-plain-ref-md = { -term-plain } are **great!**

        embedded-argument-md = A [link to { $place }]({ $url })

        compound-message-md = A message about { $arg }. { argument-md }

        function-md = You said: { QUOTE($text) }

        parent-plain = Some stuff
             .attr-md = Some **Markdown** stuff
             .attr-plain = This and **That**

        references-md-message-plain = Plain. { simple-md }

        references-md-attr-plain = Plain. { parent-plain.attr-md }

        references-md-attr-md = **Markdown**. { parent-plain.attr-md }

        references-plain-attr-md = **Markdown**. { parent-plain.attr-plain }

        -brand-plain = { $variant ->
             [short] *A&B*
            *[long]  *A & B*
         }

        -brand-md = { $variant ->
             [bolded]  CoolBrand **2**
            *[normal]  CoolBrand2
         }

        references-md-variant-plain = { -brand-md(variant: "bolded") } is cool

        references-md-variant-md = { -brand-md(variant: "bolded") } is cool

        references-plain-variant-plain = { -brand-plain(variant: "short") } is awesome

        references-plain-variant-md = { -brand-plain(variant: "short") } is awesome
        """
        ),
        use_isolating=False,
        functions={"QUOTE": QUOTE},
        escapers=[escaper],
    )


def test_strip_markdown():
    assert StrippedMarkdown("**Some bolded** and __italic__ text") == Markdown("Some bolded and italic text")
    assert (
        StrippedMarkdown(
            """

> A quotation
> about something
        """
        )
        == Markdown("\nA quotation\nabout something\n")
    )


def test_md_select_false(markdown_escaping_bundle: FluentBundle):
    val, errs = markdown_escaping_bundle.format("not-md-message")
    assert val == "**some text**"


def test_md_simple(markdown_escaping_bundle: FluentBundle):
    val, errs = markdown_escaping_bundle.format("simple-md")
    assert val == Markdown("This is **great**")
    assert errs == []


def test_md_argument_is_escaped(markdown_escaping_bundle: FluentBundle):
    val, errs = markdown_escaping_bundle.format("argument-md", {"arg": "**Jack**"})
    assert val == Markdown("This **thing** is called Jack.")
    assert errs == []


def test_md_argument_already_escaped(markdown_escaping_bundle: FluentBundle):
    val, errs = markdown_escaping_bundle.format("argument-md", {"arg": Markdown("**Jack**")})
    assert val == Markdown("This **thing** is called **Jack**.")
    assert errs == []


def test_included_md(markdown_escaping_bundle: FluentBundle):
    val, errs = markdown_escaping_bundle.format("term-md-ref-md")
    assert val == Markdown("**Jack** & __Jill__ are **great!**")
    assert errs == []


def test_included_plain(markdown_escaping_bundle: FluentBundle):
    val, errs = markdown_escaping_bundle.format("term-plain-ref-md")
    assert val == Markdown("Jack & Jill are **great!**")
    assert errs == []


def test_md_compound_message(markdown_escaping_bundle: FluentBundle):
    val, errs = markdown_escaping_bundle.format("compound-message-md", {"arg": "**Jack & Jill**"})
    assert val == Markdown("A message about Jack & Jill. " "This **thing** is called Jack & Jill.")
    assert errs == []


def test_md_function(markdown_escaping_bundle: FluentBundle):
    val, errs = markdown_escaping_bundle.format("function-md", {"text": "Jack & Jill"})
    assert val == Markdown("You said: \n> Jack & Jill")
    assert errs == []


def test_md_plain_parent(markdown_escaping_bundle: FluentBundle):
    val, errs = markdown_escaping_bundle.format("parent-plain")
    assert val == "Some stuff"
    assert errs == []


def test_md_attribute(markdown_escaping_bundle: FluentBundle):
    val, errs = markdown_escaping_bundle.format("parent-plain.attr-md")
    assert val == Markdown("Some **Markdown** stuff")
    assert errs == []


def test_md_message_reference_from_plain(markdown_escaping_bundle: FluentBundle):
    val, errs = markdown_escaping_bundle.format("references-md-message-plain")
    assert val == "Plain. simple-md"
    assert len(errs) == 1
    assert type(errs[0]) is TypeError


def test_md_attr_reference_from_plain(markdown_escaping_bundle: FluentBundle):
    val, errs = markdown_escaping_bundle.format("references-md-attr-plain")
    assert val == "Plain. parent-plain.attr-md"
    assert len(errs) == 1
    assert type(errs[0]) is TypeError


def test_md_reference_from_md(markdown_escaping_bundle: FluentBundle):
    val, errs = markdown_escaping_bundle.format("references-md-attr-md")
    assert val == Markdown("**Markdown**. Some **Markdown** stuff")
    assert errs == []


def test_plain_reference_from_md(markdown_escaping_bundle: FluentBundle):
    val, errs = markdown_escaping_bundle.format("references-plain-attr-md")
    assert val == Markdown("**Markdown**. This and That")
    assert errs == []


def test_md_variant_from_plain(markdown_escaping_bundle: FluentBundle):
    val, errs = markdown_escaping_bundle.format("references-md-variant-plain")
    assert val == "-brand-md is cool"
    assert len(errs) == 1
    assert type(errs[0]) is TypeError


def test_md_variant_from_md(markdown_escaping_bundle: FluentBundle):
    val, errs = markdown_escaping_bundle.format("references-md-variant-md")
    assert val == Markdown("CoolBrand **2** is cool")
    assert errs == []


def test_md_plain_variant_from_plain(markdown_escaping_bundle: FluentBundle):
    val, errs = markdown_escaping_bundle.format("references-plain-variant-plain")
    assert val == "*A&B* is awesome"
    assert errs == []


def test_plain_variant_from_md(markdown_escaping_bundle: FluentBundle):
    val, errs = markdown_escaping_bundle.format("references-plain-variant-md")
    assert val == Markdown("A&B is awesome")
    assert errs == []
