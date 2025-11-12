"""
Test suite for the parser.
"""

import pytest

from rdtl import ast_nodes
from rdtl.parser import ParseError, parse


def test_simple_html():
    """Test parsing simple HTML."""
    template = "<div>Hello World</div>"
    ast = parse(template)

    assert isinstance(ast, ast_nodes.Document)
    assert len(ast.children) == 1

    div = ast.children[0]
    assert isinstance(div, ast_nodes.HTMLElement)
    assert div.tag_name == "div"
    assert len(div.children) == 1

    text = div.children[0]
    assert isinstance(text, ast_nodes.TextNode)
    assert text.content == "Hello World"


def test_html_with_attributes():
    """Test parsing HTML with attributes."""
    template = '<div class="container" id="main">Content</div>'
    ast = parse(template)

    div = ast.children[0]
    assert len(div.attributes) == 2
    assert div.attributes[0].name == "class"
    assert div.attributes[0].value == "container"
    assert div.attributes[1].name == "id"
    assert div.attributes[1].value == "main"


def test_nested_html():
    """Test nested HTML elements."""
    template = """
    <div>
        <p>
            <span>Nested</span>
        </p>
    </div>
    """
    ast = parse(template)

    # Navigate the tree
    div = None
    for child in ast.children:
        if isinstance(child, ast_nodes.HTMLElement):
            div = child
            break

    assert div is not None
    assert div.tag_name == "div"

    # Find the p tag
    p = None
    for child in div.children:
        if isinstance(child, ast_nodes.HTMLElement):
            p = child
            break

    assert p is not None
    assert p.tag_name == "p"

    # Find the span tag
    span = None
    for child in p.children:
        if isinstance(child, ast_nodes.HTMLElement):
            span = child
            break

    assert span is not None
    assert span.tag_name == "span"


def test_void_elements():
    """Test void HTML elements."""
    template = '<img src="test.jpg" alt="Test">'
    ast = parse(template)

    img = ast.children[0]
    assert isinstance(img, ast_nodes.VoidElement)
    assert img.tag_name == "img"
    assert len(img.attributes) == 2


def test_simple_variable():
    """Test parsing template variables."""
    template = "<p>{{ user }}</p>"
    ast = parse(template)

    p = ast.children[0]
    var = p.children[0]

    assert isinstance(var, ast_nodes.Variable)
    assert var.expression.base == "user"
    assert len(var.filters) == 0


def test_variable_with_lookup():
    """Test variable with attribute lookup."""
    template = "{{ user.name }}"
    ast = parse(template)

    var = ast.children[0]
    assert isinstance(var, ast_nodes.Variable)
    assert var.expression.base == "user"
    assert len(var.expression.lookups) == 1
    assert var.expression.lookups[0].type == "attribute"
    assert var.expression.lookups[0].value == "name"


def test_variable_with_filter():
    """Test variable with filter."""
    template = "{{ user.name|upper }}"
    ast = parse(template)

    var = ast.children[0]
    assert len(var.filters) == 1
    assert var.filters[0].name == "upper"
    assert len(var.filters[0].args) == 0


def test_variable_with_filter_args():
    """Test variable with filter arguments."""
    template = '{{ date|date:"Y-m-d" }}'
    ast = parse(template)

    var = ast.children[0]
    assert var.filters[0].name == "date"
    assert len(var.filters[0].args) == 1
    assert var.filters[0].args[0] == "Y-m-d"


def test_if_block():
    """Test if block."""
    template = """
    {% if user %}
        <p>Hello</p>
    {% endif %}
    """
    ast = parse(template)

    if_block = None
    for child in ast.children:
        if isinstance(child, ast_nodes.IfBlock):
            if_block = child
            break

    assert if_block is not None
    assert isinstance(if_block.if_condition, ast_nodes.SimpleCondition)
    assert if_block.if_condition.expression.base == "user"
    assert if_block.else_children is None

    # Check if body
    p = None
    for child in if_block.if_children:
        if isinstance(child, ast_nodes.HTMLElement):
            p = child
            break

    assert p is not None
    assert p.tag_name == "p"


def test_if_else_block():
    """Test if/else block."""
    template = """
    {% if user %}
        <p>Logged in</p>
    {% else %}
        <p>Logged out</p>
    {% endif %}
    """
    ast = parse(template)

    if_block = None
    for child in ast.children:
        if isinstance(child, ast_nodes.IfBlock):
            if_block = child
            break

    assert if_block is not None
    assert if_block.else_children is not None


def test_if_elif_else_block():
    """Test if/elif/else block."""
    template = """
    {% if score >= 90 %}
        <p>A</p>
    {% elif score >= 80 %}
        <p>B</p>
    {% else %}
        <p>C</p>
    {% endif %}
    """
    ast = parse(template)

    if_block = None
    for child in ast.children:
        if isinstance(child, ast_nodes.IfBlock):
            if_block = child
            break

    assert if_block is not None
    assert len(if_block.elif_branches) == 1
    assert if_block.else_children is not None

    # Check elif condition
    elif_cond, elif_children = if_block.elif_branches[0]
    assert isinstance(elif_cond, ast_nodes.Comparison)


def test_for_loop():
    """Test for loop."""
    template = """
    {% for item in items %}
        <li>{{ item }}</li>
    {% endfor %}
    """
    ast = parse(template)

    for_block = None
    for child in ast.children:
        if isinstance(child, ast_nodes.ForBlock):
            for_block = child
            break

    assert for_block is not None
    assert for_block.loop_vars == ["item"]
    assert for_block.iterable.base == "items"
    assert for_block.empty_children is None


def test_for_loop_with_empty():
    """Test for loop with empty clause."""
    template = """
    {% for item in items %}
        <li>{{ item }}</li>
    {% empty %}
        <li>No items</li>
    {% endfor %}
    """
    ast = parse(template)

    for_block = None
    for child in ast.children:
        if isinstance(child, ast_nodes.ForBlock):
            for_block = child
            break

    assert for_block is not None
    assert for_block.empty_children is not None


def test_block_tag():
    """Test block definition."""
    template = """
    {% block content %}
        <p>Default content</p>
    {% endblock %}
    """
    ast = parse(template)

    block = None
    for child in ast.children:
        if isinstance(child, ast_nodes.BlockTag):
            block = child
            break

    assert block is not None
    assert block.name == "content"


def test_with_block():
    """Test with block."""
    template = """
    {% with total=items.count %}
        <p>Total: {{ total }}</p>
    {% endwith %}
    """
    ast = parse(template)

    with_block = None
    for child in ast.children:
        if isinstance(child, ast_nodes.WithBlock):
            with_block = child
            break

    assert with_block is not None
    assert len(with_block.assignments) == 1
    assert with_block.assignments[0][0] == "total"


def test_include_tag():
    """Test include tag."""
    template = '{% include "header.html" %}'
    ast = parse(template)

    include = ast.children[0]
    assert isinstance(include, ast_nodes.IncludeTag)
    assert include.template_name == "header.html"


def test_extends_tag():
    """Test extends tag."""
    template = '{% extends "base.html" %}'
    ast = parse(template)

    extends = ast.children[0]
    assert isinstance(extends, ast_nodes.ExtendsTag)
    assert extends.parent_template == "base.html"


def test_load_tag():
    """Test load tag."""
    template = "{% load static %}"
    ast = parse(template)

    load = ast.children[0]
    assert isinstance(load, ast_nodes.LoadTag)
    assert load.libraries == ["static"]


def test_csrf_token_tag():
    """Test csrf_token tag."""
    template = "{% csrf_token %}"
    ast = parse(template)

    csrf = ast.children[0]
    assert isinstance(csrf, ast_nodes.CsrfTokenTag)


def test_comment():
    """Test template comments."""
    template = "{# This is a comment #}"
    ast = parse(template)

    comment = ast.children[0]
    assert isinstance(comment, ast_nodes.Comment)
    assert comment.content == "This is a comment"  # Lexer strips whitespace


def test_complex_nested_structure():
    """Test complex nested template."""
    template = """
    <html>
    <body>
        {% block content %}
            <main>
                {% if user %}
                    <h1>Welcome {{ user.name }}</h1>
                    {% for item in user.items %}
                        <div>
                            <h3>{{ item.title }}</h3>
                            {% if item.description %}
                                <p>{{ item.description|truncatewords:20 }}</p>
                            {% endif %}
                        </div>
                    {% endfor %}
                {% else %}
                    <p>Please log in</p>
                {% endif %}
            </main>
        {% endblock %}
    </body>
    </html>
    """
    ast = parse(template)

    # Should parse without errors
    assert isinstance(ast, ast_nodes.Document)
    assert len(ast.children) > 0


@pytest.mark.parametrize(
    ("template", "operator"),
    [
        ("{% if x == y %}A{% endif %}", "=="),
        ("{% if x != y %}A{% endif %}", "!="),
        ("{% if x < y %}A{% endif %}", "<"),
        ("{% if x > y %}A{% endif %}", ">"),
        ("{% if x <= y %}A{% endif %}", "<="),
        ("{% if x >= y %}A{% endif %}", ">="),
    ],
)
def test_comparison_operators(template, operator):
    """Test all comparison operators."""
    ast = parse(template)
    if_block = ast.children[0]
    assert isinstance(if_block.if_condition, ast_nodes.Comparison)
    assert if_block.if_condition.operator == operator


def test_boolean_operators():
    """Test and/or operators."""
    template = "{% if x and y or z %}A{% endif %}"
    ast = parse(template)

    if_block = ast.children[0]
    # Should parse to: (x and y) or z
    assert isinstance(if_block.if_condition, ast_nodes.BooleanOp)


def test_not_operator():
    """Test not operator."""
    template = "{% if not user %}A{% endif %}"
    ast = parse(template)

    if_block = ast.children[0]
    assert isinstance(if_block.if_condition, ast_nodes.SimpleCondition)
    assert if_block.if_condition.negated is True


def test_multiple_filters():
    """Test chaining multiple filters."""
    template = "{{ text|lower|truncatewords:10 }}"
    ast = parse(template)

    var = ast.children[0]
    assert len(var.filters) == 2
    assert var.filters[0].name == "lower"
    assert var.filters[1].name == "truncatewords"


def test_bracket_notation_not_supported():
    """Test that bracket notation is rejected (Django doesn't support it)."""
    # Django only supports dot notation, not bracket notation
    # Use items.0 instead of items[0]
    template = "{{ items[0] }}"
    with pytest.raises((SyntaxError, ValueError, ParseError)):
        # Should fail - brackets not supported
        parse(template)


def test_numeric_index_via_dot():
    """Test numeric index access using dot notation (Django style)."""
    # Django uses dot notation for numeric indices
    template = "{{ items.0 }}"
    ast = parse(template)

    var = ast.children[0]
    assert len(var.expression.lookups) == 1
    assert var.expression.lookups[0].type == "attribute"
    assert var.expression.lookups[0].value == "0"
