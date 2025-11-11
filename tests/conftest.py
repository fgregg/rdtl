"""
Pytest configuration and shared fixtures for RDTL tests.
"""

import pytest
from pathlib import Path
from rdtl.parser import parse
from rdtl.lexer import tokenize
from rdtl.validator import validate_template
from rdtl.formatter import format_template, FormatOptions


@pytest.fixture
def simple_html():
    """Simple HTML template for testing."""
    return "<div>Hello World</div>"


@pytest.fixture
def nested_html():
    """Nested HTML template for testing."""
    return """
<div>
    <p>Paragraph</p>
    <ul>
        <li>Item 1</li>
        <li>Item 2</li>
    </ul>
</div>
""".strip()


@pytest.fixture
def template_with_variable():
    """Template with a variable."""
    return "<div>{{ message }}</div>"


@pytest.fixture
def template_with_if():
    """Template with if block."""
    return """
{% if condition %}
    <p>True</p>
{% else %}
    <p>False</p>
{% endif %}
""".strip()


@pytest.fixture
def template_with_for():
    """Template with for loop."""
    return """
{% for item in items %}
    <li>{{ item }}</li>
{% endfor %}
""".strip()


@pytest.fixture
def default_format_options():
    """Default formatting options."""
    return FormatOptions()


@pytest.fixture
def examples_dir():
    """Path to examples directory."""
    return Path(__file__).parent.parent / "examples"


@pytest.fixture
def grammar_file():
    """Path to grammar EBNF file."""
    return Path(__file__).parent.parent / "src" / "rdtl" / "grammar.ebnf"


@pytest.fixture
def lark_grammar_file():
    """Path to Lark grammar file."""
    return Path(__file__).parent.parent / "src" / "rdtl" / "rdtl_lark.lark"


# Helper functions available to all tests
def assert_parses_successfully(template: str):
    """Assert that a template parses without errors."""
    ast = parse(template)
    assert ast is not None
    return ast


def assert_validates_successfully(template: str, strict_html: bool = False):
    """Assert that a template validates without errors."""
    is_valid, errors = validate_template(template, strict_html=strict_html)
    assert is_valid, f"Validation failed: {errors}"
    return is_valid


def assert_formats_successfully(template: str, options: FormatOptions = None):
    """Assert that a template formats without errors."""
    formatted = format_template(template, options=options)
    assert formatted is not None
    return formatted


# Make helper functions available via pytest
pytest.assert_parses_successfully = assert_parses_successfully
pytest.assert_validates_successfully = assert_validates_successfully
pytest.assert_formats_successfully = assert_formats_successfully
