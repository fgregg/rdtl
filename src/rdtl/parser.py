"""
Recursive descent parser for RDTL.

Converts token stream into an Abstract Syntax Tree (AST).
"""

import re

from rdtl import ast_nodes
from rdtl.lexer import Lexer, Token, TokenType


class ParseError(Exception):
    """Raised when parsing fails."""

    pass


class Parser:
    """
    Recursive descent parser for RDTL.

    Follows the grammar defined in grammar.ebnf.
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

    # Known Django block tags
    KNOWN_BLOCK_TAGS = {
        "if",
        "for",
        "block",
        "with",
        "autoescape",
        "filter",
        "spaceless",
        "verbatim",
    }

    def __init__(self, tokens: list[Token], discovered_blocks: set = None):
        self.tokens = tokens
        self.pos = 0

        # Merge known and discovered block tags
        self.block_tags = self.KNOWN_BLOCK_TAGS.copy()
        if discovered_blocks:
            self.block_tags.update(discovered_blocks)

    def current(self) -> Token:
        """Get current token."""
        if self.pos >= len(self.tokens):
            return self.tokens[-1]  # Return EOF
        return self.tokens[self.pos]

    def peek(self, offset: int = 1) -> Token:
        """Look ahead at token."""
        pos = self.pos + offset
        if pos >= len(self.tokens):
            return self.tokens[-1]  # Return EOF
        return self.tokens[pos]

    def advance(self) -> Token:
        """Consume and return current token."""
        token = self.current()
        if token.type != TokenType.EOF:
            self.pos += 1
        return token

    def expect(self, token_type: TokenType) -> Token:
        """Expect a specific token type and consume it."""
        token = self.current()
        if token.type != token_type:
            raise ParseError(
                f"Expected {token_type.name} but got {token.type.name} "
                f"at line {token.line}, column {token.column}"
            )
        return self.advance()

    def match(self, *token_types: TokenType) -> bool:
        """Check if current token matches any of the given types."""
        return self.current().type in token_types

    def is_identifier_like(self) -> bool:
        """Check if current token can be used as an identifier.

        In attribute lookups, Django allows keywords to be used as attribute names.
        For example: {{ obj.as }}, {{ obj.if }}, {{ obj.for }} are all valid.
        """
        token_type = self.current().type
        # IDENTIFIER is obviously allowed
        if token_type == TokenType.IDENTIFIER:
            return True
        # NUMBER is allowed for numeric indices
        if token_type == TokenType.NUMBER:
            return True
        # Keywords can be used as attribute names
        keyword_types = {
            TokenType.IF,
            TokenType.ELIF,
            TokenType.ELSE,
            TokenType.ENDIF,
            TokenType.FOR,
            TokenType.IN,
            TokenType.EMPTY,
            TokenType.ENDFOR,
            TokenType.BLOCK,
            TokenType.ENDBLOCK,
            TokenType.WITH,
            TokenType.ENDWITH,
            TokenType.INCLUDE,
            TokenType.EXTENDS,
            TokenType.LOAD,
            TokenType.CSRF_TOKEN,
            TokenType.AUTOESCAPE,
            TokenType.ENDAUTOESCAPE,
            TokenType.COMMENT,
            TokenType.ENDCOMMENT,
            TokenType.IFCHANGED,
            TokenType.ENDIFCHANGED,
            TokenType.FILTER,
            TokenType.ENDFILTER,
            TokenType.SPACELESS,
            TokenType.ENDSPACELESS,
            TokenType.VERBATIM,
            TokenType.ENDVERBATIM,
            TokenType.CYCLE,
            TokenType.RESETCYCLE,
            TokenType.DEBUG,
            TokenType.LOREM,
            TokenType.REGROUP,
            TokenType.QUERYSTRING,
            TokenType.URL,
            TokenType.STATIC,
            TokenType.AS,
            TokenType.BY,
        }
        return token_type in keyword_types

    # ========================================================================
    # Main parsing methods
    # ========================================================================

    def parse(self) -> ast_nodes.Document:
        """Parse the entire template into a Document."""
        children = []

        while not self.match(TokenType.EOF):
            child = self.parse_element()
            if child:
                children.append(child)

        return ast_nodes.Document(children=children)

    def parse_element(self) -> ast_nodes.ASTNode | None:
        """Parse a single element (HTML, template, text, etc.)."""
        token = self.current()

        # DOCTYPE declaration
        if token.type == TokenType.DOCTYPE:
            return self.parse_doctype()

        # HTML comment
        if token.type == TokenType.HTML_COMMENT:
            return self.parse_html_comment()

        # CDATA section
        if token.type == TokenType.CDATA:
            return self.parse_cdata()

        # HTML element
        if token.type == TokenType.HTML_OPEN_TAG:
            return self.parse_html_element()

        # Self-closing HTML element
        if token.type == TokenType.HTML_SELF_CLOSE:
            return self.parse_void_element()

        # Template variable
        if token.type == TokenType.TEMPLATE_VAR_START:
            return self.parse_variable()

        # Template tag
        if token.type == TokenType.TEMPLATE_TAG_START:
            return self.parse_template_tag()

        # Comment
        if token.type == TokenType.TEMPLATE_COMMENT_START:
            return self.parse_comment()

        # Text content
        if token.type == TokenType.TEXT:
            text = self.advance().value
            # Skip empty whitespace-only text nodes
            if text.strip():
                return ast_nodes.TextNode(content=text)
            # But keep them if they have content
            if text:
                return ast_nodes.TextNode(content=text)
            return None

        # Ignore closing tags here - they're handled by parse_html_element
        if token.type == TokenType.HTML_CLOSE_TAG:
            return None

        raise ParseError(
            f"Unexpected token {token.type.name} at line {token.line}, column {token.column}"
        )

    # ========================================================================
    # HTML parsing
    # ========================================================================

    def parse_html_element(self) -> ast_nodes.HTMLElement:
        """Parse an HTML element with opening and closing tags."""
        open_token = self.expect(TokenType.HTML_OPEN_TAG)
        tag_name = open_token.value

        # Parse attributes
        attributes = self.parse_attributes()

        # Check if this is a void element (shouldn't have closing tag)
        if tag_name.lower() in self.VOID_ELEMENTS:
            return ast_nodes.VoidElement(tag_name=tag_name, attributes=attributes)

        # Parse children until we hit the closing tag
        children = []
        while not self.match(TokenType.HTML_CLOSE_TAG, TokenType.EOF):
            child = self.parse_element()
            if child:
                children.append(child)

            # Safety check for closing tag
            if self.match(TokenType.HTML_CLOSE_TAG):
                break

        # Expect closing tag
        if not self.match(TokenType.HTML_CLOSE_TAG):
            raise ParseError(
                f"Expected closing tag for <{tag_name}> at line {self.current().line}"
            )

        close_token = self.expect(TokenType.HTML_CLOSE_TAG)

        # Verify tag names match
        if close_token.value != tag_name:
            raise ParseError(
                f"Mismatched closing tag: expected </{tag_name}> but got </{close_token.value}> "
                f"at line {close_token.line}"
            )

        return ast_nodes.HTMLElement(
            tag_name=tag_name, attributes=attributes, children=children
        )

    def parse_void_element(self) -> ast_nodes.VoidElement:
        """Parse a self-closing/void element."""
        token = self.expect(TokenType.HTML_SELF_CLOSE)
        tag_name = token.value
        attributes = self.parse_attributes()
        return ast_nodes.VoidElement(tag_name=tag_name, attributes=attributes)

    def parse_attributes(self) -> list[ast_nodes.Attribute]:
        """Parse HTML attributes (supports both static and dynamic names)."""
        attributes = []

        while self.match(TokenType.ATTR_NAME) or self.match(
            TokenType.ATTR_NAME_DYNAMIC
        ):
            name_token = self.advance()
            name = name_token.value
            is_dynamic = name_token.type == TokenType.ATTR_NAME_DYNAMIC

            # Check for attribute value
            value = None
            if self.match(TokenType.ATTR_VALUE):
                value_token = self.advance()
                value = value_token.value

            attributes.append(
                ast_nodes.Attribute(name=name, value=value, is_dynamic_name=is_dynamic)
            )

        return attributes

    def parse_doctype(self) -> ast_nodes.DocType:
        """Parse a DOCTYPE declaration."""
        token = self.expect(TokenType.DOCTYPE)
        return ast_nodes.DocType(content=token.value)

    def parse_html_comment(self) -> ast_nodes.HTMLComment:
        """Parse an HTML comment."""
        token = self.expect(TokenType.HTML_COMMENT)
        return ast_nodes.HTMLComment(content=token.value)

    def parse_cdata(self) -> ast_nodes.CDATA:
        """Parse a CDATA section."""
        token = self.expect(TokenType.CDATA)
        return ast_nodes.CDATA(content=token.value)

    # ========================================================================
    # Template variable parsing
    # ========================================================================

    def parse_variable(self) -> ast_nodes.Variable:
        """Parse {{ variable|filter }}."""
        self.expect(TokenType.TEMPLATE_VAR_START)

        # Parse expression
        expression = self.parse_expression()

        # Parse filters
        filters = []
        while self.match(TokenType.PIPE):
            self.advance()  # |
            filters.append(self.parse_filter())

        self.expect(TokenType.TEMPLATE_VAR_END)

        return ast_nodes.Variable(expression=expression, filters=filters)

    def parse_filter(self) -> ast_nodes.Filter:
        """Parse a filter: filter_name or filter_name:arg1,arg2."""
        name_token = self.expect(TokenType.IDENTIFIER)
        name = name_token.value

        args = []
        if self.match(TokenType.COLON):
            self.advance()  # :

            # Parse first argument
            args.append(self.parse_filter_arg())

            # Parse additional arguments
            while self.match(TokenType.COMMA):
                self.advance()  # ,
                args.append(self.parse_filter_arg())

        return ast_nodes.Filter(name=name, args=args)

    def parse_filter_arg(self) -> str | int | float:
        """Parse a filter argument (string, number, or identifier)."""
        if self.match(TokenType.STRING):
            return self.advance().value
        elif self.match(TokenType.NUMBER):
            value = self.advance().value
            return float(value) if "." in value else int(value)
        elif self.match(TokenType.IDENTIFIER):
            return self.advance().value
        else:
            raise ParseError(f"Expected filter argument at line {self.current().line}")

    # ========================================================================
    # Expression parsing
    # ========================================================================

    def parse_expression(self) -> ast_nodes.Expression | ast_nodes.Literal:
        """
        Parse a variable expression or literal: user.name, items.0, 42, "string".

        Note: Django only supports dot notation, not bracket notation.
        Examples:
            {{ user.name }}     ✓ ast_nodes.Attribute access
            {{ items.0 }}       ✓ Numeric index via dot
            {{ user['name'] }}  ✗ NOT supported (no bracket syntax)
            {{ items[0] }}      ✗ NOT supported (no bracket syntax)
        """
        # Check for literal values first
        if self.match(TokenType.NUMBER):
            value = self.advance().value
            num_value = float(value) if "." in value else int(value)
            return ast_nodes.Literal(value=num_value, type="number")

        if self.match(TokenType.STRING):
            value = self.advance().value
            return ast_nodes.Literal(value=value, type="string")

        # Parse base identifier
        base_token = self.expect(TokenType.IDENTIFIER)
        base = base_token.value

        # Parse lookups (dot notation only - Django doesn't support brackets)
        # Track previous token to check for spaces before dots
        prev_token = base_token
        lookups = []
        while self.match(TokenType.DOT):
            dot_token = self.advance()  # .

            # Django doesn't allow spaces around dots in lookups
            # Valid: user.name, items.0
            # Invalid: user. name, user .name, user . name

            # Check 1: No space before the dot
            # The dot should immediately follow the previous token
            expected_dot_col = prev_token.column + len(prev_token.value)
            if (
                dot_token.line != prev_token.line
                or dot_token.column != expected_dot_col
            ):
                raise ParseError(
                    f"No spaces allowed before '.' in lookups at line {dot_token.line}. "
                    f"Use 'user.name' not 'user . name'"
                )

            # Check 2: No space after the dot
            # The next token should immediately follow the dot
            next_token = self.current()
            if (
                next_token.line != dot_token.line
                or next_token.column != dot_token.column + 1
            ):
                raise ParseError(
                    f"No spaces allowed after '.' in lookups at line {dot_token.line}. "
                    f"Use 'user.name' not 'user . name'"
                )

            # Django allows identifiers, numbers, and keywords after dot
            # e.g., user.name or items.0 or obj.as
            if self.is_identifier_like():
                attr_token = self.advance()
                lookups.append(
                    ast_nodes.Lookup(type="attribute", value=attr_token.value)
                )
                prev_token = attr_token  # Track for next iteration
            else:
                raise ParseError(
                    f"Expected attribute name or index after '.' at line {self.current().line}"
                )

        return ast_nodes.Expression(base=base, lookups=lookups)

    def parse_expression_with_filters(
        self,
    ) -> ast_nodes.Expression | ast_nodes.Literal | ast_nodes.FilteredExpression:
        """
        Parse an expression with optional filters.

        Used in conditions where filters are allowed: {% if field|length > 1 %}
        Returns ast_nodes.Expression/ast_nodes.Literal if no filters, ast_nodes.FilteredExpression if filters present.
        """
        # Parse base expression
        expression = self.parse_expression()

        # Check for filters
        if self.match(TokenType.PIPE):
            filters = []
            while self.match(TokenType.PIPE):
                self.advance()  # |
                filters.append(self.parse_filter())

            # Wrap in FilteredExpression
            return ast_nodes.FilteredExpression(expression=expression, filters=filters)

        # No filters, return plain expression
        return expression

    # ========================================================================
    # Template tag parsing
    # ========================================================================

    def parse_template_tag(self) -> ast_nodes.ASTNode:
        """Parse template tags like {% if %}, {% for %}, etc."""
        self.expect(TokenType.TEMPLATE_TAG_START)

        tag_type = self.current().type

        # If block
        if tag_type == TokenType.IF:
            return self.parse_if_block()

        # For block
        elif tag_type == TokenType.FOR:
            return self.parse_for_block()

        # Block tag
        elif tag_type == TokenType.BLOCK:
            return self.parse_block_tag()

        # With block
        elif tag_type == TokenType.WITH:
            return self.parse_with_block()

        # Include tag
        elif tag_type == TokenType.INCLUDE:
            return self.parse_include_tag()

        # Extends tag
        elif tag_type == TokenType.EXTENDS:
            return self.parse_extends_tag()

        # Load tag
        elif tag_type == TokenType.LOAD:
            return self.parse_load_tag()

        # URL tag
        elif tag_type == TokenType.URL:
            return self.parse_url_tag()

        # Static tag
        elif tag_type == TokenType.STATIC:
            return self.parse_static_tag()

        # CSRF token
        elif tag_type == TokenType.CSRF_TOKEN:
            return self.parse_csrf_token_tag()

        # Cycle tag
        elif tag_type == TokenType.CYCLE:
            return self.parse_cycle_tag()

        # Reset cycle tag
        elif tag_type == TokenType.RESETCYCLE:
            return self.parse_resetcycle_tag()

        # Debug tag
        elif tag_type == TokenType.DEBUG:
            return self.parse_debug_tag()

        # Lorem tag
        elif tag_type == TokenType.LOREM:
            return self.parse_lorem_tag()

        # Regroup tag
        elif tag_type == TokenType.REGROUP:
            return self.parse_regroup_tag()

        # Query string tag
        elif tag_type == TokenType.QUERYSTRING:
            return self.parse_querystring_tag()

        # Comment block
        elif tag_type == TokenType.COMMENT:
            return self.parse_comment_block()

        # Ifchanged block
        elif tag_type == TokenType.IFCHANGED:
            return self.parse_ifchanged_block()

        # Filter block
        elif tag_type == TokenType.FILTER:
            return self.parse_filter_block()

        # Spaceless block
        elif tag_type == TokenType.SPACELESS:
            return self.parse_spaceless_block()

        # Verbatim block
        elif tag_type == TokenType.VERBATIM:
            return self.parse_verbatim_block()

        # Autoescape block
        elif tag_type == TokenType.AUTOESCAPE:
            return self.parse_autoescape_block()

        # Generic single tag or custom block tag
        elif tag_type == TokenType.IDENTIFIER:
            tag_name = self.current().value.lower()

            # Check if this is a discovered custom block tag
            if tag_name in self.block_tags:
                return self.parse_generic_block_tag()
            else:
                return self.parse_single_tag()

        else:
            raise ParseError(
                f"Unknown template tag {self.current().value} at line {self.current().line}"
            )

    def parse_if_block(self) -> ast_nodes.IfBlock:
        """Parse {% if condition %}...{% elif %}...{% else %}...{% endif %}."""
        self.expect(TokenType.IF)

        # Parse if condition
        if_condition = self.parse_condition()
        self.expect(TokenType.TEMPLATE_TAG_END)

        # Parse if body
        if_children = self.parse_block_body(
            [TokenType.ELIF, TokenType.ELSE, TokenType.ENDIF]
        )

        # Parse elif branches
        elif_branches = []
        while (
            self.match(TokenType.TEMPLATE_TAG_START)
            and self.peek().type == TokenType.ELIF
        ):
            self.expect(TokenType.TEMPLATE_TAG_START)
            self.expect(TokenType.ELIF)

            elif_condition = self.parse_condition()
            self.expect(TokenType.TEMPLATE_TAG_END)

            elif_children = self.parse_block_body(
                [TokenType.ELIF, TokenType.ELSE, TokenType.ENDIF]
            )
            elif_branches.append((elif_condition, elif_children))

        # Parse else branch
        else_children = None
        if (
            self.match(TokenType.TEMPLATE_TAG_START)
            and self.peek().type == TokenType.ELSE
        ):
            self.expect(TokenType.TEMPLATE_TAG_START)
            self.expect(TokenType.ELSE)
            self.expect(TokenType.TEMPLATE_TAG_END)

            else_children = self.parse_block_body([TokenType.ENDIF])

        # Parse endif
        self.expect(TokenType.TEMPLATE_TAG_START)
        self.expect(TokenType.ENDIF)
        self.expect(TokenType.TEMPLATE_TAG_END)

        return ast_nodes.IfBlock(
            if_condition=if_condition,
            if_children=if_children,
            elif_branches=elif_branches,
            else_children=else_children,
        )

    def parse_for_block(self) -> ast_nodes.ForBlock:
        """Parse {% for item in items %} or {% for key, value in items %}."""
        self.expect(TokenType.FOR)

        # Parse loop variables (can be tuple unpacking)
        loop_vars = []
        loop_vars.append(self.expect(TokenType.IDENTIFIER).value)

        # Check for comma-separated variables (tuple unpacking)
        while self.match(TokenType.COMMA):
            self.advance()  # ,
            loop_vars.append(self.expect(TokenType.IDENTIFIER).value)

        # Expect 'in'
        self.expect(TokenType.IN)

        # Parse iterable
        iterable = self.parse_expression()

        self.expect(TokenType.TEMPLATE_TAG_END)

        # Parse loop body
        children = self.parse_block_body([TokenType.EMPTY, TokenType.ENDFOR])

        # Parse empty clause
        empty_children = None
        if (
            self.match(TokenType.TEMPLATE_TAG_START)
            and self.peek().type == TokenType.EMPTY
        ):
            self.expect(TokenType.TEMPLATE_TAG_START)
            self.expect(TokenType.EMPTY)
            self.expect(TokenType.TEMPLATE_TAG_END)

            empty_children = self.parse_block_body([TokenType.ENDFOR])

        # Parse endfor
        self.expect(TokenType.TEMPLATE_TAG_START)
        self.expect(TokenType.ENDFOR)
        self.expect(TokenType.TEMPLATE_TAG_END)

        return ast_nodes.ForBlock(
            loop_vars=loop_vars,
            iterable=iterable,
            children=children,
            empty_children=empty_children,
        )

    def parse_block_tag(self) -> ast_nodes.BlockTag:
        """Parse {% block name %}...{% endblock %}."""
        self.expect(TokenType.BLOCK)

        # Parse block name
        name_token = self.expect(TokenType.IDENTIFIER)
        name = name_token.value

        self.expect(TokenType.TEMPLATE_TAG_END)

        # Parse block body
        children = self.parse_block_body([TokenType.ENDBLOCK])

        # Parse endblock
        self.expect(TokenType.TEMPLATE_TAG_START)
        self.expect(TokenType.ENDBLOCK)

        # Optional: block name can appear after endblock
        if self.match(TokenType.IDENTIFIER):
            end_name = self.advance().value
            if end_name != name:
                raise ParseError(
                    f"Block name mismatch: {name} vs {end_name} at line {self.current().line}"
                )

        self.expect(TokenType.TEMPLATE_TAG_END)

        return ast_nodes.BlockTag(name=name, children=children)

    def parse_with_block(self) -> ast_nodes.WithBlock:
        """Parse {% with var=value %}...{% endwith %}."""
        self.expect(TokenType.WITH)

        # Parse assignments
        assignments = []

        while not self.match(TokenType.TEMPLATE_TAG_END):
            var_name = self.expect(TokenType.IDENTIFIER).value
            self.expect(TokenType.EQUALS)
            var_value = self.parse_expression()

            assignments.append((var_name, var_value))

            # Check for additional assignments
            if not self.match(TokenType.TEMPLATE_TAG_END):
                # Could be whitespace or another assignment
                pass

        self.expect(TokenType.TEMPLATE_TAG_END)

        # Parse block body
        children = self.parse_block_body([TokenType.ENDWITH])

        # Parse endwith
        self.expect(TokenType.TEMPLATE_TAG_START)
        self.expect(TokenType.ENDWITH)
        self.expect(TokenType.TEMPLATE_TAG_END)

        return ast_nodes.WithBlock(assignments=assignments, children=children)

    def parse_include_tag(self) -> ast_nodes.IncludeTag:
        """
        Parse {% include "template.html" %} or {% include "template.html" with var=value %}.

        Supports the 'with' clause for passing context variables to the included template.
        """
        self.expect(TokenType.INCLUDE)

        # Parse template name (string or variable)
        if self.match(TokenType.STRING):
            template_name = self.advance().value
        else:
            # Could be a variable expression
            template_name = self.parse_expression()

        # Parse optional 'with' clause
        context_vars = {}
        if self.match(TokenType.WITH):
            self.advance()  # with

            # Parse key=value pairs
            while not self.match(TokenType.TEMPLATE_TAG_END):
                # Parse key (identifier)
                key_token = self.expect(TokenType.IDENTIFIER)
                key = key_token.value

                # Expect =
                self.expect(TokenType.EQUALS)

                # Parse value (expression)
                value = self.parse_expression()

                context_vars[key] = value

                # Check if there are more assignments (no explicit separator in Django)
                if self.match(TokenType.TEMPLATE_TAG_END):
                    break

        self.expect(TokenType.TEMPLATE_TAG_END)

        # If template_name is a string, use it directly; otherwise it's an Expression
        if isinstance(template_name, str):
            return ast_nodes.IncludeTag(
                template_name=template_name, context_vars=context_vars
            )
        else:
            # For variable includes, convert expression to string representation
            return ast_nodes.IncludeTag(
                template_name=str(template_name), context_vars=context_vars
            )

    def parse_extends_tag(self) -> ast_nodes.ExtendsTag:
        """Parse {% extends "base.html" %}."""
        self.expect(TokenType.EXTENDS)

        # Parse parent template name
        parent_template = self.expect(TokenType.STRING).value

        self.expect(TokenType.TEMPLATE_TAG_END)

        return ast_nodes.ExtendsTag(parent_template=parent_template)

    def parse_load_tag(self) -> ast_nodes.LoadTag:
        """Parse {% load static %} or {% load static humanize %}."""
        self.expect(TokenType.LOAD)

        # Parse library names (can be multiple)
        # NOTE: Libraries might be keywords (like 'static'), so accept both IDENTIFIER and other keywords
        libraries = []
        while not self.match(TokenType.TEMPLATE_TAG_END):
            token = self.current()
            # Accept identifiers or keyword tokens as library names
            if (
                token.type in (TokenType.IDENTIFIER, TokenType.STATIC, TokenType.URL)
                or token.value.isidentifier()
            ):
                libraries.append(self.advance().value)
            else:
                break

        if not libraries:
            raise ParseError(
                f"Expected at least one library name in load tag at line {self.current().line}"
            )

        self.expect(TokenType.TEMPLATE_TAG_END)

        return ast_nodes.LoadTag(libraries=libraries)

    def parse_url_tag(self) -> ast_nodes.UrlTag:
        """Parse {% url 'view_name' arg1 arg2 key=val as var %}."""
        self.expect(TokenType.URL)

        # Parse view name (must be string or identifier)
        if self.match(TokenType.STRING):
            view_name = self.advance().value
        elif self.match(TokenType.IDENTIFIER):
            view_name = self.advance().value
        else:
            raise ParseError(
                f"Expected view name in url tag at line {self.current().line}"
            )

        # Parse args and kwargs
        args = []
        kwargs = {}
        as_var = None

        while not self.match(TokenType.TEMPLATE_TAG_END):
            # Check for 'as' keyword
            if self.match(TokenType.AS):
                self.advance()
                as_var = self.expect(TokenType.IDENTIFIER).value
                break

            # Check for keyword argument (key=value)
            if self.match(TokenType.IDENTIFIER):
                # Look ahead for =
                if self.peek().type == TokenType.EQUALS:
                    key = self.advance().value
                    self.expect(TokenType.EQUALS)

                    # Parse value expression
                    kwargs[key] = self.parse_expression()
                else:
                    # Positional argument - parse as expression to handle attribute access
                    args.append(self.parse_expression())

            elif self.match(TokenType.STRING):
                args.append(self.advance().value)
            elif self.match(TokenType.NUMBER):
                args.append(self.advance().value)
            else:
                break

        self.expect(TokenType.TEMPLATE_TAG_END)
        return ast_nodes.UrlTag(
            view_name=view_name, args=args, kwargs=kwargs, as_var=as_var
        )

    def parse_static_tag(self) -> ast_nodes.StaticTag:
        """Parse {% static 'path/to/file.css' as var %}."""
        self.expect(TokenType.STATIC)

        # Parse path (string or identifier)
        if self.match(TokenType.STRING):
            path = self.advance().value
        elif self.match(TokenType.IDENTIFIER):
            path = self.advance().value
        else:
            raise ParseError(
                f"Expected path in static tag at line {self.current().line}"
            )

        # Check for 'as' keyword
        as_var = None
        if self.match(TokenType.AS):
            self.advance()
            as_var = self.expect(TokenType.IDENTIFIER).value

        self.expect(TokenType.TEMPLATE_TAG_END)
        return ast_nodes.StaticTag(path=path, as_var=as_var)

    def parse_csrf_token_tag(self) -> ast_nodes.CsrfTokenTag:
        """Parse {% csrf_token %}."""
        self.expect(TokenType.CSRF_TOKEN)
        self.expect(TokenType.TEMPLATE_TAG_END)

        return ast_nodes.CsrfTokenTag()

    def parse_cycle_tag(self) -> ast_nodes.CycleTag:
        """Parse {% cycle 'val1' 'val2' as name %} or {% cycle name %}."""
        self.expect(TokenType.CYCLE)

        values = []
        cycle_name = None

        # Parse values until we hit 'as' or %}
        while not self.match(TokenType.TEMPLATE_TAG_END):
            if self.match(TokenType.AS):
                # 'as' keyword for naming the cycle
                self.advance()  # AS
                cycle_name = self.expect(TokenType.IDENTIFIER).value
                break
            elif self.match(TokenType.IDENTIFIER):
                # Variable reference in silent mode
                values.append(self.current().value)
                self.advance()
            elif self.match(TokenType.STRING):
                values.append(self.advance().value)
            elif self.match(TokenType.NUMBER):
                values.append(self.advance().value)
            else:
                break

        self.expect(TokenType.TEMPLATE_TAG_END)
        return ast_nodes.CycleTag(values=values, cycle_name=cycle_name)

    def parse_resetcycle_tag(self) -> ast_nodes.ResetCycleTag:
        """Parse {% resetcycle %} or {% resetcycle name %}."""
        self.expect(TokenType.RESETCYCLE)

        cycle_name = None
        if self.match(TokenType.IDENTIFIER):
            cycle_name = self.advance().value

        self.expect(TokenType.TEMPLATE_TAG_END)
        return ast_nodes.ResetCycleTag(cycle_name=cycle_name)

    def parse_debug_tag(self) -> ast_nodes.DebugTag:
        """Parse {% debug %}."""
        self.expect(TokenType.DEBUG)
        self.expect(TokenType.TEMPLATE_TAG_END)
        return ast_nodes.DebugTag()

    def parse_lorem_tag(self) -> ast_nodes.LoremTag:
        """Parse {% lorem [count] [method] [random] %}."""
        self.expect(TokenType.LOREM)

        count = 1
        method = "w"
        random = False

        # Parse optional arguments
        if self.match(TokenType.NUMBER):
            count = int(self.advance().value)

        if self.match(TokenType.IDENTIFIER):
            method_val = self.advance().value.lower()
            if method_val in ("w", "p", "b"):
                method = method_val

        if self.match(TokenType.IDENTIFIER):
            random_val = self.current().value.lower()
            if random_val == "random":
                random = True
                self.advance()

        self.expect(TokenType.TEMPLATE_TAG_END)
        return ast_nodes.LoremTag(count=count, method=method, random=random)

    def parse_regroup_tag(self) -> ast_nodes.RegroupTag:
        """Parse {% regroup list by attribute as var %}."""
        self.expect(TokenType.REGROUP)

        # Parse list expression
        list_expr = self.parse_expression()

        # Expect 'by'
        if not self.match(TokenType.BY):
            raise ParseError(
                f"Expected 'by' in regroup tag at line {self.current().line}"
            )
        self.advance()  # BY

        # Parse attribute
        attribute = self.expect(TokenType.IDENTIFIER).value

        # Expect 'as'
        if not self.match(TokenType.AS):
            raise ParseError(
                f"Expected 'as' in regroup tag at line {self.current().line}"
            )
        self.advance()  # AS

        # Parse variable name
        var_name = self.expect(TokenType.IDENTIFIER).value

        self.expect(TokenType.TEMPLATE_TAG_END)
        return ast_nodes.RegroupTag(
            list_expr=list_expr, attribute=attribute, var_name=var_name
        )

    def parse_querystring_tag(self) -> ast_nodes.QueryStringTag:
        """Parse {% querystring key=value key2=value2 %}."""
        self.expect(TokenType.QUERYSTRING)

        updates = {}

        # Parse key=value pairs
        while not self.match(TokenType.TEMPLATE_TAG_END):
            if self.match(TokenType.IDENTIFIER):
                key = self.advance().value

                # Check for =
                if self.match(TokenType.EQUALS):
                    self.advance()

                    # Parse value (string, number, or identifier)
                    if self.match(TokenType.STRING):
                        value = self.advance().value
                    elif self.match(TokenType.NUMBER):
                        value = self.advance().value
                    elif self.match(TokenType.IDENTIFIER):
                        value = self.advance().value
                    else:
                        raise ParseError(
                            f"Expected value after '=' at line {self.current().line}"
                        )

                    updates[key] = value
            else:
                break

        self.expect(TokenType.TEMPLATE_TAG_END)
        return ast_nodes.QueryStringTag(updates=updates)

    def parse_single_tag(self):
        """
        Parse arbitrary single tags like {% url 'name' %}, {% static 'path' %}, etc.
        Collects everything between the tag name and %} as raw content.
        """

        # Get tag name
        tag_name_token = self.expect(TokenType.IDENTIFIER)
        tag_name = tag_name_token.value

        # Collect all content until %}
        content_parts = []
        while not self.match(TokenType.TEMPLATE_TAG_END):
            if self.match(TokenType.EOF):
                raise ParseError(f"Unterminated single tag '{tag_name}'")

            token = self.advance()
            content_parts.append(token.value)

        self.expect(TokenType.TEMPLATE_TAG_END)

        raw_content = " ".join(content_parts).strip()
        return ast_nodes.SingleTag(tag_name=tag_name, raw_content=raw_content)

    def parse_generic_block_tag(self):
        """
        Parse generic/custom block tags like {% myblock args %}...{% endmyblock %}.
        Used for auto-discovered block tags.
        """

        # Get tag name
        tag_name_token = self.expect(TokenType.IDENTIFIER)
        tag_name = tag_name_token.value

        # Collect arguments until %}
        args_parts = []
        while not self.match(TokenType.TEMPLATE_TAG_END):
            if self.match(TokenType.EOF):
                raise ParseError(f"Unterminated block tag '{tag_name}'")
            token = self.advance()
            args_parts.append(token.value)

        self.expect(TokenType.TEMPLATE_TAG_END)
        raw_args = " ".join(args_parts).strip()

        # Parse block body until {% endTAGNAME %}
        children = []
        while not self.match(TokenType.EOF):
            # Check for end tag
            if self.match(TokenType.TEMPLATE_TAG_START):
                next_token = self.peek()
                if next_token.type == TokenType.IDENTIFIER:
                    end_tag_name = next_token.value.lower()
                    if end_tag_name == f"end{tag_name.lower()}":
                        # Found matching end tag
                        self.expect(TokenType.TEMPLATE_TAG_START)
                        self.expect(TokenType.IDENTIFIER)  # end{tagname}
                        self.expect(TokenType.TEMPLATE_TAG_END)
                        break

            # Parse child element
            child = self.parse_element()
            if child:
                children.append(child)

        return ast_nodes.GenericBlockTag(
            tag_name=tag_name, raw_args=raw_args, children=children
        )

    def parse_comment_block(self) -> ast_nodes.CommentBlock:
        """Parse {% comment %}...{% endcomment %}."""
        self.expect(TokenType.COMMENT)
        self.expect(TokenType.TEMPLATE_TAG_END)

        # Parse block body (everything inside is ignored but still parsed for structure)
        children = self.parse_block_body([TokenType.ENDCOMMENT])

        # Parse endcomment
        self.expect(TokenType.TEMPLATE_TAG_START)
        self.expect(TokenType.ENDCOMMENT)
        self.expect(TokenType.TEMPLATE_TAG_END)

        return ast_nodes.CommentBlock(children=children)

    def parse_ifchanged_block(self) -> ast_nodes.IfChangedBlock:
        """Parse {% ifchanged var1 var2 %}...{% endifchanged %}."""
        self.expect(TokenType.IFCHANGED)

        # Parse optional watch expressions
        watch_expressions = []
        while not self.match(TokenType.TEMPLATE_TAG_END):
            if self.match(TokenType.IDENTIFIER):
                watch_expressions.append(self.parse_expression())
            else:
                break

        self.expect(TokenType.TEMPLATE_TAG_END)

        # Parse block body
        children = self.parse_block_body([TokenType.ENDIFCHANGED])

        # Parse endifchanged
        self.expect(TokenType.TEMPLATE_TAG_START)
        self.expect(TokenType.ENDIFCHANGED)
        self.expect(TokenType.TEMPLATE_TAG_END)

        return ast_nodes.IfChangedBlock(
            watch_expressions=watch_expressions, children=children
        )

    def parse_filter_block(self) -> ast_nodes.FilterBlock:
        """Parse {% filter name %}...{% endfilter %}."""
        self.expect(TokenType.FILTER)

        # Parse filter name
        filter_name = self.expect(TokenType.IDENTIFIER).value

        self.expect(TokenType.TEMPLATE_TAG_END)

        # Parse block body
        children = self.parse_block_body([TokenType.ENDFILTER])

        # Parse endfilter
        self.expect(TokenType.TEMPLATE_TAG_START)
        self.expect(TokenType.ENDFILTER)
        self.expect(TokenType.TEMPLATE_TAG_END)

        return ast_nodes.FilterBlock(filter_name=filter_name, children=children)

    def parse_spaceless_block(self) -> ast_nodes.SpacelessBlock:
        """Parse {% spaceless %}...{% endspaceless %}."""
        self.expect(TokenType.SPACELESS)
        self.expect(TokenType.TEMPLATE_TAG_END)

        # Parse block body
        children = self.parse_block_body([TokenType.ENDSPACELESS])

        # Parse endspaceless
        self.expect(TokenType.TEMPLATE_TAG_START)
        self.expect(TokenType.ENDSPACELESS)
        self.expect(TokenType.TEMPLATE_TAG_END)

        return ast_nodes.SpacelessBlock(children=children)

    def parse_verbatim_block(self) -> ast_nodes.VerbatimBlock:
        """Parse {% verbatim %}...{% endverbatim %}."""
        self.expect(TokenType.VERBATIM)
        self.expect(TokenType.TEMPLATE_TAG_END)

        # Collect raw content until {% endverbatim %}
        # Inside verbatim, nothing is parsed - it's all raw text
        content_parts = []
        while not self.match(TokenType.EOF):
            if self.match(TokenType.TEMPLATE_TAG_START):
                # Check if this is the end tag
                next_token = self.peek()
                if next_token.type == TokenType.ENDVERBATIM:
                    # End of verbatim block
                    self.expect(TokenType.TEMPLATE_TAG_START)
                    self.expect(TokenType.ENDVERBATIM)
                    self.expect(TokenType.TEMPLATE_TAG_END)
                    break

            # Add token to content
            token = self.advance()
            content_parts.append(token.value)

        content = "".join(content_parts)
        return ast_nodes.VerbatimBlock(content=content)

    def parse_autoescape_block(self) -> ast_nodes.AutoescapeBlock:
        """Parse {% autoescape on/off %}...{% endautoescape %}."""
        self.expect(TokenType.AUTOESCAPE)

        # Parse mode (on or off)
        mode_token = self.expect(TokenType.IDENTIFIER)
        mode = mode_token.value.lower()

        if mode not in ("on", "off"):
            raise ParseError(
                f"Autoescape mode must be 'on' or 'off', got '{mode}' at line {mode_token.line}"
            )

        self.expect(TokenType.TEMPLATE_TAG_END)

        # Parse block body
        children = self.parse_block_body([TokenType.ENDAUTOESCAPE])

        # Parse endautoescape
        self.expect(TokenType.TEMPLATE_TAG_START)
        self.expect(TokenType.ENDAUTOESCAPE)
        self.expect(TokenType.TEMPLATE_TAG_END)

        return ast_nodes.AutoescapeBlock(mode=mode, children=children)

    def parse_block_body(self, end_tokens: list[TokenType]) -> list[ast_nodes.ASTNode]:
        """Parse the body of a block until we hit an end token."""
        children = []

        while not self.match(TokenType.EOF):
            # Check if we've hit an end token
            if self.match(TokenType.TEMPLATE_TAG_START):
                next_token = self.peek()
                if next_token.type in end_tokens:
                    break

            child = self.parse_element()
            if child:
                children.append(child)

        return children

    # ========================================================================
    # Condition parsing (for if/elif)
    # ========================================================================

    def parse_condition(self) -> ast_nodes.Condition:
        """Parse a boolean condition."""
        return self.parse_or_condition()

    def parse_or_condition(self) -> ast_nodes.Condition:
        """Parse OR conditions."""
        left = self.parse_and_condition()

        if self.match(TokenType.OR):
            operands = [left]
            while self.match(TokenType.OR):
                self.advance()
                operands.append(self.parse_and_condition())
            return ast_nodes.BooleanOp(operator="or", operands=operands)

        return left

    def parse_and_condition(self) -> ast_nodes.Condition:
        """Parse AND conditions."""
        left = self.parse_not_condition()

        if self.match(TokenType.AND):
            operands = [left]
            while self.match(TokenType.AND):
                self.advance()
                operands.append(self.parse_not_condition())
            return ast_nodes.BooleanOp(operator="and", operands=operands)

        return left

    def parse_not_condition(self) -> ast_nodes.Condition:
        """Parse NOT conditions."""
        if self.match(TokenType.NOT):
            self.advance()
            expr = self.parse_primary_condition()
            return ast_nodes.SimpleCondition(expression=expr, negated=True)

        return self.parse_primary_condition()

    def parse_primary_condition(self) -> ast_nodes.Condition:
        """
        Parse primary condition (comparison or simple expression).

        Now supports filters in conditions: {% if field|length > 1 %}
        """
        # Parse left side (with optional filters)
        left = self.parse_expression_with_filters()

        # Check for comparison operator
        if self.match(
            TokenType.EQ,
            TokenType.NE,
            TokenType.LT,
            TokenType.GT,
            TokenType.LE,
            TokenType.GE,
        ):
            op_token = self.advance()
            right = self.parse_expression_with_filters()

            op_map = {
                TokenType.EQ: "==",
                TokenType.NE: "!=",
                TokenType.LT: "<",
                TokenType.GT: ">",
                TokenType.LE: "<=",
                TokenType.GE: ">=",
            }

            return ast_nodes.Comparison(
                left=left, operator=op_map[op_token.type], right=right
            )

        # Check for 'in' operator
        if self.match(TokenType.IN):
            self.advance()
            right = self.parse_expression_with_filters()
            return ast_nodes.Comparison(left=left, operator="in", right=right)

        # Simple expression (truthy check)
        return ast_nodes.SimpleCondition(expression=left, negated=False)

    # ========================================================================
    # Comment parsing
    # ========================================================================

    def parse_comment(self) -> ast_nodes.Comment:
        """Parse {# comment #}."""
        self.expect(TokenType.TEMPLATE_COMMENT_START)

        # Read comment text
        content = ""
        if self.match(TokenType.TEXT):
            content = self.advance().value

        self.expect(TokenType.TEMPLATE_COMMENT_END)

        return ast_nodes.Comment(content=content)


def parse(content: str) -> ast_nodes.Document:
    """
    Convenience function to lex and parse a template.

    Uses two-pass approach:
    1. Discover block tags by scanning for {% endX %} patterns
    2. Parse with discovered block tags
    """
    # Pass 1: Discover block tags
    discovered_blocks = set()
    pattern = re.compile(r"\{%\s*end(\w+)")
    for match in pattern.finditer(content):
        discovered_blocks.add(match.group(1).lower())

    # Pass 2: Lex and parse
    lexer = Lexer(content)
    tokens = lexer.tokenize()
    parser = Parser(tokens, discovered_blocks=discovered_blocks)
    return parser.parse()


if __name__ == "__main__":
    # Test the parser
    template = """
    <div class="container">
        {% if user %}
            <p>Hello {{ user.name|upper }}!</p>
            <ul>
                {% for item in items %}
                    <li>{{ item }}</li>
                {% empty %}
                    <li>No items</li>
                {% endfor %}
            </ul>
        {% endif %}
    </div>
    """

    ast = parse(template)
    printer = ast_nodes.ASTPrinter()
    printer.visit(ast)
