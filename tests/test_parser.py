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


def test_is_operator():
    """Test 'is' operator."""
    template = "{% if x is None %}yes{% endif %}"
    ast = parse(template)
    assert isinstance(ast, ast_nodes.Document)
    assert len(ast.children) == 1
    if_block = ast.children[0]
    assert isinstance(if_block, ast_nodes.IfBlock)
    assert isinstance(if_block.if_condition, ast_nodes.Comparison)
    assert if_block.if_condition.operator == "is"


def test_is_not_operator():
    """Test 'is not' operator."""
    template = "{% if x is not None %}yes{% endif %}"
    ast = parse(template)
    assert isinstance(ast, ast_nodes.Document)
    assert len(ast.children) == 1
    if_block = ast.children[0]
    assert isinstance(if_block, ast_nodes.IfBlock)
    assert isinstance(if_block.if_condition, ast_nodes.Comparison)
    assert if_block.if_condition.operator == "is not"


def test_with_block_with_filter():
    """Test with block with filter in assignment."""
    template = """
    {% with value=data|get_item:key %}
        {{ value }}
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
    assert with_block.assignments[0][0] == "value"

    # The value should be a FilteredExpression
    expr = with_block.assignments[0][1]
    assert isinstance(expr, ast_nodes.FilteredExpression)
    assert expr.expression.base == "data"
    assert len(expr.filters) == 1
    assert expr.filters[0].name == "get_item"


def test_with_block_with_filter_and_dot_arg():
    """Test with block with filter that has a dot-notation argument."""
    template = """
    {% with value=event.program_data|get_item:property.name %}
        {{ value }}
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
    assert with_block.assignments[0][0] == "value"

    # The value should be a FilteredExpression
    expr = with_block.assignments[0][1]
    assert isinstance(expr, ast_nodes.FilteredExpression)
    assert expr.expression.base == "event"
    assert len(expr.expression.lookups) == 1
    assert expr.expression.lookups[0].value == "program_data"

    # Check the filter
    assert len(expr.filters) == 1
    assert expr.filters[0].name == "get_item"

    # Check the filter argument is an Expression with dot lookup
    assert len(expr.filters[0].args) == 1
    filter_arg = expr.filters[0].args[0]
    assert isinstance(filter_arg, ast_nodes.Expression)
    assert filter_arg.base == "property"
    assert len(filter_arg.lookups) == 1
    assert filter_arg.lookups[0].value == "name"


def test_with_block_multiple_assignments_with_filters():
    """Test with block with multiple assignments including filters."""
    template = """
    {% with total=items|length upper_name=user.name|upper %}
        {{ total }} {{ upper_name }}
    {% endwith %}
    """
    ast = parse(template)

    with_block = None
    for child in ast.children:
        if isinstance(child, ast_nodes.WithBlock):
            with_block = child
            break

    assert with_block is not None
    assert len(with_block.assignments) == 2

    # First assignment: total=items|length
    assert with_block.assignments[0][0] == "total"
    expr1 = with_block.assignments[0][1]
    assert isinstance(expr1, ast_nodes.FilteredExpression)
    assert expr1.expression.base == "items"
    assert expr1.filters[0].name == "length"

    # Second assignment: upper_name=user.name|upper
    assert with_block.assignments[1][0] == "upper_name"
    expr2 = with_block.assignments[1][1]
    assert isinstance(expr2, ast_nodes.FilteredExpression)
    assert expr2.expression.base == "user"
    assert expr2.filters[0].name == "upper"


def test_script_with_angle_brackets():
    """Test that < and > inside script tags are parsed as text, not HTML."""
    template = "<script>if (a < b && c > d) { x = 1; }</script>"
    ast = parse(template)
    assert len(ast.children) == 1
    script = ast.children[0]
    assert isinstance(script, ast_nodes.HTMLElement)
    assert script.tag_name == "script"
    # The JS content should be a single text node, not parsed as HTML
    assert len(script.children) == 1
    assert isinstance(script.children[0], ast_nodes.TextNode)
    assert "<" in script.children[0].content
    assert ">" in script.children[0].content


# Regression tests for issue #1: reserved lexemes (e.g. `url`) used as plain
# names. The lexer emits a dedicated token (URL, STATIC, AS, ...) for these
# words, so the parser must treat them as soft keywords wherever Django allows
# an arbitrary identifier (with target, for loop var, `as` alias, block name).
# https://github.com/fgregg/rdtl/issues/1


def test_with_target_named_url():
    """`url` is a legal variable name as a {% with %} assignment target."""
    template = "{% with url='x' %}{{ url }}{% endwith %}"
    ast = parse(template)

    with_block = next(c for c in ast.children if isinstance(c, ast_nodes.WithBlock))
    assert with_block.assignments[0][0] == "url"


def test_with_multiple_targets_reserved_names():
    """Several reserved lexemes as with targets in one tag."""
    template = "{% with url='a' static='b' %}{{ url }}{{ static }}{% endwith %}"
    ast = parse(template)

    with_block = next(c for c in ast.children if isinstance(c, ast_nodes.WithBlock))
    assert [name for name, _ in with_block.assignments] == ["url", "static"]


def test_for_loop_var_named_url():
    """`url` is a legal loop variable name."""
    template = "{% for url in items %}{{ url }}{% endfor %}"
    ast = parse(template)

    for_block = next(c for c in ast.children if isinstance(c, ast_nodes.ForBlock))
    assert for_block.loop_vars == ["url"]


def test_for_loop_tuple_unpack_reserved_names():
    """Reserved lexemes work in tuple unpacking targets."""
    template = "{% for url, static in items %}{{ url }}{% endfor %}"
    ast = parse(template)

    for_block = next(c for c in ast.children if isinstance(c, ast_nodes.ForBlock))
    assert for_block.loop_vars == ["url", "static"]


def test_url_tag_as_alias_named_url():
    """`as url` alias target accepts a reserved lexeme."""
    template = "{% url 'search' as url %}{{ url }}"
    ast = parse(template)

    url_tag = next(c for c in ast.children if isinstance(c, ast_nodes.UrlTag))
    assert url_tag.as_var == "url"


def test_block_name_reserved_lexeme():
    """A {% block %} may be named with a reserved lexeme, including the close tag."""
    template = "{% block url %}hi{% endblock url %}"
    ast = parse(template)

    block = next(c for c in ast.children if isinstance(c, ast_nodes.BlockTag))
    assert block.name == "url"


def test_include_with_context_var_named_url():
    """`{% include ... with url=... %}` context-var name accepts a reserved lexeme."""
    template = "{% include 'p.html' with url=foo %}"
    ast = parse(template)

    include = next(c for c in ast.children if isinstance(c, ast_nodes.IncludeTag))
    assert "url" in include.context_vars
