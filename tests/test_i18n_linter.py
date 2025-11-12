#!/usr/bin/env python3
"""
Tests for the i18n linter.
"""


from rdtl.i18n_linter import lint_template


class TestBasicTextDetection:
    """Test detection of untranslated user-visible text."""

    def test_untranslated_button_text(self):
        """Button text without translation should be flagged."""
        template = """<button>Save</button>"""
        issues = lint_template(template)

        assert len(issues) == 1
        assert "Save" in issues[0].text
        assert "translation tag" in issues[0].message

    def test_translated_button_text(self):
        """Button text with {% trans %} should pass."""
        template = """<button>{% trans "Save" %}</button>"""
        issues = lint_template(template)

        assert len(issues) == 0

    def test_untranslated_paragraph(self):
        """Paragraph text without translation should be flagged."""
        template = """<p>Welcome to our website!</p>"""
        issues = lint_template(template)

        assert len(issues) == 1
        assert "Welcome to our website!" in issues[0].text

    def test_translated_paragraph_blocktranslate(self):
        """Paragraph text with {% blocktranslate %} should pass."""
        template = """<p>{% blocktranslate %}Welcome to our website!{% endblocktranslate %}</p>"""
        issues = lint_template(template)

        assert len(issues) == 0

    def test_translated_paragraph_blocktrans(self):
        """Paragraph text with {% blocktrans %} should pass."""
        template = """<p>{% blocktrans %}Welcome!{% endblocktrans %}</p>"""
        issues = lint_template(template)

        assert len(issues) == 0

    def test_untranslated_heading(self):
        """Heading text without translation should be flagged."""
        template = """<h1>Page Title</h1>"""
        issues = lint_template(template)

        assert len(issues) == 1
        assert "Page Title" in issues[0].text


class TestAttributeDetection:
    """Test detection of untranslated attributes."""

    def test_untranslated_placeholder(self):
        """Placeholder attribute without translation should be flagged."""
        template = """<input type="text" placeholder="Enter your name" />"""
        issues = lint_template(template)

        assert len(issues) == 1
        assert "Enter your name" in issues[0].text
        assert "placeholder" in issues[0].message

    def test_translated_placeholder(self):
        """Placeholder with template syntax should pass."""
        template = (
            """<input type="text" placeholder="{% trans 'Enter your name' %}" />"""
        )
        issues = lint_template(template)

        assert len(issues) == 0

    def test_dynamic_placeholder(self):
        """Placeholder with variable should pass."""
        template = """<input type="text" placeholder="{{ placeholder_text }}" />"""
        issues = lint_template(template)

        assert len(issues) == 0

    def test_untranslated_title_attribute(self):
        """Title attribute without translation should be flagged."""
        template = """<a href="#" title="Click here">Link</a>"""
        issues = lint_template(template)

        # Should flag both the title attribute and the link text
        assert len(issues) == 2
        issue_texts = [issue.text for issue in issues]
        assert "Click here" in issue_texts
        assert "Link" in issue_texts

    def test_untranslated_alt_text(self):
        """Alt text without translation should be flagged."""
        template = """<img src="photo.jpg" alt="A beautiful sunset" />"""
        issues = lint_template(template)

        assert len(issues) == 1
        assert "A beautiful sunset" in issues[0].text
        assert "alt" in issues[0].message

    def test_untranslated_aria_label(self):
        """ARIA label without translation should be flagged."""
        template = """<button aria-label="Close dialog">X</button>"""
        issues = lint_template(template)

        # Should flag both aria-label and button text
        assert len(issues) == 2


class TestNonContentTags:
    """Test that script/style/code content is not flagged."""

    def test_script_content_ignored(self):
        """Script tag content should not be flagged."""
        template = """<script>
const message = "Hello world";
console.log(message);
</script>"""
        issues = lint_template(template)

        assert len(issues) == 0

    def test_style_content_ignored(self):
        """Style tag content should not be flagged."""
        template = """<style>
.button {
    content: "Click me";
}
</style>"""
        issues = lint_template(template)

        assert len(issues) == 0

    def test_pre_content_ignored(self):
        """Pre tag content should not be flagged (often code samples)."""
        template = """<pre>
Hello world example
This is code
</pre>"""
        issues = lint_template(template)

        assert len(issues) == 0

    def test_code_content_ignored(self):
        """Code tag content should not be flagged."""
        template = """<code>print("Hello world")</code>"""
        issues = lint_template(template)

        assert len(issues) == 0


class TestDynamicContent:
    """Test that dynamic content (variables) is not flagged."""

    def test_variable_output(self):
        """Variable output should not be flagged."""
        template = """<p>{{ user.name }}</p>"""
        issues = lint_template(template)

        assert len(issues) == 0

    def test_filtered_variable(self):
        """Filtered variable output should not be flagged."""
        template = """<p>{{ text|upper }}</p>"""
        issues = lint_template(template)

        assert len(issues) == 0

    def test_mixed_static_and_dynamic(self):
        """Static text mixed with variables should be flagged."""
        template = """<p>Hello, {{ user.name }}!</p>"""
        issues = lint_template(template)

        # "Hello," should be flagged but variable should not
        assert len(issues) == 1
        assert "Hello," in issues[0].text


class TestWhitespaceHandling:
    """Test that whitespace-only text is not flagged."""

    def test_whitespace_only(self):
        """Whitespace-only text should not be flagged."""
        template = """<div>
    <span>{{ value }}</span>
</div>"""
        issues = lint_template(template)

        assert len(issues) == 0

    def test_empty_elements(self):
        """Empty elements should not be flagged."""
        template = """<div></div>"""
        issues = lint_template(template)

        assert len(issues) == 0

    def test_punctuation_only(self):
        """Punctuation-only text should not be flagged."""
        template = """<span>-</span>"""
        issues = lint_template(template)

        assert len(issues) == 0


class TestUISymbols:
    """Test that UI symbols (arrows, bullets, etc.) are not flagged."""

    def test_pagination_arrows_double(self):
        """Double angle quote pagination arrows should not be flagged."""
        template = """<a>«</a> <a>»</a>"""
        issues = lint_template(template)

        assert len(issues) == 0

    def test_pagination_arrows_single(self):
        """Single angle quote pagination arrows should not be flagged."""
        template = """<a>‹</a> <a>›</a>"""
        issues = lint_template(template)

        assert len(issues) == 0

    def test_navigation_arrows(self):
        """Navigation arrows should not be flagged."""
        template = """<a>←</a> <a>→</a> <a>↑</a> <a>↓</a>"""
        issues = lint_template(template)

        assert len(issues) == 0

    def test_close_button_symbol(self):
        """Close button × symbol should not be flagged."""
        template = """<button>×</button>"""
        issues = lint_template(template)

        assert len(issues) == 0

    def test_bullet_points(self):
        """Bullet point symbols should not be flagged."""
        template = """<span>•</span> <span>◦</span>"""
        issues = lint_template(template)

        assert len(issues) == 0

    def test_checkmarks(self):
        """Checkmark symbols should not be flagged."""
        template = """<span>✓</span> <span>✔</span> <span>✗</span> <span>✘</span>"""
        issues = lint_template(template)

        assert len(issues) == 0

    def test_math_operators(self):
        """Mathematical operator symbols should not be flagged."""
        template = """<span>+</span> <span>−</span> <span>÷</span>"""
        issues = lint_template(template)

        assert len(issues) == 0

    def test_ellipsis(self):
        """Ellipsis symbols should not be flagged."""
        template = """<span>…</span> <span>⋯</span>"""
        issues = lint_template(template)

        assert len(issues) == 0

    def test_required_field_asterisk(self):
        """Required field asterisk should not be flagged."""
        template = """<label>Name <span>*</span></label>"""
        issues = lint_template(template)

        # "Name" should be flagged, but "*" should not
        assert len(issues) == 1
        assert issues[0].text == "Name"

    def test_mixed_symbols_and_text(self):
        """Text with symbols should flag only the text."""
        template = """<a>← Back</a>"""
        issues = lint_template(template)

        # "← Back" contains text, should be flagged
        assert len(issues) == 1
        assert "Back" in issues[0].text


class TestNumericContent:
    """Test that numeric content is not flagged."""

    def test_numeric_text(self):
        """Numeric text should not be flagged."""
        template = """<span>123</span>"""
        issues = lint_template(template)

        assert len(issues) == 0

    def test_percentage(self):
        """Percentage values should not be flagged."""
        template = """<span>75%</span>"""
        issues = lint_template(template)

        assert len(issues) == 0

    def test_currency(self):
        """Currency values should not be flagged."""
        template = """<span>$99.99</span>"""
        issues = lint_template(template)

        assert len(issues) == 0


class TestComplexTemplates:
    """Test complex template structures."""

    def test_nested_if_blocks(self):
        """If blocks with content should be checked."""
        template = """{% if user %}
    <p>Welcome back!</p>
{% else %}
    <p>Please log in</p>
{% endif %}"""
        issues = lint_template(template)

        # Both messages should be flagged
        assert len(issues) == 2
        issue_texts = [issue.text for issue in issues]
        assert "Welcome back!" in issue_texts
        assert "Please log in" in issue_texts

    def test_for_loop_with_content(self):
        """For loops with static content should be checked."""
        template = """{% for item in items %}
    <li>Item: {{ item }}</li>
{% endfor %}"""
        issues = lint_template(template)

        # "Item:" should be flagged
        assert len(issues) == 1
        assert "Item:" in issues[0].text

    def test_block_tag_with_content(self):
        """Block tags with content should be checked."""
        template = """{% block content %}
    <h1>Default Title</h1>
{% endblock %}"""
        issues = lint_template(template)

        assert len(issues) == 1
        assert "Default Title" in issues[0].text


class TestContextReporting:
    """Test that context is properly reported in issues."""

    def test_nested_context(self):
        """Context should show nesting."""
        template = """<div><p><span>Text</span></p></div>"""
        issues = lint_template(template)

        assert len(issues) == 1
        assert "<div>" in issues[0].context
        assert "<p>" in issues[0].context
        assert "<span>" in issues[0].context

    def test_button_context(self):
        """Button context should be clear."""
        template = """<button>Click</button>"""
        issues = lint_template(template)

        assert len(issues) == 1
        assert "<button>" in issues[0].context


class TestEdgeCases:
    """Test edge cases and special scenarios."""

    def test_empty_template(self):
        """Empty template should not raise errors."""
        template = ""
        issues = lint_template(template)

        assert len(issues) == 0

    def test_invalid_template_reports_validation_error(self):
        """Invalid templates should report validation errors, not hang."""
        template = """<div>{% if x %}</div>{% endif %}"""
        issues = lint_template(template)

        # Should get validation error, not hang
        assert len(issues) > 0
        assert any("validation" in issue.message.lower() for issue in issues)

    def test_comments_not_flagged(self):
        """Template comments should not be flagged."""
        template = """{# This is a comment with text #}"""
        issues = lint_template(template)

        assert len(issues) == 0

    def test_html_comments_not_flagged(self):
        """HTML comments should not be flagged."""
        template = """<!-- This is a comment -->"""
        issues = lint_template(template)

        assert len(issues) == 0

    def test_multiple_issues_in_one_file(self):
        """Multiple issues should all be reported."""
        template = """<div>
    <h1>Title</h1>
    <p>Paragraph</p>
    <button>Button</button>
</div>"""
        issues = lint_template(template)

        assert len(issues) == 3
        issue_texts = [issue.text for issue in issues]
        assert "Title" in issue_texts
        assert "Paragraph" in issue_texts
        assert "Button" in issue_texts
