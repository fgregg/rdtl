"""
Tests for template syntax in HTML attributes.

Tests the new feature allowing templates in attributes with the opposite quote rule.
"""

from rdtl import ast_nodes
from rdtl.formatter import format_template
from rdtl.parser import parse
from rdtl.validator import validate_template

# Valid cases


def test_simple_if_in_double_quoted_attr():
    """Test if block in double-quoted attribute with single quotes."""
    template = (
        """<div class="{% if active == 'yes' %}active{% endif %}">Content</div>"""
    )
    is_valid, errors = validate_template(template)
    assert is_valid, f"Should be valid. Errors: {errors}"


def test_simple_if_in_single_quoted_attr():
    """Test if block in single-quoted attribute with double quotes."""
    template = (
        """<div class='{% if active == "yes" %}active{% endif %}'>Content</div>"""
    )
    is_valid, errors = validate_template(template)
    assert is_valid, f"Should be valid. Errors: {errors}"


def test_variable_in_double_quoted_attr():
    """Test variable in double-quoted attribute."""
    template = """<div title="{{ user.name }}">Content</div>"""
    is_valid, errors = validate_template(template)
    assert is_valid, f"Should be valid. Errors: {errors}"


def test_variable_in_single_quoted_attr():
    """Test variable in single-quoted attribute."""
    template = """<div title='{{ user.name }}'>Content</div>"""
    is_valid, errors = validate_template(template)
    assert is_valid, f"Should be valid. Errors: {errors}"


def test_mixed_text_and_template():
    """Test mixing text and template in attribute."""
    template = (
        """<div class="prefix {% if x %}special{% endif %} suffix">Content</div>"""
    )
    is_valid, errors = validate_template(template)
    assert is_valid, f"Should be valid. Errors: {errors}"


def test_multiple_templates_in_attr():
    """Test multiple template blocks in same attribute."""
    template = (
        """<div class="{% if x %}a{% endif %} {% if y %}b{% endif %}">Content</div>"""
    )
    is_valid, errors = validate_template(template)
    assert is_valid, f"Should be valid. Errors: {errors}"


def test_nested_if_elif_else():
    """Test if/elif/else in attribute."""
    template = """
    <div class="{% if score >= 90 %}A{% elif score >= 80 %}B{% else %}C{% endif %}">
        Grade
    </div>
    """
    is_valid, errors = validate_template(template)
    assert is_valid, f"Should be valid. Errors: {errors}"


def test_comparison_operators():
    """Test various comparison operators in attribute templates."""
    templates = [
        """<div class="{% if x == 'y' %}a{% endif %}">""",
        """<div class="{% if x != 'y' %}a{% endif %}">""",
        """<div class="{% if x > 5 %}a{% endif %}">""",
        """<div class="{% if x < 5 %}a{% endif %}">""",
        """<div class="{% if x >= 5 %}a{% endif %}">""",
        """<div class="{% if x <= 5 %}a{% endif %}">""",
    ]

    for template in templates:
        is_valid, errors = validate_template(template + "</div>")
        assert is_valid, f"Should be valid: {template}. Errors: {errors}"


def test_boolean_operators():
    """Test boolean operators in attribute templates."""
    template = """<div class="{% if x and y or z %}active{% endif %}">Content</div>"""
    is_valid, errors = validate_template(template)
    assert is_valid, f"Should be valid. Errors: {errors}"


def test_variable_with_filter():
    """Test variable with filter in attribute."""
    template = """<div title="{{ user.name|upper }}">Content</div>"""
    is_valid, errors = validate_template(template)
    assert is_valid, f"Should be valid. Errors: {errors}"


def test_img_src_with_conditional():
    """Test realistic use case: conditional image source."""
    template = """
    <img src="{% if user %}{{ user.avatar }}{% else %}'/default.jpg'{% endif %}" alt="Avatar">
    """
    is_valid, errors = validate_template(template)
    assert is_valid, f"Should be valid. Errors: {errors}"


def test_multiple_attributes_with_templates():
    """Test multiple attributes each with templates."""
    template = """
    <div class="{% if x %}active{% endif %}"
         title="{{ user.name }}"
         data-value="{% if y %}{{ y }}{% endif %}">
        Content
    </div>
    """
    is_valid, errors = validate_template(template)
    assert is_valid, f"Should be valid. Errors: {errors}"


# Same quote type (now valid with proper string tracking)


def test_same_quotes_double_now_valid():
    """Test that same quote type (double) is now supported inside string literals."""
    template = """<div class="{% if x == "y" %}active{% endif %}">Content</div>"""
    is_valid, errors = validate_template(template)
    assert is_valid, f"Should be valid. Errors: {errors}"


def test_same_quotes_single_now_valid():
    """Test that same quote type (single) is now supported inside string literals."""
    template = """<div class='{% if x == 'y' %}active{% endif %}'>Content</div>"""
    is_valid, errors = validate_template(template)
    assert is_valid, f"Should be valid. Errors: {errors}"


def test_same_quotes_in_variable_now_valid():
    """Test that same quotes are now supported in variables too."""
    template = """<div title="{{ user.name|default:"anonymous" }}">Content</div>"""
    is_valid, errors = validate_template(template)
    assert is_valid, f"Should be valid. Errors: {errors}"


def test_contractions_with_double_quotes():
    """Test the motivating case: contractions in double-quoted attributes."""
    template = """<div title="{% trans "that's all folks" %}">Content</div>"""
    is_valid, errors = validate_template(template)
    assert is_valid, f"Should be valid. Errors: {errors}"


def test_contractions_with_single_quotes():
    """Test contractions forcing double quotes inside single-quoted attribute."""
    template = """<div title='{% trans "that's all folks" %}'>Content</div>"""
    is_valid, errors = validate_template(template)
    assert is_valid, f"Should be valid. Errors: {errors}"


def test_escaped_quotes_in_string_literal():
    """Test that escape sequences work properly."""
    template = r"""<div title="{% trans "say \"hello\"" %}">Content</div>"""
    is_valid, errors = validate_template(template)
    assert is_valid, f"Should be valid. Errors: {errors}"


def test_mixed_quotes_in_expression():
    """Test multiple string literals with different quote types."""
    template = (
        """<div data-msg="{% if x == "a" or y == 'b' %}ok{% endif %}">Content</div>"""
    )
    is_valid, errors = validate_template(template)
    assert is_valid, f"Should be valid. Errors: {errors}"


# Parsing tests


def test_parse_template_in_attr():
    """Test that parser correctly handles template-in-attribute."""
    template = """<div class="{% if active %}active{% endif %}">Content</div>"""

    # Should parse without errors
    ast = parse(template)
    assert ast is not None


def test_parse_preserves_structure():
    """Test that parser preserves the structure correctly."""
    template = """<div class="prefix {{ var }} suffix">Content</div>"""

    ast = parse(template)
    # Verify we got an HTMLElement
    div = ast.children[0]

    assert isinstance(div, ast_nodes.HTMLElement)
    assert div.tag_name == "div"


# Formatter tests


def test_formatter_preserves_templates_in_attrs():
    """Test that formatter preserves templates in attributes."""
    template = """<div class="{% if x %}active{% endif %}">Content</div>"""
    formatted = format_template(template)

    # Should still contain the template
    assert "{% if x %}" in formatted
    assert "{% endif %}" in formatted


# Edge cases


def test_empty_template_in_attr():
    """Test empty template block in attribute."""
    template = """<div class="">Content</div>"""
    is_valid, errors = validate_template(template)
    assert is_valid, f"Should be valid. Errors: {errors}"


def test_only_template_in_attr():
    """Test attribute with only template, no other text."""
    template = """<div class="{% if x %}active{% endif %}">Content</div>"""
    is_valid, errors = validate_template(template)
    assert is_valid, f"Should be valid. Errors: {errors}"


def test_template_at_start_middle_end():
    """Test templates at different positions in attribute."""
    templates = [
        """<div class="{% if x %}a{% endif %} suffix">Content</div>""",  # start
        """<div class="prefix {% if x %}a{% endif %} suffix">Content</div>""",  # middle
        """<div class="prefix {% if x %}a{% endif %}">Content</div>""",  # end
    ]

    for template in templates:
        is_valid, errors = validate_template(template)
        assert is_valid, f"Should be valid: {template}. Errors: {errors}"


def test_number_comparison_no_quotes():
    """Test comparison with numbers (no quotes needed)."""
    template = """<div class="{% if count > 5 %}many{% endif %}">Content</div>"""
    is_valid, errors = validate_template(template)
    assert is_valid, f"Should be valid. Errors: {errors}"


def test_boolean_variable_no_quotes():
    """Test simple boolean variable (no quotes)."""
    template = """<div class="{% if is_active %}active{% endif %}">Content</div>"""
    is_valid, errors = validate_template(template)
    assert is_valid, f"Should be valid. Errors: {errors}"
