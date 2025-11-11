"""
Tests for custom block tag auto-discovery feature.

Tests that custom block tags are automatically discovered and parsed
while maintaining CFG properties.
"""

import unittest
from rdtl.validator import validate_template
from rdtl.parser import parse
from rdtl.formatter import format_template
from rdtl.ast_nodes import GenericBlockTag


class TestCustomBlockTags(unittest.TestCase):
    """Test auto-discovery of custom block tags."""

    def test_simple_custom_block(self):
        """Test a simple custom block tag."""
        template = """
        {% myblock %}
            <p>Content</p>
        {% endmyblock %}
        """
        is_valid, errors = validate_template(template)
        self.assertTrue(is_valid, f"Should be valid. Errors: {errors}")

        ast = parse(template)
        self.assertIsNotNone(ast)

    def test_custom_block_with_args(self):
        """Test custom block with arguments."""
        template = """
        {% myblock arg1 arg2 key="value" %}
            <p>Content</p>
        {% endmyblock %}
        """
        is_valid, errors = validate_template(template)
        self.assertTrue(is_valid, f"Should be valid. Errors: {errors}")

        ast = parse(template)
        # Find the GenericBlockTag
        for child in ast.children:
            if isinstance(child, GenericBlockTag):
                self.assertEqual(child.tag_name, 'myblock')
                self.assertIn('arg1', child.raw_args)
                break
        else:
            self.fail("GenericBlockTag not found in AST")

    def test_nested_custom_blocks(self):
        """Test nested custom block tags."""
        template = """
        {% outer %}
            {% inner %}
                <p>Nested</p>
            {% endinner %}
        {% endouter %}
        """
        is_valid, errors = validate_template(template)
        self.assertTrue(is_valid, f"Should be valid. Errors: {errors}")

        ast = parse(template)
        self.assertIsNotNone(ast)

    def test_mixed_builtin_and_custom(self):
        """Test mix of built-in and custom block tags."""
        template = """
        {% if condition %}
            {% myblock %}
                <p>Text</p>
            {% endmyblock %}
        {% endif %}
        """
        is_valid, errors = validate_template(template)
        self.assertTrue(is_valid, f"Should be valid. Errors: {errors}")

        ast = parse(template)
        self.assertIsNotNone(ast)

    def test_custom_block_in_html(self):
        """Test custom block inside HTML structure."""
        template = """
        <div>
            {% customblock %}
                <p>Content</p>
            {% endcustomblock %}
        </div>
        """
        is_valid, errors = validate_template(template)
        self.assertTrue(is_valid, f"Should be valid. Errors: {errors}")

    def test_multiple_different_custom_blocks(self):
        """Test multiple different custom block types."""
        template = """
        {% block1 %}
            Content 1
        {% endblock1 %}
        {% block2 %}
            Content 2
        {% endblock2 %}
        """
        is_valid, errors = validate_template(template)
        self.assertTrue(is_valid, f"Should be valid. Errors: {errors}")

    def test_tag_without_end_is_simple_tag(self):
        """Test that tags without matching end tags are treated as simple tags."""
        template = """
        {% myblock %}
            <p>Content</p>
        {# No endmyblock - so myblock is treated as a simple tag #}
        """
        is_valid, errors = validate_template(template)
        # Should pass because myblock is not in discovered blocks
        # (no {% endmyblock %} found), so it's treated as a simple tag
        self.assertTrue(is_valid, f"Should accept as simple tag: {errors}")

    def test_mismatched_custom_block_fails(self):
        """Test that mismatched custom block tags are rejected."""
        template = """
        {% myblock %}
            <p>Content</p>
        {% endotherblock %}
        """
        is_valid, errors = validate_template(template)
        # myblock is not discovered (no endmyblock), treated as single tag
        # But endotherblock has no matching otherblock
        self.assertFalse(is_valid, "Should reject mismatched tags")

    def test_formatter_preserves_custom_blocks(self):
        """Test that formatter preserves custom block tags."""
        template = """{% myblock arg %}
    <p>Content</p>
{% endmyblock %}"""

        formatted = format_template(template)
        self.assertIn('{% myblock', formatted)
        self.assertIn('{% endmyblock %}', formatted)
        self.assertIn('<p>Content</p>', formatted)

    def test_custom_block_proper_nesting(self):
        """Test that custom blocks must be properly nested."""
        template = """
        <div>
            {% myblock %}
        </div>
        {% endmyblock %}
        """
        is_valid, errors = validate_template(template)
        # Should fail: template block closes after HTML
        self.assertFalse(is_valid, "Should reject improper nesting")
        # Check for proper nesting error (either "closes before" or "Expected")
        self.assertTrue(any('closes before' in str(e) or 'Expected' in str(e) for e in errors))

    def test_custom_block_with_for_loop(self):
        """Test custom block containing built-in blocks."""
        template = """
        {% customwrapper %}
            {% for item in items %}
                <li>{{ item }}</li>
            {% endfor %}
        {% endcustomwrapper %}
        """
        is_valid, errors = validate_template(template)
        self.assertTrue(is_valid, f"Should be valid. Errors: {errors}")

    def test_empty_custom_block(self):
        """Test empty custom block."""
        template = """
        {% myblock %}
        {% endmyblock %}
        """
        is_valid, errors = validate_template(template)
        self.assertTrue(is_valid, f"Should be valid. Errors: {errors}")

    def test_case_insensitive_end_tag(self):
        """Test that end tags are case-insensitive."""
        template = """
        {% MyBlock %}
            Content
        {% endmyblock %}
        """
        is_valid, errors = validate_template(template)
        # This should work - case insensitive matching
        self.assertTrue(is_valid, f"Should be valid (case insensitive). Errors: {errors}")


class TestDiscoveryMechanism(unittest.TestCase):
    """Test the block tag discovery mechanism itself."""

    def test_discovery_finds_end_tags(self):
        """Test that discovery correctly identifies block tags."""
        from validator import RDTLValidator

        template = """
        {% myblock %}...{% endmyblock %}
        {% another %}...{% endanother %}
        """

        validator = RDTLValidator(template)
        discovered = validator.discovered_block_tags

        self.assertIn('myblock', discovered)
        self.assertIn('another', discovered)

    def test_discovery_merges_with_known_tags(self):
        """Test that discovered tags merge with built-in tags."""
        from validator import RDTLValidator

        template = """
        {% if x %}...{% endif %}
        {% customblock %}...{% endcustomblock %}
        """

        validator = RDTLValidator(template)

        # Should have both built-in and discovered
        self.assertIn('if', validator.ALLOWED_BLOCKS)
        self.assertIn('customblock', validator.ALLOWED_BLOCKS)

    def test_no_duplicate_discovery(self):
        """Test that multiple end tags don't cause issues."""
        template = """
        {% myblock %}...{% endmyblock %}
        {% myblock %}...{% endmyblock %}
        """

        is_valid, errors = validate_template(template)
        self.assertTrue(is_valid, f"Should be valid. Errors: {errors}")


if __name__ == '__main__':
    unittest.main()
