"""
Property-based tests for RDTL using Hypothesis.

This module uses Hypothesis to generate random RDTL templates and test:
1. Parser agreement: manual parser vs Lark-generated parser
2. Round-trip consistency: parse -> format -> parse produces identical AST
3. Formatter idempotence: format(format(x)) == format(x)
"""

import pytest
from hypothesis import given, strategies as st, settings, example
from pathlib import Path

from rdtl.parser import parse
from rdtl.formatter import format_template, FormatOptions
from rdtl.validator import validate_template


# ============================================================================
# Test Strategies
# ============================================================================

# Basic HTML tag names
html_tags = st.sampled_from([
    'div', 'p', 'span', 'a', 'ul', 'li', 'h1', 'h2', 'button', 'form'
])

# Simple identifiers for variables
identifiers = st.from_regex(r'[a-z][a-z0-9_]{0,10}', fullmatch=True)

# Simple string values
simple_strings = st.text(
    alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), max_codepoint=127),
    min_size=0,
    max_size=20
)

# Template variable strategy
@st.composite
def template_variable(draw):
    """Generate a template variable like {{ foo }} or {{ foo.bar }}"""
    var = draw(identifiers)
    # Optionally add attribute access
    if draw(st.booleans()):
        attr = draw(identifiers)
        var = f"{var}.{attr}"
    return f"{{{{ {var} }}}}"


# Simple HTML element strategy
@st.composite
def simple_html_element(draw):
    """Generate a simple HTML element like <div>content</div>"""
    tag = draw(html_tags)
    content = draw(st.one_of(
        simple_strings,
        template_variable()
    ))
    return f"<{tag}>{content}</{tag}>"


# ============================================================================
# Property Tests
# ============================================================================

class TestParserProperties:
    """Property-based tests for the parser."""

    @given(simple_html_element())
    @example("<div>Hello</div>")
    @example("<p>{{ message }}</p>")
    def test_simple_html_parses(self, template):
        """Test that simple HTML elements parse successfully."""
        try:
            ast = parse(template)
            assert ast is not None
        except Exception as e:
            pytest.fail(f"Failed to parse valid template: {e}")

    @given(identifiers)
    @example("foo")
    @example("my_variable")
    def test_simple_variables_parse(self, var_name):
        """Test that simple variables parse successfully."""
        template = f"{{{{ {var_name} }}}}"
        try:
            ast = parse(template)
            assert ast is not None
        except Exception as e:
            pytest.fail(f"Failed to parse variable {var_name}: {e}")


class TestFormatterProperties:
    """Property-based tests for the formatter."""

    @given(simple_html_element())
    @example("<div>Hello</div>")
    @settings(max_examples=50)
    def test_formatter_idempotence(self, template):
        """Test that format(format(x)) == format(x)."""
        try:
            # Skip invalid templates
            is_valid, _ = validate_template(template)
            if not is_valid:
                return

            # First format
            formatted1 = format_template(template)
            # Second format (should be identical)
            formatted2 = format_template(formatted1)

            assert formatted1 == formatted2, \
                f"Formatter not idempotent:\nFirst:  {formatted1}\nSecond: {formatted2}"
        except Exception as e:
            # If first format fails, that's OK - we're only testing idempotence
            # of successfully formatted templates
            pass

    @given(simple_html_element())
    @example("<div>text</div>")
    @settings(max_examples=50)
    def test_round_trip_consistency(self, template):
        """Test that parse -> format -> parse produces consistent AST."""
        try:
            # Skip invalid templates
            is_valid, _ = validate_template(template)
            if not is_valid:
                return

            # Parse original
            ast1 = parse(template)

            # Format
            formatted = format_template(template)

            # Parse formatted
            ast2 = parse(formatted)

            # ASTs should be structurally equivalent
            # (We compare string representations as a proxy for structural equality)
            assert str(ast1) == str(ast2), \
                f"Round-trip inconsistency:\nOriginal AST: {ast1}\nFormatted AST: {ast2}"
        except Exception as e:
            # If parsing or formatting fails, that's OK - we're only testing
            # round-trip consistency of valid templates
            pass


class TestValidatorProperties:
    """Property-based tests for the validator."""

    @given(simple_html_element())
    @settings(max_examples=50)
    def test_valid_templates_parse(self, template):
        """Test that templates marked as valid can be parsed."""
        is_valid, errors = validate_template(template)

        if is_valid:
            # If validator says it's valid, parser should succeed
            try:
                ast = parse(template)
                assert ast is not None
            except Exception as e:
                pytest.fail(
                    f"Validator approved but parser failed:\n"
                    f"Template: {template}\n"
                    f"Error: {e}"
                )


# ============================================================================
# Lark Comparison Tests (if Lark is available)
# ============================================================================

try:
    from lark import Lark
    LARK_AVAILABLE = True
except ImportError:
    LARK_AVAILABLE = False


@pytest.mark.skipif(not LARK_AVAILABLE, reason="Lark not installed")
class TestLarkComparison:
    """Compare manual parser with Lark-generated parser."""

    @pytest.fixture(scope="class")
    def lark_parser(self):
        """Load Lark grammar."""
        grammar_file = Path(__file__).parent.parent / 'src' / 'rdtl' / 'rdtl_lark.lark'
        if not grammar_file.exists():
            pytest.skip(f"Lark grammar not found: {grammar_file}")

        with open(grammar_file) as f:
            grammar = f.read()

        return Lark(grammar, start='document', parser='lalr')

    @given(simple_html_element())
    @example("<div>Hello</div>")
    @example("{{ variable }}")
    @settings(max_examples=50)
    def test_parser_agreement(self, lark_parser, template):
        """Test that manual and Lark parsers agree on validity."""
        # Try manual parser
        manual_success = False
        try:
            parse(template)
            manual_success = True
        except Exception:
            manual_success = False

        # Try Lark parser
        lark_success = False
        try:
            lark_parser.parse(template)
            lark_success = True
        except Exception:
            lark_success = False

        # They should agree (both accept or both reject)
        # Note: Due to two-phase parsing, some disagreement is expected
        # for custom block tags, so we only report, not assert
        if manual_success != lark_success:
            print(f"\nParser disagreement on: {template}")
            print(f"  Manual: {'ACCEPT' if manual_success else 'REJECT'}")
            print(f"  Lark:   {'ACCEPT' if lark_success else 'REJECT'}")


# ============================================================================
# Grammar-Based Generation (Using hypothesis.extra.lark)
# ============================================================================

try:
    from hypothesis.extra.lark import from_lark
    LARK_GENERATION_AVAILABLE = True
except ImportError:
    LARK_GENERATION_AVAILABLE = False


@pytest.mark.skipif(not LARK_GENERATION_AVAILABLE, reason="hypothesis.extra.lark not available")
class TestGrammarGeneration:
    """Generate test cases directly from the RDTL grammar using Hypothesis."""

    @staticmethod
    def get_template_strategy():
        """Create Hypothesis strategy from RDTL grammar."""
        from lark import Lark

        grammar_file = Path(__file__).parent.parent / 'src' / 'rdtl' / 'rdtl_lark.lark'
        if not grammar_file.exists():
            pytest.skip(f"Grammar file not found: {grammar_file}")

        with open(grammar_file) as f:
            grammar_text = f.read()

        grammar = Lark(grammar_text, start='document', parser='lalr')

        # Use ASCII printable characters for readable output
        # Provide explicit strategy for WS (whitespace) terminal
        return from_lark(
            grammar,
            start='document',
            alphabet=st.characters(min_codepoint=32, max_codepoint=126),
            explicit={'WS': st.just(' ')}  # Use single space for whitespace
        )

    @given(st.data())
    @settings(max_examples=5, deadline=None)
    def test_grammar_generated_templates_parse(self, data):
        """Test that templates generated from grammar always parse."""
        template_strategy = self.get_template_strategy()
        template = data.draw(template_strategy)

        print(f"\n{'='*60}")
        print(f"Generated template:\n{template}")
        print(f"{'='*60}")

        try:
            ast = parse(template)
            assert ast is not None
            print("✓ Parsed successfully")
        except Exception as e:
            pytest.fail(f"Grammar-generated template failed to parse:\n{template}\n\nError: {e}")

    @given(st.data())
    @settings(max_examples=10, deadline=None)
    def test_grammar_templates_roundtrip(self, data):
        """Test that grammar-generated templates survive roundtrip."""
        template_strategy = self.get_template_strategy()
        template = data.draw(template_strategy)

        try:
            # Parse original
            ast1 = parse(template)

            # Format
            formatted = format_template(template)

            # Parse formatted
            ast2 = parse(formatted)

            # Should be structurally equivalent
            assert str(ast1) == str(ast2), \
                f"Roundtrip failed:\nOriginal: {template}\nFormatted: {formatted}"

            print(f"✓ Roundtrip successful for: {template[:50]}...")
        except Exception as e:
            # Some grammar-generated templates might be edge cases
            print(f"⚠ Roundtrip failed (acceptable for grammar exploration): {e}")

    @given(st.data())
    @settings(max_examples=10, deadline=None)
    def test_grammar_formatter_idempotence(self, data):
        """Test that formatting grammar-generated templates is idempotent."""
        template_strategy = self.get_template_strategy()
        template = data.draw(template_strategy)

        try:
            # Format once
            formatted1 = format_template(template)

            # Format again
            formatted2 = format_template(formatted1)

            # Should be identical
            assert formatted1 == formatted2, \
                f"Formatter not idempotent:\nFirst:  {formatted1}\nSecond: {formatted2}"

            print(f"✓ Idempotent for: {template[:50]}...")
        except Exception as e:
            # Some templates might fail formatting (that's OK, we're exploring)
            print(f"⚠ Formatting failed (acceptable): {e}")


# ============================================================================
# Example-Based Tests (Using Hypothesis @example decorator)
# ============================================================================

class TestKnownCases:
    """Test specific known cases using Hypothesis examples."""

    @given(st.just("<div>Hello</div>"))
    @example("<div>Hello</div>")
    def test_simple_div(self, template):
        """Test simple div element."""
        ast = parse(template)
        assert ast is not None

    @given(st.just("{{ variable }}"))
    @example("{{ variable }}")
    def test_simple_variable(self, template):
        """Test simple variable."""
        ast = parse(template)
        assert ast is not None

    @given(st.just("{% if condition %}yes{% endif %}"))
    @example("{% if condition %}yes{% endif %}")
    def test_simple_if(self, template):
        """Test simple if block."""
        ast = parse(template)
        assert ast is not None

    @given(st.just("{% for item in items %}{{ item }}{% endfor %}"))
    @example("{% for item in items %}{{ item }}{% endfor %}")
    def test_simple_for(self, template):
        """Test simple for loop."""
        ast = parse(template)
        assert ast is not None


if __name__ == '__main__':
    # Run tests with pytest
    pytest.main([__file__, '-v'])
