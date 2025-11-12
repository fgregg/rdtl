"""
Property-based tests for nested quote handling.

These tests cover the stateful lexer feature that allows same-quote
nesting in attributes: title="{% trans "that's all folks" %}"

This feature broke Lark generation (regex-based lexing can't handle it),
so we use custom Hypothesis strategies instead of Lark-based generation.

The hybrid approach:
- Lark generates ~90% of test cases (basic templates)
- Custom strategies generate ~10% (nested quotes edge cases)
- Combined: 100% coverage
"""

import pytest
from hypothesis import example, given, settings
from hypothesis import strategies as st

from rdtl.formatter import format_template
from rdtl.parser import parse
from rdtl.validator import validate_template

# ============================================================================
# Hypothesis Strategies for Nested Quotes
# ============================================================================

# Basic building blocks
html_tags = st.sampled_from(["div", "p", "span", "button", "a", "section"])
identifiers = st.from_regex(r"[a-z][a-z0-9_]{0,10}", fullmatch=True)
simple_text = st.text(
    alphabet=st.characters(
        whitelist_categories=("Lu", "Ll", "Nd", "Zs"), max_codepoint=127
    ),
    min_size=1,
    max_size=20,
)


@st.composite
def quoted_string_in_template(draw):
    """Generate a quoted string that can appear inside template tags.

    This generates strings with both quote types, which can now appear
    in attributes using the same quote type (thanks to stateful lexer).
    """
    quote = draw(st.sampled_from(['"', "'"]))
    # Generate text without the quote character (to avoid escaping complexity)
    text = draw(
        st.text(
            alphabet=st.characters(
                whitelist_categories=("Lu", "Ll", "Nd", "Zs"),
                blacklist_characters=quote,
                max_codepoint=127,
            ),
            min_size=1,
            max_size=15,
        )
    )
    return f"{quote}{text}{quote}"


@st.composite
def template_in_attribute_with_nested_quotes(draw):
    """Generate attribute with template that uses SAME quote type as attribute.

    This is the key feature enabled by the stateful lexer:
    - title="{% trans "hello" %}"  (double in double)
    - title='{% trans 'hello' %}'  (single in single)
    """
    # Choose attribute quote type
    attr_quote = draw(st.sampled_from(['"', "'"]))
    attr_name = draw(st.sampled_from(["class", "title", "data-msg", "aria-label"]))

    # Generate template tag that uses the SAME quote
    tag_type = draw(st.sampled_from(["trans", "if"]))

    if tag_type == "trans":
        # {% trans "text" %} or {% trans 'text' %}
        text = draw(simple_text)
        template = f"{{% trans {attr_quote}{text}{attr_quote} %}}"
    else:  # if
        # {% if var == "value" %}...{% endif %}
        var = draw(identifiers)
        value = draw(simple_text)
        template = (
            f"{{% if {var} == {attr_quote}{value}{attr_quote} %}}active{{% endif %}}"
        )

    return f"{attr_name}={attr_quote}{template}{attr_quote}"


@st.composite
def html_element_with_nested_quotes(draw):
    """Generate complete HTML element with nested-quote attributes."""
    tag = draw(html_tags)
    attr = draw(template_in_attribute_with_nested_quotes())
    content = draw(simple_text)
    return f"<{tag} {attr}>{content}</{tag}>"


# ============================================================================
# Property Tests
# ============================================================================


@given(html_element_with_nested_quotes())
@example('<div title="{% trans "hello" %}">content</div>')
@example("<div class='{% if x == 'y' %}active{% endif %}'>content</div>")
@settings(max_examples=100)
def test_nested_quotes_parse(template):
    """Test that nested-quote templates parse successfully."""
    try:
        ast = parse(template)
        assert ast is not None, "Parser should return an AST"
    except Exception as e:
        pytest.fail(f"Failed to parse nested-quote template: {template}\nError: {e}")


@given(html_element_with_nested_quotes())
@example('<div title="{% trans "hello" %}">content</div>')
@settings(max_examples=50)
def test_nested_quotes_roundtrip(template):
    """Test round-trip consistency for nested quotes."""
    try:
        # Parse original
        parse(template)

        # Format and re-parse
        formatted = format_template(template)
        parse(formatted)

        # The formatter may add trailing newlines, so format both to normalize
        formatted_again = format_template(formatted)

        # After normalization, they should be identical
        assert formatted == formatted_again, (
            f"Round-trip failed (not idempotent):\n"
            f"Original: {template}\n"
            f"Formatted once: {formatted}\n"
            f"Formatted twice: {formatted_again}"
        )
    except Exception as e:
        pytest.fail(f"Round-trip failed for: {template}\nError: {e}")


@given(template_in_attribute_with_nested_quotes())
@example('title="{% trans "hello" %}"')
@example("class='{% if x == 'y' %}active{% endif %}'")
@settings(max_examples=50)
def test_nested_quotes_validate(attr_with_template):
    """Test that validator accepts nested quotes."""
    template = f"<div {attr_with_template}>content</div>"
    try:
        is_valid, errors = validate_template(template)
        assert is_valid, (
            f"Validator should accept nested-quote template:\n"
            f"Template: {template}\n"
            f"Errors: {errors}"
        )
    except Exception as e:
        pytest.fail(f"Validation failed for: {template}\nError: {e}")


@given(html_element_with_nested_quotes())
@settings(max_examples=30)
def test_nested_quotes_format_idempotent(template):
    """Test that formatting nested-quote templates is idempotent."""
    try:
        formatted_once = format_template(template)
        formatted_twice = format_template(formatted_once)

        assert formatted_once == formatted_twice, (
            f"Formatting should be idempotent:\n"
            f"Original: {template}\n"
            f"Formatted once: {formatted_once}\n"
            f"Formatted twice: {formatted_twice}"
        )
    except Exception as e:
        pytest.fail(f"Formatter idempotence failed for: {template}\nError: {e}")
