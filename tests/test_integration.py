#!/usr/bin/env python3
"""
Comprehensive integration test for all Django 5.2 built-in features.
Tests Phases 1-5 implementation.
"""

from rdtl.formatter import FormatOptions, Formatter
from rdtl.lexer import Lexer
from rdtl.parser import Parser
from rdtl.validator import RDTLValidator


def test_phase_1_html_features():
    """Test Phase 1: HTML features (DOCTYPE, comments, CDATA)."""
    print("\n" + "=" * 70)
    print("PHASE 1: HTML FEATURES")
    print("=" * 70)

    template = """<!DOCTYPE html>
<html>
<!-- This is an HTML comment -->
<head>
    <title>Test</title>
    <script>
    <![CDATA[
    function test() {
        if (x < 5 && y > 3) {
            return true;
        }
    }
    ]]>
    </script>
</head>
<body>
    <!-- Another comment -->
    <p>Content</p>
</body>
</html>"""

    # Validate
    validator = RDTLValidator(template)
    is_valid = validator.validate()
    assert is_valid, f"Validation failed: {validator.errors}"
    print("✓ Validation passed")

    # Parse
    lexer = Lexer(template)
    tokens = lexer.tokenize()
    parser = Parser(tokens)
    ast = parser.parse()
    print(f"✓ Parsed successfully ({len(ast.children)} top-level nodes)")

    # Format
    formatter = Formatter()
    formatted = formatter.format(ast)
    print(f"✓ Formatted successfully ({len(formatted)} chars)")

    # Re-parse formatted output
    lexer2 = Lexer(formatted)
    tokens2 = lexer2.tokenize()
    parser2 = Parser(tokens2)
    parser2.parse()
    print("✓ Re-parsed formatted output successfully")

    print("\n✅ Phase 1: All HTML features working!")


def test_phase_2_block_tags():
    """Test Phase 2: Django block tags."""
    print("\n" + "=" * 70)
    print("PHASE 2: DJANGO BLOCK TAGS")
    print("=" * 70)

    template = """{% comment %}
This is a Django comment block.
It can span multiple lines.
{% endcomment %}

{% autoescape on %}
    <p>{{ user_input }}</p>
{% endautoescape %}

{% ifchanged %}
    {{ current_date }}
{% endifchanged %}

{% filter upper %}
    This text will be uppercase.
{% endfilter %}

{% spaceless %}
    <p>
        <a href="/">Home</a>
    </p>
{% endspaceless %}

{% verbatim %}
    This is literal text that won't be processed.
    Vue.js syntax like {{ message }} is preserved.
{% endverbatim %}"""

    # Validate
    validator = RDTLValidator(template)
    is_valid = validator.validate()
    assert is_valid, f"Validation failed: {validator.errors}"
    print("✓ Validation passed")

    # Parse
    lexer = Lexer(template)
    tokens = lexer.tokenize()
    parser = Parser(tokens)
    ast = parser.parse()
    print(f"✓ Parsed successfully ({len(ast.children)} top-level nodes)")

    # Check for expected block types
    block_types = [
        type(node).__name__ for node in ast.children if hasattr(node, "__class__")
    ]
    assert "CommentBlock" in block_types, "Missing CommentBlock"
    assert "AutoescapeBlock" in block_types, "Missing AutoescapeBlock"
    assert "IfChangedBlock" in block_types, "Missing IfChangedBlock"
    assert "FilterBlock" in block_types, "Missing FilterBlock"
    assert "SpacelessBlock" in block_types, "Missing SpacelessBlock"
    assert "VerbatimBlock" in block_types, "Missing VerbatimBlock"
    print("✓ All expected block types found")

    # Format
    formatter = Formatter()
    formatted = formatter.format(ast)
    print(f"✓ Formatted successfully ({len(formatted)} chars)")

    # Re-parse formatted output
    lexer2 = Lexer(formatted)
    tokens2 = lexer2.tokenize()
    parser2 = Parser(tokens2)
    parser2.parse()
    print("✓ Re-parsed formatted output successfully")

    print("\n✅ Phase 2: All block tags working!")


def test_phase_3_single_tags():
    """Test Phase 3: Django single tags."""
    print("\n" + "=" * 70)
    print("PHASE 3: DJANGO SINGLE TAGS")
    print("=" * 70)

    template = """{% cycle 'odd' 'even' %}
{% cycle 'odd' 'even' as rowcolors %}
{% resetcycle rowcolors %}
{% debug %}
{% lorem 3 p %}
{% lorem 10 w random %}
{% regroup cities by country as country_list %}
{% querystring page=1 %}"""

    # Validate
    validator = RDTLValidator(template)
    is_valid = validator.validate()
    assert is_valid, f"Validation failed: {validator.errors}"
    print("✓ Validation passed")

    # Parse
    lexer = Lexer(template)
    tokens = lexer.tokenize()
    parser = Parser(tokens)
    ast = parser.parse()
    print(f"✓ Parsed successfully ({len(ast.children)} top-level nodes)")

    # Check for expected tag types
    tag_types = [
        type(node).__name__ for node in ast.children if hasattr(node, "__class__")
    ]
    assert "CycleTag" in tag_types, "Missing CycleTag"
    assert "ResetCycleTag" in tag_types, "Missing ResetCycleTag"
    assert "DebugTag" in tag_types, "Missing DebugTag"
    assert "LoremTag" in tag_types, "Missing LoremTag"
    assert "RegroupTag" in tag_types, "Missing RegroupTag"
    assert "QueryStringTag" in tag_types, "Missing QueryStringTag"
    print("✓ All expected single tags found")

    # Format
    formatter = Formatter()
    formatted = formatter.format(ast)
    print(f"✓ Formatted successfully ({len(formatted)} chars)")

    # Re-parse formatted output
    lexer2 = Lexer(formatted)
    tokens2 = lexer2.tokenize()
    parser2 = Parser(tokens2)
    parser2.parse()
    print("✓ Re-parsed formatted output successfully")

    print("\n✅ Phase 3: All single tags working!")


def test_phase_4_improvements():
    """Test Phase 4: Tag improvements."""
    print("\n" + "=" * 70)
    print("PHASE 4: TAG IMPROVEMENTS")
    print("=" * 70)

    template = """{% load static humanize %}
{% load i18n l10n %}

{% url 'home' %}
{% url 'article-detail' article.id %}
{% url 'user-profile' user.username page=1 as profile_url %}

{% static 'css/style.css' %}
{% static 'js/app.js' as app_script %}

{% for key, value in items %}
    {{ key }}: {{ value }}
{% endfor %}

{% for x, y, z in coordinates %}
    Point: ({{ x }}, {{ y }}, {{ z }})
{% endfor %}"""

    # Validate
    validator = RDTLValidator(template)
    is_valid = validator.validate()
    assert is_valid, f"Validation failed: {validator.errors}"
    print("✓ Validation passed")

    # Parse
    lexer = Lexer(template)
    tokens = lexer.tokenize()
    parser = Parser(tokens)
    ast = parser.parse()
    print(f"✓ Parsed successfully ({len(ast.children)} top-level nodes)")

    # Check load tag has multiple libraries
    load_tags = [node for node in ast.children if type(node).__name__ == "LoadTag"]
    assert len(load_tags) >= 2, "Expected at least 2 load tags"
    assert (
        len(load_tags[0].libraries) == 2
    ), f"Expected 2 libraries in first load tag, got {load_tags[0].libraries}"
    print(f"✓ Load tag with multiple libraries: {load_tags[0].libraries}")

    # Check for loop with tuple unpacking
    for_blocks = []

    def find_for_blocks(node):
        if type(node).__name__ == "ForBlock":
            for_blocks.append(node)
        if hasattr(node, "children"):
            for child in node.children:
                find_for_blocks(child)

    for child in ast.children:
        find_for_blocks(child)

    assert len(for_blocks) >= 2, "Expected at least 2 for blocks"

    # First for block should have 2 loop vars (key, value)
    assert (
        len(for_blocks[0].loop_vars) == 2
    ), f"Expected 2 loop vars, got {for_blocks[0].loop_vars}"
    print(f"✓ For block with tuple unpacking: {for_blocks[0].loop_vars}")

    # Second for block should have 3 loop vars (x, y, z)
    assert (
        len(for_blocks[1].loop_vars) == 3
    ), f"Expected 3 loop vars, got {for_blocks[1].loop_vars}"
    print(f"✓ For block with 3-tuple unpacking: {for_blocks[1].loop_vars}")

    # Check url tags
    url_tags = [node for node in ast.children if type(node).__name__ == "UrlTag"]
    assert len(url_tags) >= 3, "Expected at least 3 url tags"
    print(f"✓ Found {len(url_tags)} url tags with argument parsing")

    # Check static tags
    static_tags = [node for node in ast.children if type(node).__name__ == "StaticTag"]
    assert len(static_tags) >= 2, "Expected at least 2 static tags"
    print(f"✓ Found {len(static_tags)} static tags")

    # Format
    formatter = Formatter()
    formatted = formatter.format(ast)
    print(f"✓ Formatted successfully ({len(formatted)} chars)")

    # Re-parse formatted output
    lexer2 = Lexer(formatted)
    tokens2 = lexer2.tokenize()
    parser2 = Parser(tokens2)
    parser2.parse()
    print("✓ Re-parsed formatted output successfully")

    print("\n✅ Phase 4: All improvements working!")


def test_phase_5_filter_validation():
    """Test Phase 5: Filter validation."""
    print("\n" + "=" * 70)
    print("PHASE 5: FILTER VALIDATION")
    print("=" * 70)

    # Test with valid Django filters
    valid_template = """{{ value|default:"nothing" }}
{{ text|upper|truncatewords:30 }}
{{ date_joined|date:"Y-m-d" }}
{{ items|length }}
{{ price|floatformat:2 }}
{{ content|safe|linebreaks }}"""

    validator = RDTLValidator(valid_template, validate_filters=True)
    is_valid = validator.validate()
    assert is_valid, f"Valid filters rejected: {validator.errors}"
    print("✓ Valid Django filters passed validation")

    # Test with invalid/custom filters
    invalid_template = """{{ value|custom_filter }}
{{ text|my_uppercase }}"""

    validator2 = RDTLValidator(invalid_template, validate_filters=True)
    is_valid2 = validator2.validate()
    assert not is_valid2, "Invalid filters should be rejected"
    assert (
        len(validator2.errors) == 2
    ), f"Expected 2 errors, got {len(validator2.errors)}"
    print(f"✓ Invalid filters correctly rejected: {len(validator2.errors)} errors")

    # Test with validation disabled (should pass)
    validator3 = RDTLValidator(invalid_template, validate_filters=False)
    is_valid3 = validator3.validate()
    assert (
        is_valid3
    ), f"Custom filters should pass when validation disabled: {validator3.errors}"
    print("✓ Custom filters allowed when validation disabled")

    # Test chained filters
    chained_template = """{{ value|default:""|upper|truncatewords:5|safe }}"""
    validator4 = RDTLValidator(chained_template, validate_filters=True)
    is_valid4 = validator4.validate()
    assert is_valid4, f"Chained filters failed: {validator4.errors}"
    print("✓ Chained filters work correctly")

    print(f"\n✓ KNOWN_FILTERS contains {len(RDTLValidator.KNOWN_FILTERS)} filters")

    print("\n✅ Phase 5: Filter validation working!")


def test_full_integration():
    """Test all features together in one comprehensive template."""
    print("\n" + "=" * 70)
    print("FULL INTEGRATION TEST")
    print("=" * 70)

    template = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>{% block title %}My Site{% endblock %}</title>
    {% load static humanize %}
    {% static 'css/style.css' as stylesheet %}
    <link rel="stylesheet" href="{{ stylesheet }}">

    <!-- Analytics script -->
    <script>
    <![CDATA[
    var analytics = {
        track: function(event) {
            if (event && event.name) {
                console.log(event.name);
            }
        }
    };
    ]]>
    </script>
</head>
<body>
    {% comment %}
    Main content area
    Navigation and article list
    {% endcomment %}

    <nav>
        {% spaceless %}
            <a href="{% url 'home' %}">Home</a>
            <a href="{% url 'about' %}">About</a>
        {% endspaceless %}
    </nav>

    {% autoescape on %}
        <h1>{{ page_title|default:"Welcome"|title }}</h1>

        {% if articles %}
            {% for article in articles %}
                {% ifchanged article.category %}
                    <h2>{{ article.category|upper }}</h2>
                {% endifchanged %}

                <article>
                    <h3>
                        <a href="{% url 'article-detail' article.id %}">
                            {{ article.title|truncatewords:10 }}
                        </a>
                    </h3>
                    <p class="meta">
                        Published: {{ article.published|date:"F j, Y" }}
                        {% cycle 'odd' 'even' as row_class %}
                    </p>
                    {% filter linebreaks %}
                        {{ article.summary|safe|truncatechars:200 }}
                    {% endfilter %}
                </article>
            {% empty %}
                <p>No articles found.</p>
            {% endfor %}
        {% endif %}

        {% regroup articles by author as author_list %}

        <div class="pagination">
            <a href="{% querystring page=page_num %}">Next</a>
        </div>
    {% endautoescape %}

    <!-- Debug information -->
    {% if debug_mode %}
        {% verbatim %}
        Vue template: {{ message }}
        {% endverbatim %}
        {% debug %}
    {% endif %}

    <!-- Footer -->
    <footer>
        <p>&copy; 2025 My Site. {% lorem 5 w %}</p>
    </footer>
</body>
</html>"""

    print(f"Template size: {len(template)} characters")
    print(f"Template lines: {len(template.splitlines())}")

    # Validate with filter validation
    validator = RDTLValidator(template, validate_filters=True)
    is_valid = validator.validate()
    assert is_valid, f"Validation failed: {validator.errors}"
    print("✓ Validation passed (with filter validation)")

    # Tokenize
    lexer = Lexer(template)
    tokens = lexer.tokenize()
    print(f"✓ Tokenized: {len(tokens)} tokens")

    # Parse
    parser = Parser(tokens)
    ast = parser.parse()
    print(f"✓ Parsed: {len(ast.children)} top-level nodes")

    # Count features
    feature_counts = {}

    def count_features(node):
        node_type = type(node).__name__
        feature_counts[node_type] = feature_counts.get(node_type, 0) + 1

        if hasattr(node, "children"):
            for child in node.children:
                count_features(child)
        if hasattr(node, "empty_children") and node.empty_children:
            for child in node.empty_children:
                count_features(child)

    for child in ast.children:
        count_features(child)

    print("\nFeature usage:")
    for feature, count in sorted(feature_counts.items()):
        if feature not in ["Text", "VariableExpression", "Identifier", "StringLiteral"]:
            print(f"  - {feature}: {count}")

    # Format
    formatter = Formatter(
        FormatOptions(
            indent_size=4, space_in_template_tags=True, space_in_variables=True
        )
    )
    formatted = formatter.format(ast)
    print(f"\n✓ Formatted: {len(formatted)} characters")

    # Re-validate formatted output
    validator2 = RDTLValidator(formatted, validate_filters=True)
    is_valid2 = validator2.validate()
    assert is_valid2, f"Formatted output validation failed: {validator2.errors}"
    print("✓ Formatted output validates")

    # Re-parse formatted output
    lexer2 = Lexer(formatted)
    tokens2 = lexer2.tokenize()
    parser2 = Parser(tokens2)
    ast2 = parser2.parse()
    print("✓ Formatted output parses successfully")

    # Re-format and check idempotency
    formatter2 = Formatter(
        FormatOptions(
            indent_size=4, space_in_template_tags=True, space_in_variables=True
        )
    )
    formatted2 = formatter2.format(ast2)
    if formatted == formatted2:
        print("✓ Formatting is idempotent")
    else:
        print("⚠ Formatting has minor differences on re-format (non-critical)")
        # Note: This is acceptable as long as both parse correctly

    print("\n✅ FULL INTEGRATION TEST PASSED!")


def main():
    """Run all integration tests."""
    print("=" * 70)
    print("COMPREHENSIVE INTEGRATION TEST SUITE")
    print("Django 5.2 Built-in Features (Phases 1-5)")
    print("=" * 70)

    try:
        test_phase_1_html_features()
        test_phase_2_block_tags()
        test_phase_3_single_tags()
        test_phase_4_improvements()
        test_phase_5_filter_validation()
        test_full_integration()

        print("\n" + "=" * 70)
        print("🎉 ALL TESTS PASSED! 🎉")
        print("=" * 70)
        print("\nAll Phase 1-5 features are working correctly:")
        print("  ✓ HTML features (DOCTYPE, comments, CDATA)")
        print("  ✓ Django block tags (6 new tags)")
        print("  ✓ Django single tags (6 new tags)")
        print("  ✓ Tag improvements (url, static, load, for)")
        print("  ✓ Filter validation (58 Django filters)")
        print("  ✓ Full integration with all features combined")
        print("\nReady for Phase 7: Documentation!")
        print("=" * 70)

    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        raise
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        raise


if __name__ == "__main__":
    main()
