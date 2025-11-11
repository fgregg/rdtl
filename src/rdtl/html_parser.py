"""
HTML parsing for RDTL templates.

Handles HTML elements, attributes, and related constructs.
Extracted from main Parser to improve modularity and maintainability.
"""

from rdtl import ast_nodes
from rdtl.lexer import TokenType



class HtmlParser:
    """Specialized parser for HTML elements and attributes.

    This parser handles:
    - HTML opening and closing tags
    - Void/self-closing elements
    - HTML attributes (static and dynamic)
    - DOCTYPE declarations
    - HTML comments
    - CDATA sections

    The HtmlParser works in conjunction with the main Parser,
    accessing its token stream and element parsing through delegation.
    """

    VOID_ELEMENTS = {
        "area",
        "base",
        "br",
        "col",
        "embed",
        "hr",
        "img",
        "input",
        "link",
        "meta",
        "param",
        "source",
        "track",
        "wbr",
    }

    def __init__(self, parser):
        """Initialize with reference to main parser.

        Args:
            parser: Main Parser instance for token access and element parsing.
        """
        self.parser = parser

    def parse_html_element(self) -> ast_nodes.HTMLElement | ast_nodes.VoidElement:
        """Parse HTML elements with automatic void element detection.

        This method handles all HTML element parsing, automatically detecting
        void/self-closing elements and treating them specially. Void elements
        (like <img>, <br>, <input>) don't have closing tags in HTML5.

        Void Element Detection:
            The parser maintains a VOID_ELEMENTS set of HTML5 void elements:
            area, base, br, col, embed, hr, img, input, link, meta, param,
            source, track, wbr.

            When a void element is detected, returns VoidElement immediately
            without expecting a closing tag. For all other elements, expects
            matching closing tags with name verification.

        Tag Name Matching:
            Closing tags must match opening tags exactly (case-insensitive):
            <div>...</div> ✓
            <div>...</DIV> ✓
            <div>...</span> ✗ ParseError

        Nesting:
            Supports arbitrary nesting of HTML elements and template tags:
            <div>
                {% if user %}
                    <p>{{ user.name }}</p>
                {% endif %}
            </div>

        Returns:
            VoidElement: For void elements (no closing tag expected).
            HTMLElement: For normal elements with children and closing tag.

        Raises:
            ParseError: If closing tag is missing or mismatched.

        Examples:
            <img src="photo.jpg"> → VoidElement('img', [Attribute('src', 'photo.jpg')])
            <div class="box">text</div> → HTMLElement('div', [...], [TextNode('text')])
            <p>Hello {{ name }}</p> → HTMLElement('p', [], [TextNode('Hello '), Variable(...)])
        """
        open_token = self.parser.expect(TokenType.HTML_OPEN_TAG)
        tag_name = open_token.value

        # Parse attributes
        attributes = self.parse_attributes()

        # Check if this is a void element (shouldn't have closing tag)
        if tag_name.lower() in self.VOID_ELEMENTS:
            return ast_nodes.VoidElement(tag_name=tag_name, attributes=attributes)

        # Parse children until we hit the closing tag
        children = []
        while not self.parser.match(TokenType.HTML_CLOSE_TAG, TokenType.EOF):
            child = self.parser.parse_element()
            if child:
                children.append(child)

            # Safety check for closing tag
            if self.parser.match(TokenType.HTML_CLOSE_TAG):
                break

        # Expect closing tag
        if not self.parser.match(TokenType.HTML_CLOSE_TAG):
            from rdtl.parser import ParseError

            raise ParseError(
                f"Expected closing tag for <{tag_name}> at line {self.parser.current().line}"
            )

        close_token = self.parser.expect(TokenType.HTML_CLOSE_TAG)

        # Verify tag names match
        if close_token.value != tag_name:
            from rdtl.parser import ParseError

            raise ParseError(
                f"Mismatched closing tag: expected </{tag_name}> but got </{close_token.value}> "
                f"at line {close_token.line}"
            )

        return ast_nodes.HTMLElement(
            tag_name=tag_name, attributes=attributes, children=children
        )

    def parse_void_element(self) -> ast_nodes.VoidElement:
        """Parse a self-closing/void element."""
        token = self.parser.expect(TokenType.HTML_SELF_CLOSE)
        tag_name = token.value
        attributes = self.parse_attributes()
        return ast_nodes.VoidElement(tag_name=tag_name, attributes=attributes)

    def parse_attributes(self) -> list[ast_nodes.Attribute]:
        """Parse HTML element attributes with support for dynamic attribute names.

        Attributes can have:
        - Static names: class, id, data-value
        - Dynamic names: {{ attr_name }} (RDTL extension)
        - Values: Quoted strings or None for boolean attributes
        - Boolean attributes: disabled, checked, readonly (no value)

        Dynamic Attribute Names:
            RDTL extends HTML to allow computed attribute names using
            Django template variables:
            <div {{ dynamic_attr }}="value">
            <button {{ "disabled" if not active else "" }}>

            These are marked with is_dynamic_name=True in the AST.

        Boolean Attributes:
            HTML5 boolean attributes (disabled, checked, etc.) can appear
            without values:
            <input disabled> → Attribute('disabled', value=None)
            <input disabled="disabled"> → Attribute('disabled', value='disabled')

        Attribute Value Parsing:
            Values are always strings after lexing. The lexer handles:
            - Double-quoted: class="foo"
            - Single-quoted: class='foo'
            - Unquoted: class=foo (lexer limitation, not standard HTML)

        Returns:
            List of Attribute nodes with name, optional value, and dynamic flag.

        Examples:
            class="container" → [Attribute('class', 'container', is_dynamic_name=False)]
            disabled → [Attribute('disabled', None, is_dynamic_name=False)]
            {{ attr }}="val" → [Attribute('{{ attr }}', 'val', is_dynamic_name=True)]
        """
        attributes = []

        while self.parser.match(TokenType.ATTR_NAME) or self.parser.match(
            TokenType.ATTR_NAME_DYNAMIC
        ):
            name_token = self.parser.advance()
            name = name_token.value
            is_dynamic = name_token.type == TokenType.ATTR_NAME_DYNAMIC

            # Check for attribute value
            value = None
            if self.parser.match(TokenType.ATTR_VALUE):
                value_token = self.parser.advance()
                value = value_token.value

            attributes.append(
                ast_nodes.Attribute(name=name, value=value, is_dynamic_name=is_dynamic)
            )

        return attributes

    def parse_doctype(self) -> ast_nodes.DocType:
        """Parse a DOCTYPE declaration."""
        token = self.parser.expect(TokenType.DOCTYPE)
        return ast_nodes.DocType(content=token.value)

    def parse_html_comment(self) -> ast_nodes.HTMLComment:
        """Parse an HTML comment."""
        token = self.parser.expect(TokenType.HTML_COMMENT)
        return ast_nodes.HTMLComment(content=token.value)

    def parse_cdata(self) -> ast_nodes.CDATA:
        """Parse a CDATA section."""
        token = self.parser.expect(TokenType.CDATA)
        return ast_nodes.CDATA(content=token.value)
