#!/usr/bin/env python3
"""
Test dynamic attribute names - Phase 2 (simple cases where entire name is template).
"""

import traceback

from rdtl.formatter import Formatter
from rdtl.lexer import Lexer
from rdtl.parser import Parser


def test_simple_variable_attribute_name():
    """Test {{ attr_name }}="value" pattern."""
    print("\n" + "=" * 70)
    print("TEST: Simple Variable Attribute Name")
    print("=" * 70)

    template = '<div {{ attr_name }}="value">Content</div>'

    # Lex
    lexer = Lexer(template)
    tokens = lexer.tokenize()
    print(f"✓ Lexed successfully ({len(tokens)} tokens)")

    # Print tokens for debugging
    for i, token in enumerate(tokens):
        print(f"  Token {i}: {token.type.name} = {repr(token.value)}")

    # Parse
    parser = Parser(tokens)
    ast = parser.parse()
    print("✓ Parsed successfully")

    # Check attribute
    div = ast.children[0]
    assert len(div.attributes) == 1
    assert div.attributes[0].name == "{{ attr_name }}"
    assert div.attributes[0].value == "value"
    assert div.attributes[0].is_dynamic_name
    print(f"✓ Dynamic attribute parsed: {div.attributes[0]}")

    # Format
    formatter = Formatter()
    formatted = formatter.format(ast)
    print(f"✓ Formatted: {formatted.strip()}")

    # Re-parse
    lexer2 = Lexer(formatted)
    tokens2 = lexer2.tokenize()
    parser2 = Parser(tokens2)
    parser2.parse()
    print("✓ Round-trip successful")

    print("\n✅ Simple variable attribute name test passed!")


def test_variable_with_filter():
    """Test {{ attr|filter }}="value" pattern."""
    print("\n" + "=" * 70)
    print("TEST: Variable with Filter")
    print("=" * 70)

    template = '<div {{ attr_name|safe }}="value">Content</div>'

    # Lex
    lexer = Lexer(template)
    tokens = lexer.tokenize()
    print("✓ Lexed successfully")

    # Parse
    parser = Parser(tokens)
    ast = parser.parse()
    print("✓ Parsed successfully")

    # Check attribute
    div = ast.children[0]
    assert len(div.attributes) == 1
    assert div.attributes[0].name == "{{ attr_name|safe }}"
    assert div.attributes[0].is_dynamic_name
    print("✓ Dynamic attribute with filter parsed correctly")

    print("\n✅ Variable with filter test passed!")


def test_template_tag_attribute_name():
    """Test {% if x %}attr1{% else %}attr2{% endif %}="value" pattern."""
    print("\n" + "=" * 70)
    print("TEST: Template Tag Attribute Name")
    print("=" * 70)

    template = '<div {% if active %}data-active{% else %}data-inactive{% endif %}="true">Content</div>'

    # Lex
    lexer = Lexer(template)
    tokens = lexer.tokenize()
    print("✓ Lexed successfully")

    # Parse
    parser = Parser(tokens)
    ast = parser.parse()
    print("✓ Parsed successfully")

    # Check attribute
    div = ast.children[0]
    assert len(div.attributes) == 1
    assert "{% if active %}" in div.attributes[0].name
    assert div.attributes[0].is_dynamic_name
    print("✓ Dynamic attribute with template tag parsed correctly")

    # Format
    formatter = Formatter()
    formatter.format(ast)
    print("✓ Formatted successfully")

    print("\n✅ Template tag attribute name test passed!")


def test_multiple_attributes_mixed():
    """Test mix of static and dynamic attribute names."""
    print("\n" + "=" * 70)
    print("TEST: Mixed Static and Dynamic Attributes")
    print("=" * 70)

    template = '<div id="test" {{ dynamic_attr }}="value1" class="foo" {{ another }}="value2">Content</div>'

    # Lex
    lexer = Lexer(template)
    tokens = lexer.tokenize()
    print("✓ Lexed successfully")

    # Parse
    parser = Parser(tokens)
    ast = parser.parse()
    print("✓ Parsed successfully")

    # Check attributes
    div = ast.children[0]
    assert len(div.attributes) == 4

    # Static attributes
    assert div.attributes[0].name == "id"
    assert div.attributes[0].is_dynamic_name is False

    # Dynamic attribute
    assert div.attributes[1].name == "{{ dynamic_attr }}"
    assert div.attributes[1].is_dynamic_name

    # Static attribute
    assert div.attributes[2].name == "class"
    assert div.attributes[2].is_dynamic_name is False

    # Dynamic attribute
    assert div.attributes[3].name == "{{ another }}"
    assert div.attributes[3].is_dynamic_name

    print("✓ Mixed attributes parsed correctly:")
    for attr in div.attributes:
        dynamic = "[dynamic]" if attr.is_dynamic_name else "[static]"
        print(f"    {dynamic} {attr.name}={repr(attr.value)}")

    print("\n✅ Mixed attributes test passed!")


def test_boolean_dynamic_attribute():
    """Test dynamic boolean attribute (no value)."""
    print("\n" + "=" * 70)
    print("TEST: Boolean Dynamic Attribute")
    print("=" * 70)

    template = "<button {{ attr_name }}>Click</button>"

    # Lex
    lexer = Lexer(template)
    tokens = lexer.tokenize()
    print("✓ Lexed successfully")

    # Parse
    parser = Parser(tokens)
    ast = parser.parse()
    print("✓ Parsed successfully")

    # Check attribute
    button = ast.children[0]
    assert len(button.attributes) == 1
    assert button.attributes[0].name == "{{ attr_name }}"
    assert button.attributes[0].value is None  # Boolean attribute
    assert button.attributes[0].is_dynamic_name
    print("✓ Boolean dynamic attribute parsed correctly")

    print("\n✅ Boolean dynamic attribute test passed!")


def test_quotes_in_attribute_name():
    """Test that quotes work independently in attribute names."""
    print("\n" + "=" * 70)
    print("TEST: Quotes in Attribute Name (Independent)")
    print("=" * 70)

    # Double quotes in name, single quotes in value - should work
    template = "<div {{ \"attr\" }}='value'>Content</div>"

    # Lex
    lexer = Lexer(template)
    tokens = lexer.tokenize()
    print("✓ Lexed with double quotes in name")

    # Parse
    parser = Parser(tokens)
    parser.parse()
    print("✓ Parsed successfully")

    # Now try single quotes in name, double quotes in value
    template2 = "<div {{ 'attr' }}=\"value\">Content</div>"

    lexer2 = Lexer(template2)
    tokens2 = lexer2.tokenize()
    print("✓ Lexed with single quotes in name")

    parser2 = Parser(tokens2)
    parser2.parse()
    print("✓ Parsed successfully")

    print("\n✅ Independent quote rules test passed!")


def main():
    """Run all Phase 2 tests."""
    print("=" * 70)
    print("PHASE 2: SIMPLE DYNAMIC ATTRIBUTE NAMES TEST SUITE")
    print("=" * 70)

    try:
        test_simple_variable_attribute_name()
        test_variable_with_filter()
        test_template_tag_attribute_name()
        test_multiple_attributes_mixed()
        test_boolean_dynamic_attribute()
        test_quotes_in_attribute_name()

        print("\n" + "=" * 70)
        print("🎉 ALL PHASE 2 TESTS PASSED! 🎉")
        print("=" * 70)
        print("\nDynamic attribute names now working:")
        print('  ✓ {{ attr_name }}="value"')
        print('  ✓ {{ attr|filter }}="value"')
        print('  ✓ {% if x %}attr1{% else %}attr2{% endif %}="value"')
        print("  ✓ Mixed static and dynamic attributes")
        print("  ✓ Boolean dynamic attributes")
        print("  ✓ Independent quote rules")
        print("=" * 70)

    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        raise
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        traceback.print_exc()
        raise


if __name__ == "__main__":
    main()
