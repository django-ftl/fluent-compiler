import argparse
import random
from dataclasses import dataclass

from fluent.syntax import serialize
from fluent.syntax.ast import Comment, Identifier, Message, Pattern, Placeable, Resource, TextElement, VariableReference


@dataclass(frozen=True)
class ItemRatios:
    """
    Represent the ratios of different items inside the generated ftl file
    """

    message: int
    comment: int


@dataclass(frozen=True)
class ElementCountRatios:
    """
    Represent the ratios of the different count of elements within a pattern
    """

    one: int
    two: int
    three: int
    four: int


@dataclass(frozen=True)
class Config:
    filename: str
    num_items: int

    # Controls for the random generation of various elements
    item_ratios: ItemRatios = ItemRatios(message=40, comment=1)
    element_ratios: ElementCountRatios = ElementCountRatios(one=400, two=10, three=10, four=1)


def parse_config() -> Config:
    parser = argparse.ArgumentParser(description="Generate a sample ftl file")
    parser.add_argument(
        "filename",
        help="Filename for the generated file",
    )
    parser.add_argument(
        "-n",
        "--num-items",
        type=int,
        help="The number of items in the generated file",
        default=100,
    )
    return Config(**parser.parse_args().__dict__)


def generate_file(config: Config) -> None:
    with open("/usr/share/dict/words") as dictionary_file:
        all_words = [line.strip() for line in dictionary_file.readlines()]

    with open(config.filename, "w") as outfile:
        outfile.write(serialize(_generate_resource(config, all_words)))


def _generate_resource(config: Config, words: list[str]) -> Resource:
    body = []

    generators = (_generate_message, _generate_comment)
    weights = (config.item_ratios.message, config.item_ratios.comment)

    for _ in range(config.num_items):
        (generator,) = random.choices(generators, weights)
        body.append(generator(config, words))

    return Resource(body=body)


def _generate_message(config: Config, words: list[str]) -> Message:
    id = _generate_identifier(words, joiner="-", elements=4)
    return Message(
        id=id,
        value=_generate_pattern(config, words),
    )


def _generate_comment(config: Config, words: list[str]) -> Comment:
    """
    Generate a random comment, of the form:

    # some words
    """
    return Comment(content=" ".join(random.choices(words, k=random.randint(1, 10))))


def _generate_identifier(words: list[str], joiner: str, elements: int) -> Identifier:
    """
    Generate a random identifier, of the form:

    correct-horse-battery-staple
    """
    return Identifier(name=joiner.join(random.choices(words, k=elements)))


def _generate_pattern(config: Config, words: list[str]) -> Pattern:
    """
    Generate a pattern, which is a sequence of elements of the form:

    some text { identifier } some more text { other_identifier }
    """
    (num_elements,) = random.choices(
        (1, 2, 3, 4),
        weights=(
            config.element_ratios.one,
            config.element_ratios.two,
            config.element_ratios.three,
            config.element_ratios.four,
        ),
    )
    elements = []
    for i in range(num_elements):
        if i % 2:
            elements.append(_generate_placeable(words))
        else:
            elements.append(_generate_text_element(words))

    return Pattern(elements=elements)


def _generate_text_element(words: list[str]) -> TextElement:
    """
    Generate a random text element, of the form:

    some words
    """
    return TextElement(value=" ".join(random.choices(words, k=random.randint(1, 10))))


def _generate_placeable(words: list[str]) -> Placeable:
    return Placeable(expression=_generate_variable_reference(words))


def _generate_variable_reference(words: list[str]) -> VariableReference:
    """
    Generate a variable reference, of the form:

    { some_variable }
    """
    return VariableReference(id=_generate_identifier(words, joiner="_", elements=2))


def main():
    config = parse_config()
    generate_file(config)


if __name__ == "__main__":
    main()
