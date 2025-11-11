#!/usr/bin/env python3
"""
Test hyphenated static attribute names (Phase 1).
Tests data-*, aria-*, hx-*, and other HTML5 attributes with hyphens.
"""

from rdtl.formatter import Formatter
from rdtl.lexer import Lexer
from rdtl.parser import Parser


def test_data_attributes():
    """Test data-* attributes."""
    print("\n" + "=" * 70)
    print("TEST: Data Attributes")
    print("=" * 70)

    template = '<div data-item="123" data-user-id="456">Content</div>'

    # Lex
    lexer = Lexer(template)
    tokens = lexer.tokenize()
    print(f"✓ Lexed successfully ({len(tokens)} tokens)")

    # Parse
    parser = Parser(tokens)
    ast = parser.parse()
    print("✓ Parsed successfully")

    # Check attributes
    html_element = ast.children[0]
    assert len(html_element.attributes) == 2
    assert html_element.attributes[0].name == "data-item"
    assert html_element.attributes[0].value == "123"
    assert html_element.attributes[1].name == "data-user-id"
    assert html_element.attributes[1].value == "456"
    print(
        f"✓ Attributes parsed correctly: {[attr.name for attr in html_element.attributes]}"
    )

    # Format
    formatter = Formatter()
    formatted = formatter.format(ast)
    print(f"✓ Formatted successfully: {formatted.strip()}")

    print("\n✅ Data attributes test passed!")


def test_aria_attributes():
    """Test aria-* attributes."""
    print("\n" + "=" * 70)
    print("TEST: ARIA Attributes")
    print("=" * 70)

    template = '<button aria-label="Close" aria-pressed="false">X</button>'

    # Lex
    lexer = Lexer(template)
    tokens = lexer.tokenize()
    print("✓ Lexed successfully")

    # Parse
    parser = Parser(tokens)
    ast = parser.parse()
    print("✓ Parsed successfully")

    # Check attributes
    button = ast.children[0]
    assert len(button.attributes) == 2
    assert button.attributes[0].name == "aria-label"
    assert button.attributes[0].value == "Close"
    assert button.attributes[1].name == "aria-pressed"
    assert button.attributes[1].value == "false"
    print(f"✓ Attributes parsed correctly: {[attr.name for attr in button.attributes]}")

    print("\n✅ ARIA attributes test passed!")


def test_htmx_attributes():
    """Test hx-* attributes (HTMX framework)."""
    print("\n" + "=" * 70)
    print("TEST: HTMX Attributes")
    print("=" * 70)

    template = '<div hx-get="/api" hx-target="#result" hx-swap="innerHTML">Load</div>'

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
    assert len(div.attributes) == 3
    assert div.attributes[0].name == "hx-get"
    assert div.attributes[0].value == "/api"
    assert div.attributes[1].name == "hx-target"
    assert div.attributes[1].value == "#result"
    assert div.attributes[2].name == "hx-swap"
    assert div.attributes[2].value == "innerHTML"
    print(f"✓ Attributes parsed correctly: {[attr.name for attr in div.attributes]}")

    print("\n✅ HTMX attributes test passed!")


def test_alpine_attributes():
    """Test x-* attributes (Alpine.js framework)."""
    print("\n" + "=" * 70)
    print("TEST: Alpine.js Attributes")
    print("=" * 70)

    template = '<div x-data="{open: false}" x-show="open" x-on:click="open = true">Toggle</div>'

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
    assert len(div.attributes) == 3
    assert div.attributes[0].name == "x-data"
    assert div.attributes[1].name == "x-show"
    assert div.attributes[2].name == "x-on:click"
    print(f"✓ Attributes parsed correctly: {[attr.name for attr in div.attributes]}")

    print("\n✅ Alpine.js attributes test passed!")


def test_multiple_hyphens():
    """Test attributes with multiple hyphens."""
    print("\n" + "=" * 70)
    print("TEST: Multiple Hyphens")
    print("=" * 70)

    template = (
        '<div data-user-profile-id="123" aria-describedby-ref="desc">Content</div>'
    )

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
    assert len(div.attributes) == 2
    assert div.attributes[0].name == "data-user-profile-id"
    assert div.attributes[1].name == "aria-describedby-ref"
    print("✓ Attributes with multiple hyphens parsed correctly")

    print("\n✅ Multiple hyphens test passed!")


def test_round_trip():
    """Test parse → format → re-parse for hyphenated attributes."""
    print("\n" + "=" * 70)
    print("TEST: Round Trip")
    print("=" * 70)

    template = '<div data-item="123" aria-label="Info" hx-get="/api">Content</div>'

    # First parse
    lexer = Lexer(template)
    tokens = lexer.tokenize()
    parser = Parser(tokens)
    ast = parser.parse()
    print("✓ First parse successful")

    # Format
    formatter = Formatter()
    formatted = formatter.format(ast)
    print(f"✓ Formatted: {formatted.strip()}")

    # Re-parse formatted output
    lexer2 = Lexer(formatted)
    tokens2 = lexer2.tokenize()
    parser2 = Parser(tokens2)
    ast2 = parser2.parse()
    print("✓ Second parse successful")

    # Verify attributes match
    div1 = ast.children[0]
    div2 = ast2.children[0]
    assert len(div1.attributes) == len(div2.attributes)
    for attr1, attr2 in zip(div1.attributes, div2.attributes):
        assert attr1.name == attr2.name
        assert attr1.value == attr2.value
    print("✓ Round trip preserves attributes")

    print("\n✅ Round trip test passed!")


def main():
    """Run all Phase 1 tests."""
    print("=" * 70)
    print("PHASE 1: HYPHENATED STATIC ATTRIBUTES TEST SUITE")
    print("=" * 70)

    try:
        test_data_attributes()
        test_aria_attributes()
        test_htmx_attributes()
        test_alpine_attributes()
        test_multiple_hyphens()
        test_round_trip()

        print("\n" + "=" * 70)
        print("🎉 ALL PHASE 1 TESTS PASSED! 🎉")
        print("=" * 70)
        print("\nHyphenated attributes now working:")
        print("  ✓ data-* attributes (HTML5)")
        print("  ✓ aria-* attributes (accessibility)")
        print("  ✓ hx-* attributes (HTMX)")
        print("  ✓ x-* attributes (Alpine.js)")
        print("  ✓ Multiple hyphens in names")
        print("  ✓ Round-trip parsing")
        print("=" * 70)

    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        raise
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        raise


if __name__ == "__main__":
    main()
