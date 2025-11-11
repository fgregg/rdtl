#!/usr/bin/env python3
"""
Test dynamic attribute names - Phase 3 (mixed static + dynamic parts).
"""

from rdtl.formatter import Formatter
from rdtl.lexer import Lexer
from rdtl.parser import Parser


def test_prefix_dynamic_suffix():
    """Test data-{{ id }}-item pattern."""
    print("\n" + "=" * 70)
    print("TEST: Prefix + Dynamic + Suffix")
    print("=" * 70)

    template = '<div data-{{ item_id }}-active="true">Content</div>'

    # Lex
    lexer = Lexer(template)
    tokens = lexer.tokenize()
    print("✓ Lexed successfully")

    # Print tokens
    for i, token in enumerate(tokens):
        if token.type.name.startswith("ATTR"):
            print(f"  Token {i}: {token.type.name} = {repr(token.value)}")

    # Parse
    parser = Parser(tokens)
    ast = parser.parse()
    print("✓ Parsed successfully")

    # Check attribute
    div = ast.children[0]
    assert len(div.attributes) == 1
    assert div.attributes[0].name == "data-{{ item_id }}-active"
    assert div.attributes[0].value == "true"
    assert div.attributes[0].is_dynamic_name == True
    print(f"✓ Mixed attribute parsed: {div.attributes[0].name}")

    # Format
    formatter = Formatter()
    formatted = formatter.format(ast)
    print(f"✓ Formatted: {formatted.strip()}")

    # Re-parse
    lexer2 = Lexer(formatted)
    tokens2 = lexer2.tokenize()
    parser2 = Parser(tokens2)
    ast2 = parser2.parse()
    print("✓ Round-trip successful")

    print("\n✅ Prefix + Dynamic + Suffix test passed!")


def test_data_attribute_dynamic():
    """Test data-{{ type }}="value" pattern."""
    print("\n" + "=" * 70)
    print("TEST: Data Attribute Dynamic")
    print("=" * 70)

    template = '<div data-{{ attr_type }}="value">Content</div>'

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
    assert div.attributes[0].name == "data-{{ attr_type }}"
    assert div.attributes[0].is_dynamic_name == True
    print("✓ data-* attribute with dynamic part works")

    print("\n✅ Data attribute dynamic test passed!")


def test_htmx_dynamic():
    """Test hx-{{ action }}="/url" pattern."""
    print("\n" + "=" * 70)
    print("TEST: HTMX Dynamic Action")
    print("=" * 70)

    template = '<div hx-{{ action }}="/api/endpoint">Load</div>'

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
    assert div.attributes[0].name == "hx-{{ action }}"
    assert div.attributes[0].value == "/api/endpoint"
    assert div.attributes[0].is_dynamic_name == True
    print("✓ HTMX attribute with dynamic part works")

    print("\n✅ HTMX dynamic test passed!")


def test_alpine_dynamic():
    """Test x-{{ directive }}="value" pattern."""
    print("\n" + "=" * 70)
    print("TEST: Alpine.js Dynamic Directive")
    print("=" * 70)

    template = '<div x-{{ directive }}="value">Content</div>'

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
    assert div.attributes[0].name == "x-{{ directive }}"
    assert div.attributes[0].is_dynamic_name == True
    print("✓ Alpine.js attribute with dynamic part works")

    print("\n✅ Alpine.js dynamic test passed!")


def test_multiple_dynamic_parts():
    """Test {{ prefix }}-{{ id }}-{{ suffix }} pattern."""
    print("\n" + "=" * 70)
    print("TEST: Multiple Dynamic Parts")
    print("=" * 70)

    template = '<div {{ prefix }}-item-{{ id }}-{{ suffix }}="value">Content</div>'

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
    assert "{{ prefix }}" in div.attributes[0].name
    assert "{{ id }}" in div.attributes[0].name
    assert "{{ suffix }}" in div.attributes[0].name
    assert div.attributes[0].is_dynamic_name == True
    print(f"✓ Multiple dynamic parts: {div.attributes[0].name}")

    # Format
    formatter = Formatter()
    formatted = formatter.format(ast)
    print("✓ Formatted successfully")

    print("\n✅ Multiple dynamic parts test passed!")


def test_dynamic_with_template_tag():
    """Test data-{% if x %}active{% else %}inactive{% endif %} pattern."""
    print("\n" + "=" * 70)
    print("TEST: Dynamic with Template Tag")
    print("=" * 70)

    template = (
        '<div data-{% if active %}on{% else %}off{% endif %}="true">Content</div>'
    )

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
    assert "data-" in div.attributes[0].name
    assert "{% if active %}" in div.attributes[0].name
    assert div.attributes[0].is_dynamic_name == True
    print("✓ Dynamic with template tag works")

    print("\n✅ Dynamic with template tag test passed!")


def test_complex_real_world():
    """Test complex real-world example with multiple mixed attributes."""
    print("\n" + "=" * 70)
    print("TEST: Complex Real-World Example")
    print("=" * 70)

    template = """<div
    id="container"
    data-user-{{ user.id }}="active"
    hx-{{ http_method }}="/api/{{ endpoint }}"
    class="item-{{ status }}"
    {{ custom_attr }}="{{ custom_value }}"
    aria-label="Item">
    Content
</div>"""

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
    print(f"✓ Found {len(div.attributes)} attributes:")
    for i, attr in enumerate(div.attributes):
        dynamic = "[dynamic]" if attr.is_dynamic_name else "[static]"
        print(f"    {i+1}. {dynamic} {attr.name}")

    # Verify mix of static and dynamic
    static_count = sum(1 for attr in div.attributes if not attr.is_dynamic_name)
    dynamic_count = sum(1 for attr in div.attributes if attr.is_dynamic_name)
    print(f"✓ Static: {static_count}, Dynamic: {dynamic_count}")

    # Format
    formatter = Formatter()
    formatted = formatter.format(ast)
    print("✓ Formatted successfully")

    print("\n✅ Complex real-world test passed!")


def main():
    """Run all Phase 3 tests."""
    print("=" * 70)
    print("PHASE 3: MIXED DYNAMIC ATTRIBUTE NAMES TEST SUITE")
    print("=" * 70)

    try:
        test_prefix_dynamic_suffix()
        test_data_attribute_dynamic()
        test_htmx_dynamic()
        test_alpine_dynamic()
        test_multiple_dynamic_parts()
        test_dynamic_with_template_tag()
        test_complex_real_world()

        print("\n" + "=" * 70)
        print("🎉 ALL PHASE 3 TESTS PASSED! 🎉")
        print("=" * 70)
        print("\nMixed dynamic attribute names now working:")
        print('  ✓ data-{{ id }}-item="value"')
        print('  ✓ hx-{{ action }}="/url"')
        print('  ✓ x-{{ directive }}="value"')
        print('  ✓ {{ prefix }}-{{ id }}-{{ suffix }}="value"')
        print('  ✓ data-{% if x %}on{% else %}off{% endif %}="value"')
        print("  ✓ Complex real-world templates")
        print("=" * 70)

    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        raise
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback

        traceback.print_exc()
        raise


if __name__ == "__main__":
    main()
