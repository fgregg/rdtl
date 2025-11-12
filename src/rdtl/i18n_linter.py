#!/usr/bin/env python3
"""
i18n Linter for RDTL templates.

Checks that all user-visible text is wrapped in translation tags ({% trans %} or {% blocktranslate %}).
"""

import re
from dataclasses import dataclass

from rdtl import ast_nodes
from rdtl.parser import parse
from rdtl.validator import validate_template


@dataclass
class I18nIssue:
    """Represents an i18n linting issue."""

    line: int | None
    column: int | None
    text: str
    message: str
    context: str  # e.g., "TextNode", "HTMLElement button content"

    def __str__(self) -> str:
        location = ""
        if self.line is not None:
            location = f"Line {self.line}"
            if self.column is not None:
                location += f", col {self.column}"
            location += ": "
        return f"{location}{self.message}: {self.text!r} in {self.context}"


class I18nLinter:
    """
    Linter that checks for user-visible text not wrapped in translation tags.

    User-visible text includes:
    - TextNode content (plain text between HTML tags)
    - Button text
    - Link text
    - Label text
    - Placeholder attributes
    - Title attributes
    - Alt text for images
    - ARIA labels

    Excluded from linting:
    - Text inside {% trans %} or {% blocktranslate %} tags
    - Text inside <script> and <style> tags
    - Whitespace-only text
    - Numeric-only text
    - Variable output ({{ ... }})
    - Template comments ({# ... #})
    - HTML comments (<!-- ... -->)
    """

    # HTML tags whose content is definitely user-visible
    USER_VISIBLE_TAGS = {
        "a",
        "button",
        "label",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "p",
        "li",
        "td",
        "th",
        "dt",
        "dd",
        "legend",
        "figcaption",
        "caption",
        "option",
        "span",
        "div",
        "strong",
        "em",
        "b",
        "i",
    }

    # HTML attributes that should be translated
    TRANSLATABLE_ATTRIBUTES = {
        "title",
        "placeholder",
        "alt",
        "aria-label",
        "aria-describedby",
        "aria-valuetext",
    }

    # Tags whose content should not be linted
    NON_CONTENT_TAGS = {"script", "style", "pre", "code"}

    def __init__(self):
        self.issues: list[I18nIssue] = []
        self.in_translation_context = False
        self.in_non_content_tag = False
        self.context_stack: list[str] = []
        self.template_content = ""
        self.template_lines: list[str] = []

    def lint(self, template: str) -> list[I18nIssue]:
        """
        Lint a template for i18n issues.

        Args:
            template: The template source code

        Returns:
            List of I18nIssue objects found
        """
        self.issues = []
        self.in_translation_context = False
        self.in_non_content_tag = False
        self.context_stack = []

        # Validate template first
        is_valid, errors = validate_template(template, strict_html=False)
        if not is_valid:
            # Return validation errors as issues
            for error in errors:
                self.issues.append(
                    I18nIssue(
                        line=None,
                        column=None,
                        text="",
                        message=f"Template validation failed: {error}",
                        context="Validator",
                    )
                )
            return self.issues

        try:
            ast = parse(template)
            self._visit(ast)
        except Exception as e:
            # If parsing fails, we can't lint
            self.issues.append(
                I18nIssue(
                    line=None,
                    column=None,
                    text="",
                    message=f"Failed to parse template: {e}",
                    context="Parser",
                )
            )

        return self.issues

    def _visit(self, node: ast_nodes.ASTNode):
        """Visit an AST node and check for i18n issues."""
        if isinstance(node, ast_nodes.Document):
            for child in node.children:
                self._visit(child)

        elif isinstance(node, ast_nodes.TextNode):
            self._check_text_node(node)

        elif isinstance(node, ast_nodes.HTMLElement):
            self._check_html_element(node)

        elif isinstance(node, ast_nodes.VoidElement):
            self._check_void_element(node)

        elif isinstance(node, ast_nodes.SingleTag):
            self._check_single_tag(node)

        elif isinstance(node, ast_nodes.GenericBlockTag):
            self._check_generic_block_tag(node)

        elif isinstance(node, ast_nodes.IfBlock):
            # Visit if branch
            for child in node.if_children:
                self._visit(child)
            # Visit elif branches
            for condition, children in node.elif_branches:
                for child in children:
                    self._visit(child)
            # Visit else branch
            if node.else_children:
                for child in node.else_children:
                    self._visit(child)

        elif isinstance(node, ast_nodes.ForBlock):
            for child in node.children:
                self._visit(child)

        elif isinstance(node, ast_nodes.BlockTag):
            for child in node.children:
                self._visit(child)

        # Comments, variables, and other nodes don't need checking
        # (variables are dynamic, comments aren't user-visible)

    def _check_text_node(self, node: ast_nodes.TextNode):
        """Check if a TextNode contains untranslated user-visible text."""
        if self.in_translation_context or self.in_non_content_tag:
            return

        text = node.content.strip()
        if not text:
            return

        # Skip if it's just whitespace, punctuation, or UI symbols
        # Includes: basic punctuation, arrows, bullets, math symbols, checkmarks, etc.
        ui_symbols_pattern = (
            r"^[\s\-\—\–\.\,\:\;\!\?\(\)\[\]\{\}\*"
            r"\←\→\↑\↓\«\»\‹\›\⇐\⇒\⟵\⟶"
            r"\×\✓\✗\✔\✘\•\◦\▪\▸\⋯\…"
            r"\+\−\÷\±"
            r"]*$"
        )
        if re.match(ui_symbols_pattern, text):
            return

        # Skip if it's purely numeric
        if re.match(r"^[\d\.\,\s\%\$\€\£\¥]+$", text):
            return

        # This is likely user-visible text that should be translated
        context = " > ".join(self.context_stack) if self.context_stack else "root"
        self.issues.append(
            I18nIssue(
                line=node.lineno,
                column=node.col_offset,
                text=text,
                message="User-visible text not wrapped in translation tag",
                context=context,
            )
        )

    def _check_html_element(self, node: ast_nodes.HTMLElement):
        """Check an HTML element and its children."""
        tag = node.tag_name.lower()

        # Check translatable attributes
        self._check_element_attributes(node.attributes, f"<{tag}>")

        # Track if we're in a non-content tag
        was_in_non_content = self.in_non_content_tag
        if tag in self.NON_CONTENT_TAGS:
            self.in_non_content_tag = True

        # Track context
        self.context_stack.append(f"<{tag}>")

        # Visit children
        for child in node.children:
            self._visit(child)

        self.context_stack.pop()
        self.in_non_content_tag = was_in_non_content

    def _check_void_element(self, node: ast_nodes.VoidElement):
        """Check void element attributes (e.g., <img alt="...">)."""
        tag = node.tag_name.lower()
        self._check_element_attributes(node.attributes, f"<{tag}>")

    def _check_element_attributes(
        self, attributes: list[ast_nodes.Attribute], context: str
    ):
        """Check if element attributes contain untranslated text."""
        if self.in_translation_context:
            return

        for attr in attributes:
            attr_name = attr.name.lower()
            if attr_name in self.TRANSLATABLE_ATTRIBUTES and attr.value:
                # Check if the value contains template syntax
                if "{{" in attr.value or "{%" in attr.value:
                    # It's dynamic, probably fine
                    continue

                # Static translatable attribute
                text = attr.value.strip()
                if text and not re.match(
                    r"^[\s\-\—\–\.\,\:\;\!\?\(\)\[\]\{\}]*$", text
                ):
                    self.issues.append(
                        I18nIssue(
                            line=None,
                            column=None,
                            text=text,
                            message=f"Translatable attribute '{attr_name}' not using translation tag",
                            context=context,
                        )
                    )

    def _check_single_tag(self, node: ast_nodes.SingleTag):
        """Check single tags - mark translation tags."""
        if node.tag_name in ("trans", "translate"):
            # This is a translation tag, everything inside is translated
            # But since it's a single tag, it doesn't have children to protect
            pass

    def _check_generic_block_tag(self, node: ast_nodes.GenericBlockTag):
        """Check generic block tags - mark translation blocks."""
        if node.tag_name in ("blocktranslate", "blocktrans"):
            # Everything inside this block is translated
            was_in_translation = self.in_translation_context
            self.in_translation_context = True

            for child in node.children:
                self._visit(child)

            self.in_translation_context = was_in_translation
        else:
            # Regular block tag, check children normally
            self.context_stack.append(f"{{% {node.tag_name} %}}")
            for child in node.children:
                self._visit(child)
            self.context_stack.pop()


def lint_template(template: str) -> list[I18nIssue]:
    """
    Convenience function to lint a template.

    Args:
        template: The template source code

    Returns:
        List of I18nIssue objects found
    """
    linter = I18nLinter()
    return linter.lint(template)
