"""
Test suite for the parser.
"""

import unittest
from rdtl.parser import parse
from rdtl.ast_nodes import *


class TestParser(unittest.TestCase):
    """Test cases for the parser."""

    def test_simple_html(self):
        """Test parsing simple HTML."""
        template = "<div>Hello World</div>"
        ast = parse(template)

        self.assertIsInstance(ast, Document)
        self.assertEqual(len(ast.children), 1)

        div = ast.children[0]
        self.assertIsInstance(div, HTMLElement)
        self.assertEqual(div.tag_name, 'div')
        self.assertEqual(len(div.children), 1)

        text = div.children[0]
        self.assertIsInstance(text, TextNode)
        self.assertEqual(text.content, 'Hello World')

    def test_html_with_attributes(self):
        """Test parsing HTML with attributes."""
        template = '<div class="container" id="main">Content</div>'
        ast = parse(template)

        div = ast.children[0]
        self.assertEqual(len(div.attributes), 2)
        self.assertEqual(div.attributes[0].name, 'class')
        self.assertEqual(div.attributes[0].value, 'container')
        self.assertEqual(div.attributes[1].name, 'id')
        self.assertEqual(div.attributes[1].value, 'main')

    def test_nested_html(self):
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
            if isinstance(child, HTMLElement):
                div = child
                break

        self.assertIsNotNone(div)
        self.assertEqual(div.tag_name, 'div')

        # Find the p tag
        p = None
        for child in div.children:
            if isinstance(child, HTMLElement):
                p = child
                break

        self.assertIsNotNone(p)
        self.assertEqual(p.tag_name, 'p')

        # Find the span tag
        span = None
        for child in p.children:
            if isinstance(child, HTMLElement):
                span = child
                break

        self.assertIsNotNone(span)
        self.assertEqual(span.tag_name, 'span')

    def test_void_elements(self):
        """Test void HTML elements."""
        template = '<img src="test.jpg" alt="Test">'
        ast = parse(template)

        img = ast.children[0]
        self.assertIsInstance(img, VoidElement)
        self.assertEqual(img.tag_name, 'img')
        self.assertEqual(len(img.attributes), 2)

    def test_simple_variable(self):
        """Test parsing template variables."""
        template = "<p>{{ user }}</p>"
        ast = parse(template)

        p = ast.children[0]
        var = p.children[0]

        self.assertIsInstance(var, Variable)
        self.assertEqual(var.expression.base, 'user')
        self.assertEqual(len(var.filters), 0)

    def test_variable_with_lookup(self):
        """Test variable with attribute lookup."""
        template = "{{ user.name }}"
        ast = parse(template)

        var = ast.children[0]
        self.assertIsInstance(var, Variable)
        self.assertEqual(var.expression.base, 'user')
        self.assertEqual(len(var.expression.lookups), 1)
        self.assertEqual(var.expression.lookups[0].type, 'attribute')
        self.assertEqual(var.expression.lookups[0].value, 'name')

    def test_variable_with_filter(self):
        """Test variable with filter."""
        template = "{{ user.name|upper }}"
        ast = parse(template)

        var = ast.children[0]
        self.assertEqual(len(var.filters), 1)
        self.assertEqual(var.filters[0].name, 'upper')
        self.assertEqual(len(var.filters[0].args), 0)

    def test_variable_with_filter_args(self):
        """Test variable with filter arguments."""
        template = '{{ date|date:"Y-m-d" }}'
        ast = parse(template)

        var = ast.children[0]
        self.assertEqual(var.filters[0].name, 'date')
        self.assertEqual(len(var.filters[0].args), 1)
        self.assertEqual(var.filters[0].args[0], 'Y-m-d')

    def test_if_block(self):
        """Test if block."""
        template = """
        {% if user %}
            <p>Hello</p>
        {% endif %}
        """
        ast = parse(template)

        if_block = None
        for child in ast.children:
            if isinstance(child, IfBlock):
                if_block = child
                break

        self.assertIsNotNone(if_block)
        self.assertIsInstance(if_block.if_condition, SimpleCondition)
        self.assertEqual(if_block.if_condition.expression.base, 'user')
        self.assertIsNone(if_block.else_children)

        # Check if body
        p = None
        for child in if_block.if_children:
            if isinstance(child, HTMLElement):
                p = child
                break

        self.assertIsNotNone(p)
        self.assertEqual(p.tag_name, 'p')

    def test_if_else_block(self):
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
            if isinstance(child, IfBlock):
                if_block = child
                break

        self.assertIsNotNone(if_block)
        self.assertIsNotNone(if_block.else_children)

    def test_if_elif_else_block(self):
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
            if isinstance(child, IfBlock):
                if_block = child
                break

        self.assertIsNotNone(if_block)
        self.assertEqual(len(if_block.elif_branches), 1)
        self.assertIsNotNone(if_block.else_children)

        # Check elif condition
        elif_cond, elif_children = if_block.elif_branches[0]
        self.assertIsInstance(elif_cond, Comparison)

    def test_for_loop(self):
        """Test for loop."""
        template = """
        {% for item in items %}
            <li>{{ item }}</li>
        {% endfor %}
        """
        ast = parse(template)

        for_block = None
        for child in ast.children:
            if isinstance(child, ForBlock):
                for_block = child
                break

        self.assertIsNotNone(for_block)
        self.assertEqual(for_block.loop_var, 'item')
        self.assertEqual(for_block.iterable.base, 'items')
        self.assertIsNone(for_block.empty_children)

    def test_for_loop_with_empty(self):
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
            if isinstance(child, ForBlock):
                for_block = child
                break

        self.assertIsNotNone(for_block)
        self.assertIsNotNone(for_block.empty_children)

    def test_block_tag(self):
        """Test block definition."""
        template = """
        {% block content %}
            <p>Default content</p>
        {% endblock %}
        """
        ast = parse(template)

        block = None
        for child in ast.children:
            if isinstance(child, BlockTag):
                block = child
                break

        self.assertIsNotNone(block)
        self.assertEqual(block.name, 'content')

    def test_with_block(self):
        """Test with block."""
        template = """
        {% with total=items.count %}
            <p>Total: {{ total }}</p>
        {% endwith %}
        """
        ast = parse(template)

        with_block = None
        for child in ast.children:
            if isinstance(child, WithBlock):
                with_block = child
                break

        self.assertIsNotNone(with_block)
        self.assertEqual(len(with_block.assignments), 1)
        self.assertEqual(with_block.assignments[0][0], 'total')

    def test_include_tag(self):
        """Test include tag."""
        template = '{% include "header.html" %}'
        ast = parse(template)

        include = ast.children[0]
        self.assertIsInstance(include, IncludeTag)
        self.assertEqual(include.template_name, 'header.html')

    def test_extends_tag(self):
        """Test extends tag."""
        template = '{% extends "base.html" %}'
        ast = parse(template)

        extends = ast.children[0]
        self.assertIsInstance(extends, ExtendsTag)
        self.assertEqual(extends.parent_template, 'base.html')

    def test_load_tag(self):
        """Test load tag."""
        template = '{% load static %}'
        ast = parse(template)

        load = ast.children[0]
        self.assertIsInstance(load, LoadTag)
        self.assertEqual(load.library, 'static')

    def test_csrf_token_tag(self):
        """Test csrf_token tag."""
        template = '{% csrf_token %}'
        ast = parse(template)

        csrf = ast.children[0]
        self.assertIsInstance(csrf, CsrfTokenTag)

    def test_comment(self):
        """Test template comments."""
        template = '{# This is a comment #}'
        ast = parse(template)

        comment = ast.children[0]
        self.assertIsInstance(comment, Comment)
        self.assertEqual(comment.content, ' This is a comment ')

    def test_complex_nested_structure(self):
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
        self.assertIsInstance(ast, Document)
        self.assertTrue(len(ast.children) > 0)

    def test_comparison_operators(self):
        """Test all comparison operators."""
        templates = [
            ("{% if x == y %}A{% endif %}", '=='),
            ("{% if x != y %}A{% endif %}", '!='),
            ("{% if x < y %}A{% endif %}", '<'),
            ("{% if x > y %}A{% endif %}", '>'),
            ("{% if x <= y %}A{% endif %}", '<='),
            ("{% if x >= y %}A{% endif %}", '>='),
        ]

        for template, op in templates:
            ast = parse(template)
            if_block = ast.children[0]
            self.assertIsInstance(if_block.if_condition, Comparison)
            self.assertEqual(if_block.if_condition.operator, op)

    def test_boolean_operators(self):
        """Test and/or operators."""
        template = "{% if x and y or z %}A{% endif %}"
        ast = parse(template)

        if_block = ast.children[0]
        # Should parse to: (x and y) or z
        self.assertIsInstance(if_block.if_condition, BooleanOp)

    def test_not_operator(self):
        """Test not operator."""
        template = "{% if not user %}A{% endif %}"
        ast = parse(template)

        if_block = ast.children[0]
        self.assertIsInstance(if_block.if_condition, SimpleCondition)
        self.assertTrue(if_block.if_condition.negated)

    def test_multiple_filters(self):
        """Test chaining multiple filters."""
        template = "{{ text|lower|truncatewords:10 }}"
        ast = parse(template)

        var = ast.children[0]
        self.assertEqual(len(var.filters), 2)
        self.assertEqual(var.filters[0].name, 'lower')
        self.assertEqual(var.filters[1].name, 'truncatewords')

    def test_bracket_notation_not_supported(self):
        """Test that bracket notation is rejected (Django doesn't support it)."""
        # Django only supports dot notation, not bracket notation
        # Use items.0 instead of items[0]
        template = "{{ items[0] }}"
        with self.assertRaises(Exception):
            # Should fail - brackets not supported
            parse(template)

    def test_numeric_index_via_dot(self):
        """Test numeric index access using dot notation (Django style)."""
        # Django uses dot notation for numeric indices
        template = '{{ items.0 }}'
        ast = parse(template)

        var = ast.children[0]
        self.assertEqual(len(var.expression.lookups), 1)
        self.assertEqual(var.expression.lookups[0].type, 'attribute')
        self.assertEqual(var.expression.lookups[0].value, '0')


if __name__ == '__main__':
    unittest.main()
