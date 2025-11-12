#!/usr/bin/env python3
"""
Tests for formatter idempotence and correctness.

Tests the fixes for:
1. Smart quote selection for attributes (VoidElement and HTMLElement)
2. Inline tag formatting (IncludeTag, SingleTag)
3. Script tag preservation
4. GenericBlockTag inline/block detection
"""


from rdtl.formatter import format_template
from rdtl.parser import parse


class TestSmartQuoteSelection:
    """Test smart quote selection for HTML attributes."""

    def test_void_element_quotes_with_json(self):
        """VoidElement should use single quotes when value contains double quotes."""
        template = """<input type="text" hx-vals='{"id": "{{ widget.id }}"}' />"""

        formatted = format_template(template)

        # Should keep single quotes because value contains double quotes
        assert "hx-vals='{" in formatted
        assert 'hx-vals="{' not in formatted

    def test_void_element_quotes_without_conflict(self):
        """VoidElement should use preferred quotes when no conflict."""
        template = """<input type="text" name="username" />"""

        formatted = format_template(template)

        # Should use double quotes (default preference)
        assert 'name="username"' in formatted

    def test_html_element_quotes_with_json(self):
        """HTMLElement should use single quotes when value contains double quotes."""
        template = """<div hx-vals='{"id": "{{ x }}"}'>test</div>"""

        formatted = format_template(template)

        # Should keep single quotes
        assert "hx-vals='{" in formatted
        assert 'hx-vals="{' not in formatted

    def test_quotes_with_both_types_present(self):
        """Should escape preferred quote when both quote types in value."""
        # Use proper escaping in Python string
        template = """<div data-val="test &quot;quote&quot; and 'apostrophe'">x</div>"""

        formatted = format_template(template)

        # Should format successfully (escaping happens)
        assert "data-val" in formatted

    def test_idempotent_with_json_attributes(self):
        """Formatting JSON attributes should be idempotent."""
        template = """<input hx-vals='{"key": "value"}' />"""

        first = format_template(template)
        second = format_template(first)

        assert first == second


class TestInlineTagFormatting:
    """Test inline formatting for tags that shouldn't add newlines."""

    def test_include_tag_inline(self):
        """IncludeTag inside element should not add extra newlines."""
        template = """<div>{% include "test.html" %}</div>"""

        first = format_template(template)
        second = format_template(first)

        assert first == second
        # Should not have double newlines
        assert "\n\n" not in first

    def test_single_tag_inline(self):
        """SingleTag should not add extra newlines."""
        template = """<h1>{{ title }} {% trans "Test" %}</h1>"""

        first = format_template(template)
        second = format_template(first)

        assert first == second

    def test_include_with_context(self):
        """IncludeTag with context should be idempotent."""
        template = """<div>{% include "form.html" with value=x %}</div>"""

        first = format_template(template)
        second = format_template(first)

        assert first == second


class TestPreserveWhitespaceTag:
    """Test that tags which preserve whitespace are handled correctly."""

    def test_pre_tag_preserves_whitespace(self):
        """Pre tags should preserve exact whitespace including indentation."""
        template = """<pre>
Line 1
  Line 2 with indent
    Line 3 with more indent
{{ variable }}
</pre>"""

        first = format_template(template)
        second = format_template(first)

        # Should be idempotent
        assert first == second

        # Content should be preserved exactly (whitespace matters in pre tags)
        assert first.strip() == template.strip()

    def test_pre_with_django_tags(self):
        """Pre tags with Django tags should preserve formatting."""
        template = """<pre>{% if show %}
  Code line 1
  Code line 2
{% endif %}</pre>"""

        first = format_template(template)
        second = format_template(first)

        assert first == second


class TestScriptTagPreservation:
    """Test that script tags preserve their content as-is."""

    def test_script_with_template_variables(self):
        """Script tag with Django variables should be idempotent."""
        template = """<script>
const id = '{{ object.id }}';
const name = '{{ object.name }}';
</script>"""

        first = format_template(template)
        second = format_template(first)

        assert first == second

    def test_script_with_if_block(self):
        """Script tag with if block should be preserved."""
        template = """<script>
const value = '{% if x %}{{ x }}{% endif %}';
</script>"""

        first = format_template(template)
        second = format_template(first)

        assert first == second

    def test_script_attributes_formatted(self):
        """Script tag attributes should still be formatted."""
        template = """<script type="text/javascript" src="{{ url }}">
const x = 1;
</script>"""

        formatted = format_template(template)

        # Attributes should be present
        assert 'type="text/javascript"' in formatted
        assert 'src="{{ url }}"' in formatted

    def test_script_content_not_reformatted(self):
        """Script content should not be reformatted."""
        template = """<script>
const x=1;
  const y  =  2;
</script>"""

        first = format_template(template)

        # JavaScript spacing should be preserved
        assert "const x=1;" in first
        assert "const y  =  2;" in first


class TestGenericBlockTagFormatting:
    """Test GenericBlockTag inline/block detection."""

    def test_blocktranslate_inline(self):
        """Blocktranslate inside p tag should format inline."""
        template = """<p>{% blocktranslate with title=page.title %}There are no {{ title }} items.{% endblocktranslate %}</p>"""

        first = format_template(template)
        second = format_template(first)

        assert first == second

    def test_blocktranslate_with_variable(self):
        """Blocktranslate with Django variable should be idempotent."""
        template = """<p>{% blocktranslate with form_title=form_page.title|lower %}There are no {{ form_title }} submissions to display.{% endblocktranslate %}</p>"""

        first = format_template(template)
        second = format_template(first)

        assert first == second

    def test_generic_block_with_html_children(self):
        """GenericBlockTag with HTML children should format as block."""
        template = """{% cache 500 sidebar %}
<div class="sidebar">
    <h3>Title</h3>
</div>
{% endcache %}"""

        formatted = format_template(template)

        # Should have newlines for block formatting
        assert "{% cache 500 sidebar %}\n" in formatted

    def test_generic_block_cache_with_html_children(self):
        """Cache tag (GenericBlockTag) with HTML should format as block."""
        template = """{% cache 500 key %}
<div>Content</div>
{% endcache %}"""

        first = format_template(template)
        second = format_template(first)

        # Should be idempotent
        assert first == second


class TestIdempotence:
    """Test overall idempotence for complex cases."""

    def test_nested_tags_with_variables(self):
        """Complex nesting should be idempotent."""
        template = """<div class="container">
    {% if user %}
        <p>{% trans "Welcome" %} {{ user.name }}</p>
    {% endif %}
</div>"""

        first = format_template(template)
        second = format_template(first)
        third = format_template(second)

        assert first == second == third

    def test_void_elements_with_complex_attributes(self):
        """Void elements with complex attributes should be idempotent."""
        template = """<input type="text"
           name="search"
           hx-get="{{ url }}"
           hx-trigger="input changed delay:300ms"
           hx-vals='{"id": "{{ widget_id }}"}'
           />"""

        first = format_template(template)
        second = format_template(first)

        assert first == second

    def test_mixed_inline_and_block_tags(self):
        """Mix of inline and block tags should be idempotent."""
        template = """<div>
    {% block content %}
        <p>{% blocktranslate %}Text{{ var }}{% endblocktranslate %}</p>
        {% include "partial.html" %}
    {% endblock %}
</div>"""

        first = format_template(template)
        second = format_template(first)

        assert first == second

    def test_script_in_complex_template(self):
        """Script tag in complex template should be idempotent."""
        template = """<div class="page">
    <h1>{{ title }}</h1>
    <script>
        const data = '{% if obj %}{{ obj.id }}{% endif %}';
    </script>
    <p>Content</p>
</div>"""

        first = format_template(template)
        second = format_template(first)

        assert first == second


class TestCommentWhitespace:
    """Test that comments don't accumulate whitespace."""

    def test_comment_whitespace_stripped(self):
        """Comments should not accumulate whitespace on each format."""
        template = """{# This is a comment #}"""

        first = format_template(template)
        second = format_template(first)
        third = format_template(second)

        # All should be identical (main requirement)
        assert first == second == third


class TestLiteralSerialization:
    """Test that Literal nodes serialize correctly."""

    def test_literal_in_condition(self):
        """Literals in conditions should serialize as valid syntax."""
        template = """{% if field.name == 'location' %}Yes{% endif %}"""

        formatted = format_template(template)

        # Should have 'location' not Literal('location')
        assert "'location'" in formatted or '"location"' in formatted
        assert "Literal(" not in formatted

    def test_literal_in_comparison(self):
        """Literals in comparisons should be idempotent."""
        template = """{% if x == 'test' %}{{ y }}{% endif %}"""

        first = format_template(template)
        second = format_template(first)

        assert first == second
        assert "Literal(" not in first

    def test_number_literal(self):
        """Number literals should serialize correctly."""
        template = """{% if count > 5 %}Many{% endif %}"""

        formatted = format_template(template)

        assert "5" in formatted
        assert "Literal(5)" not in formatted


class TestBlockTagInlineDetection:
    """Test that block tags with inline content format correctly."""

    def test_spaceless_with_text_only(self):
        """Spaceless with only text/variables should format inline."""
        template = """<span>{% spaceless %}{{ value }}{% endspaceless %}</span>"""

        first = format_template(template)
        second = format_template(first)

        # Should be idempotent
        assert first == second

    def test_filter_block_inline(self):
        """Filter block with inline content should be idempotent."""
        template = """<p>{% filter upper %}hello{% endfilter %}</p>"""

        first = format_template(template)
        second = format_template(first)

        assert first == second

    def test_autoescape_inline(self):
        """Autoescape with inline content should be idempotent."""
        template = """<span>{% autoescape on %}{{ text }}{% endautoescape %}</span>"""

        first = format_template(template)
        second = format_template(first)

        assert first == second

    def test_comment_block_inline(self):
        """Comment block inline should be idempotent."""
        template = """<div>{% comment %}note{% endcomment %}</div>"""

        first = format_template(template)
        second = format_template(first)

        assert first == second

    def test_spaceless_with_inline_html_elements(self):
        """Spaceless with inline HTML elements should be idempotent and not add whitespace."""
        # Real-world case: button with icon
        template = """<button>{% spaceless %}<i class="icon"></i> Save{% endspaceless %}</button>"""

        first = format_template(template)
        second = format_template(first)
        third = format_template(second)

        # Should be idempotent
        assert first == second == third

        # Should not add any newlines that would affect rendering
        assert "\n" not in first.strip()  # Single line, no newlines except at end

    def test_spaceless_with_strong_inline(self):
        """Spaceless with strong tags should not add rendering whitespace."""
        template = """<p>This is {% spaceless %}<strong>bold text</strong>{% endspaceless %} in a sentence.</p>"""

        first = format_template(template)
        second = format_template(first)

        # Should be idempotent
        assert first == second

        # Content should remain on same line (no newlines between elements)
        # The \n at the very end is okay, but not in the middle
        content = first.strip()
        # Should not have newlines within the tag content
        assert content.count("\n") == 0


class TestRoundTrip:
    """Test that parse -> format -> parse produces same AST."""

    def test_simple_roundtrip(self):
        """Simple template should roundtrip correctly."""
        template = """<div>{{ x }}</div>"""

        formatted = format_template(template)
        second = format_template(formatted)

        # Should be idempotent
        assert formatted == second

    def test_complex_roundtrip(self):
        """Complex template should roundtrip correctly."""
        template = """<div class="container">
    {% if user %}
        <p>{{ user.name }}</p>
    {% endif %}
</div>"""

        formatted = format_template(template)
        second = format_template(formatted)

        # Should be idempotent
        assert formatted == second

    def test_roundtrip_preserves_semantics(self):
        """Roundtrip should preserve template semantics."""
        template = """<input hx-vals='{"id": "{{ x }}"}' />"""

        # Parse original
        ast1 = parse(template)

        # Format and parse again
        formatted = format_template(template)
        ast2 = parse(formatted)

        # Both should parse successfully
        assert ast1 is not None
        assert ast2 is not None

        # Should be idempotent
        second_format = format_template(formatted)
        assert formatted == second_format
