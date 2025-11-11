"""
Lexer (tokenizer) for RDTL.

Converts template string into a stream of tokens.
"""

from dataclasses import dataclass
from enum import Enum, auto


class TokenType(Enum):
    """Types of tokens in RDTL."""

    # HTML tokens
    HTML_OPEN_TAG = auto()  # <div>
    HTML_CLOSE_TAG = auto()  # </div>
    HTML_SELF_CLOSE = auto()  # <br />
    ATTR_NAME = auto()  # attribute name (static)
    ATTR_NAME_DYNAMIC = auto()  # attribute name (contains templates)
    ATTR_VALUE = auto()  # attribute value
    DOCTYPE = auto()  # <!DOCTYPE html>
    HTML_COMMENT = auto()  # <!-- comment -->
    CDATA = auto()  # <![CDATA[...]]>

    # Template tokens
    TEMPLATE_VAR_START = auto()  # {{
    TEMPLATE_VAR_END = auto()  # }}
    TEMPLATE_TAG_START = auto()  # {%
    TEMPLATE_TAG_END = auto()  # %}
    TEMPLATE_COMMENT_START = auto()  # {#
    TEMPLATE_COMMENT_END = auto()  # #}

    # Template keywords
    IF = auto()
    ELIF = auto()
    ELSE = auto()
    ENDIF = auto()
    FOR = auto()
    IN = auto()
    EMPTY = auto()
    ENDFOR = auto()
    BLOCK = auto()
    ENDBLOCK = auto()
    WITH = auto()
    ENDWITH = auto()
    INCLUDE = auto()
    EXTENDS = auto()
    LOAD = auto()
    CSRF_TOKEN = auto()
    AUTOESCAPE = auto()
    ENDAUTOESCAPE = auto()
    COMMENT = auto()
    ENDCOMMENT = auto()
    IFCHANGED = auto()
    ENDIFCHANGED = auto()
    FILTER = auto()
    ENDFILTER = auto()
    SPACELESS = auto()
    ENDSPACELESS = auto()
    VERBATIM = auto()
    ENDVERBATIM = auto()
    CYCLE = auto()
    RESETCYCLE = auto()
    DEBUG = auto()
    LOREM = auto()
    REGROUP = auto()
    QUERYSTRING = auto()
    URL = auto()
    STATIC = auto()
    AS = auto()
    BY = auto()

    # Operators and symbols
    PIPE = auto()  # |
    COLON = auto()  # :
    COMMA = auto()  # ,
    DOT = auto()  # .
    EQUALS = auto()  # =
    LPAREN = auto()  # (
    RPAREN = auto()  # )
    LBRACKET = auto()  # [
    RBRACKET = auto()  # ]

    # Comparison operators
    EQ = auto()  # ==
    NE = auto()  # !=
    LT = auto()  # <
    GT = auto()  # >
    LE = auto()  # <=
    GE = auto()  # >=

    # Logical operators
    AND = auto()
    OR = auto()
    NOT = auto()

    # Literals and identifiers
    IDENTIFIER = auto()
    STRING = auto()
    NUMBER = auto()

    # Text content
    TEXT = auto()

    # Special
    EOF = auto()


@dataclass
class Token:
    """A single token from the lexer."""

    type: TokenType
    value: str
    line: int
    column: int

    def __repr__(self) -> str:
        return f"Token({self.type.name}, {self.value!r}, {self.line}:{self.column})"


class Lexer:
    """Tokenizes RDTL template strings into a stream of tokens.

    The lexer implements a state machine that switches between different modes
    based on Django template delimiters. It handles HTML, template tags,
    variables, and comments while tracking position for error reporting.

    State Machine Modes:
        TEXT Mode (default):
            - Reads HTML tags, text content, and plain characters
            - Watches for template delimiters: {%, {{, {#, <!--
            - Emits: HTML_OPEN_TAG, HTML_CLOSE_TAG, TEXT, HTML_COMMENT, DOCTYPE
            - Transitions to TAG/VAR/COMMENT mode on delimiter detection

        TAG Mode ({% ... %}):
            - Active inside Django template tags
            - Tokenizes keywords, identifiers, operators, literals
            - Emits: TEMPLATE_TAG_START, keywords (IF, FOR, etc.), IDENTIFIER,
                     STRING, NUMBER, operators (==, !=, |, etc.), TEMPLATE_TAG_END
            - Returns to TEXT mode on %}

        VAR Mode ({{ ... }}):
            - Active inside Django variable interpolations
            - Tokenizes variable names, lookups, filters
            - Emits: TEMPLATE_VAR_START, IDENTIFIER, DOT, PIPE, COLON,
                     STRING, NUMBER, TEMPLATE_VAR_END
            - Returns to TEXT mode on }}

        COMMENT Mode ({# ... #}):
            - Active inside Django template comments
            - Collects all content until closing delimiter
            - Emits: COMMENT token with full comment text
            - Returns to TEXT mode on #}

    HTML Parsing Features:
        The lexer includes specialized HTML parsing:
        - Opening tags: <div>, <span>, etc.
        - Closing tags: </div>, </span>, etc.
        - Self-closing/void: <img>, <br>, <input>
        - Attributes: class="foo", disabled, data-value="123"
        - Dynamic attributes: {{ attr_name }}="value"
        - DOCTYPE declarations: <!DOCTYPE html>
        - HTML comments: <!-- comment -->

    Keyword Recognition:
        The lexer maintains a KEYWORDS dictionary mapping strings to token types.
        Common keywords include:
        - Control flow: if, elif, else, endif, for, endfor
        - Blocks: block, endblock, with, endwith
        - Tags: include, extends, load, url, static
        - Operators: and, or, not, as, by, in

    Position Tracking:
        The lexer tracks line and column numbers for error reporting:
        - line: Current line number (1-indexed)
        - column: Current column number (1-indexed)
        - Each token includes position information

    Usage:
        lexer = Lexer(template_string)
        tokens = lexer.tokenize()
        for token in tokens:
            print(f"{token.type}: {token.value} at {token.line}:{token.col}")

    Error Handling:
        The lexer raises LexError for:
        - Unterminated strings
        - Invalid characters in specific modes
        - Malformed template delimiters

    Thread Safety:
        Lexer instances are NOT thread-safe. Each instance maintains
        mutable position state. Create separate instances for concurrent
        tokenization.
    """

    # Keywords that can appear in template tags
    KEYWORDS = {
        "if": TokenType.IF,
        "elif": TokenType.ELIF,
        "else": TokenType.ELSE,
        "endif": TokenType.ENDIF,
        "for": TokenType.FOR,
        "in": TokenType.IN,
        "empty": TokenType.EMPTY,
        "endfor": TokenType.ENDFOR,
        "block": TokenType.BLOCK,
        "endblock": TokenType.ENDBLOCK,
        "with": TokenType.WITH,
        "endwith": TokenType.ENDWITH,
        "include": TokenType.INCLUDE,
        "extends": TokenType.EXTENDS,
        "load": TokenType.LOAD,
        "csrf_token": TokenType.CSRF_TOKEN,
        "autoescape": TokenType.AUTOESCAPE,
        "endautoescape": TokenType.ENDAUTOESCAPE,
        "comment": TokenType.COMMENT,
        "endcomment": TokenType.ENDCOMMENT,
        "ifchanged": TokenType.IFCHANGED,
        "endifchanged": TokenType.ENDIFCHANGED,
        "filter": TokenType.FILTER,
        "endfilter": TokenType.ENDFILTER,
        "spaceless": TokenType.SPACELESS,
        "endspaceless": TokenType.ENDSPACELESS,
        "verbatim": TokenType.VERBATIM,
        "endverbatim": TokenType.ENDVERBATIM,
        "cycle": TokenType.CYCLE,
        "resetcycle": TokenType.RESETCYCLE,
        "debug": TokenType.DEBUG,
        "lorem": TokenType.LOREM,
        "regroup": TokenType.REGROUP,
        "querystring": TokenType.QUERYSTRING,
        "url": TokenType.URL,
        "static": TokenType.STATIC,
        "as": TokenType.AS,
        "by": TokenType.BY,
        "and": TokenType.AND,
        "or": TokenType.OR,
        "not": TokenType.NOT,
    }

    def __init__(self, content: str):
        self.content = content
        self.pos = 0
        self.line = 1
        self.column = 1
        self.tokens: list[Token] = []

    def current_char(self) -> str | None:
        """Get current character without consuming it."""
        if self.pos >= len(self.content):
            return None
        return self.content[self.pos]

    def peek(self, offset: int = 1) -> str | None:
        """Look ahead at character at current position + offset."""
        pos = self.pos + offset
        if pos >= len(self.content):
            return None
        return self.content[pos]

    def advance(self) -> str | None:
        """Consume and return current character."""
        char = self.current_char()
        if char is None:
            return None

        self.pos += 1
        if char == "\n":
            self.line += 1
            self.column = 1
        else:
            self.column += 1

        return char

    def advance_checked(self) -> str:
        """Consume and return current character (must not be None)."""
        char = self.advance()
        assert char is not None, "Attempted to advance past end of input"
        return char

    def skip_whitespace(self):
        """Skip whitespace characters."""
        while self.current_char() and self.current_char() in " \t\n\r":
            self.advance()

    def read_while(self, predicate) -> str:
        """Read characters while predicate is true."""
        result: list[str] = []
        while self.current_char() and predicate(self.current_char()):
            result.append(self.advance_checked())
        return "".join(result)

    def read_string(self, quote: str) -> str:
        """Read a quoted string."""
        result: list[str] = []
        self.advance()  # Skip opening quote

        while True:
            char = self.current_char()
            if char is None:
                raise SyntaxError(f"Unterminated string at line {self.line}")

            if char == quote:
                self.advance()  # Skip closing quote
                break

            if char == "\\":
                self.advance()
                next_char = self.current_char()
                if next_char in ('"', "'", "\\"):
                    result.append(self.advance_checked())
                else:
                    result.append("\\")
            else:
                result.append(self.advance_checked())

        return "".join(result)

    def read_number(self) -> str:
        """Read a number (integer or float)."""
        result: list[str] = []

        # Handle negative numbers
        if self.current_char() == "-":
            result.append(self.advance_checked())

        # Read digits
        result.append(self.read_while(lambda c: c.isdigit()))

        # Read decimal part
        peek_char = self.peek()
        if self.current_char() == "." and peek_char is not None and peek_char.isdigit():
            result.append(self.advance_checked())  # .
            result.append(self.read_while(lambda c: c.isdigit()))

        return "".join(result)

    def read_identifier(self) -> str:
        """Read an identifier or keyword."""
        return self.read_while(lambda c: c.isalnum() or c == "_")

    def read_attribute_name(self) -> str:
        """Read an attribute name (allows hyphens, colons for HTML5/framework attributes)."""
        # First character must be letter, underscore, or @ (for framework directives)
        current = self.current_char()
        if not current or not (current.isalpha() or current in ("_", "@", ":")):
            return ""

        # Allow letters, digits, hyphens, colons, underscores, @
        # Supports: data-*, aria-*, hx-*, x-on:click, @click, :bind, etc.
        return self.read_while(lambda c: c.isalnum() or c in ("_", "-", ":", "@", "."))

    def _attribute_name_has_template(self) -> bool:
        """
        Peek ahead to check if the attribute name contains template syntax.
        Returns True if {{ or {% is found before =, >, or whitespace.
        """
        saved_pos = self.pos
        saved_line = self.line
        saved_column = self.column

        try:
            while self.current_char() and self.current_char() not in (
                "=",
                ">",
                " ",
                "\t",
                "\n",
                "\r",
                "/",
            ):
                if self.current_char() == "{" and self.peek() in ("{", "%"):
                    return True
                self.advance()
            return False
        finally:
            # Restore position
            self.pos = saved_pos
            self.line = saved_line
            self.column = saved_column

    def tokenize_dynamic_attribute_name(self) -> str:
        """
        Tokenize a dynamic attribute name that may contain template expressions.
        Supports both simple (entire name is template) and mixed (static + template parts).
        Returns the raw string with template syntax preserved.
        """
        parts = []

        while self.current_char() and self.current_char() not in (
            "=",
            ">",
            " ",
            "\t",
            "\n",
            "\r",
            "/",
        ):
            if self.current_char() == "{" and self.peek() == "{":
                # Template variable {{ ... }}
                parts.append(self._collect_template_variable_in_attr_name())
            elif self.current_char() == "{" and self.peek() == "%":
                # Template tag {% ... %}
                parts.append(self._collect_template_tag_in_attr_name())
            else:
                # Static part - read until next template or end
                static_part: list[str] = []
                while (
                    self.current_char()
                    and self.current_char()
                    not in ("=", ">", " ", "\t", "\n", "\r", "/")
                    and self.current_char() != "{"
                ):
                    static_part.append(self.advance_checked())
                if static_part:
                    parts.append("".join(static_part))

        if not parts:
            raise SyntaxError(f"Empty dynamic attribute name at line {self.line}")

        return "".join(parts)

    def _collect_template_variable_in_attr_name(self) -> str:
        """Collect a template variable {{ ... }} in attribute name. No quote restrictions."""
        result: list[str] = []
        result.append(self.advance_checked())  # {
        result.append(self.advance_checked())  # {

        depth = 0
        while self.current_char():
            char = self.current_char()

            # Track nesting depth for inner {{}}
            if char == "{" and self.peek() == "{":
                depth += 1
                result.append(self.advance_checked())
                result.append(self.advance_checked())
                continue

            # Check for closing }}
            if char == "}" and self.peek() == "}":
                result.append(self.advance_checked())  # }
                result.append(self.advance_checked())  # }
                if depth == 0:
                    return "".join(result)
                depth -= 1
                continue

            result.append(self.advance_checked())

        raise SyntaxError(
            f"Unclosed template variable in attribute name at line {self.line}"
        )

    def _collect_template_tag_in_attr_name(self) -> str:
        """Collect a template tag {% ... %} in attribute name. No quote restrictions."""
        result: list[str] = []
        result.append(self.advance_checked())  # {
        result.append(self.advance_checked())  # %

        while self.current_char():
            char = self.current_char()

            # Check for closing %}
            if char == "%" and self.peek() == "}":
                result.append(self.advance_checked())  # %
                result.append(self.advance_checked())  # }
                return "".join(result)

            result.append(self.advance_checked())

        raise SyntaxError(
            f"Unclosed template tag in attribute name at line {self.line}"
        )

    def add_token(self, token_type: TokenType, value: str = ""):
        """Add a token to the token list."""
        self.tokens.append(Token(token_type, value, self.line, self.column))

    def tokenize(self) -> list[Token]:
        """Tokenize the entire template."""
        while self.pos < len(self.content):
            self.tokenize_text_mode()

        self.add_token(TokenType.EOF)
        return self.tokens

    def tokenize_text_mode(self):
        """Tokenize in text mode (reading HTML and plain text)."""
        start_line = self.line
        start_col = self.column

        # Check for template syntax
        char = self.current_char()
        next_char = self.peek()

        # Template variable: {{
        if char == "{" and next_char == "{":
            self.advance()  # {
            self.advance()  # {
            self.add_token(TokenType.TEMPLATE_VAR_START, "{{")
            self.tokenize_var_mode()
            return

        # Template tag: {%
        if char == "{" and next_char == "%":
            self.advance()  # {
            self.advance()  # %
            self.add_token(TokenType.TEMPLATE_TAG_START, "{%")
            self.tokenize_tag_mode()
            return

        # Template comment: {#
        if char == "{" and next_char == "#":
            self.advance()  # {
            self.advance()  # #
            self.add_token(TokenType.TEMPLATE_COMMENT_START, "{#")
            self.tokenize_comment_mode()
            return

        # HTML tag: <
        if char == "<":
            # Check for DOCTYPE, HTML comment, or CDATA
            if self.peek() == "!":
                peek2 = self.peek(2) if self.pos + 2 < len(self.content) else None
                peek3 = self.peek(3) if self.pos + 3 < len(self.content) else None

                # HTML comment: <!--
                if peek2 == "-" and peek3 == "-":
                    self.tokenize_html_comment()
                    return

                # DOCTYPE: <!DOCTYPE
                if self.content[self.pos : self.pos + 9].upper() == "<!DOCTYPE":
                    self.tokenize_doctype()
                    return

                # CDATA: <![CDATA[
                if self.content[self.pos : self.pos + 9] == "<![CDATA[":
                    self.tokenize_cdata()
                    return

            self.tokenize_html_tag()
            return

        # Plain text
        text = []
        while True:
            char = self.current_char()
            if char is None:
                break

            # Check for start of template or HTML syntax
            next_char = self.peek()
            if char == "<":
                break
            if char == "{" and next_char in ("{", "%", "#"):
                break

            text.append(self.advance())

        if text:
            self.tokens.append(
                Token(TokenType.TEXT, "".join(text), start_line, start_col)
            )

    def tokenize_html_tag(self):
        """Tokenize an HTML tag."""
        start_line = self.line
        start_col = self.column

        self.advance()  # <

        # Check for closing tag
        is_closing = self.current_char() == "/"
        if is_closing:
            self.advance()  # /

        # Read tag name
        tag_name = self.read_identifier()

        if not tag_name:
            raise SyntaxError(f"Expected tag name at line {self.line}")

        # Read attributes (for opening tags)
        attributes = []
        is_self_closing = False

        while True:
            self.skip_whitespace()

            char = self.current_char()
            if char is None:
                raise SyntaxError(f"Unterminated HTML tag at line {self.line}")

            # Self-closing: />
            if char == "/" and self.peek() == ">":
                is_self_closing = True
                self.advance()  # /
                self.advance()  # >
                break

            # End of tag: >
            if char == ">":
                self.advance()
                break

            # Read attribute name (supports hyphens for HTML5 attributes and template syntax)
            # Check if attribute name contains any template syntax (scan ahead)
            if self._attribute_name_has_template():
                # Dynamic attribute name - collect the entire name with mixed parts
                attr_name = self.tokenize_dynamic_attribute_name()
                attributes.append(("name_dynamic", attr_name))
            else:
                # Static attribute name
                attr_name = self.read_attribute_name()
                if not attr_name:
                    raise SyntaxError(f"Expected attribute name at line {self.line}")
                attributes.append(("name", attr_name))

            self.skip_whitespace()

            # Check for = (attribute value)
            if self.current_char() == "=":
                self.advance()  # =
                self.skip_whitespace()

                # Read attribute value
                if self.current_char() in ('"', "'"):
                    quote = self.current_char()
                    # Tokenize attribute value (may contain templates)
                    attr_value = self.tokenize_attribute_value(quote)
                    attributes.append(("value", attr_value))
                else:
                    # Unquoted attribute value
                    attr_value = self.read_while(lambda c: c not in " \t\n\r>/")
                    attributes.append(("value", attr_value))

        # Create appropriate token
        if is_closing:
            self.tokens.append(
                Token(TokenType.HTML_CLOSE_TAG, tag_name, start_line, start_col)
            )
        elif is_self_closing:
            self.tokens.append(
                Token(TokenType.HTML_SELF_CLOSE, tag_name, start_line, start_col)
            )
            for attr_type, attr_val in attributes:
                # Determine token type based on attribute type
                if attr_type == "name":
                    token_type = TokenType.ATTR_NAME
                elif attr_type == "name_dynamic":
                    token_type = TokenType.ATTR_NAME_DYNAMIC
                else:  # 'value'
                    token_type = TokenType.ATTR_VALUE
                self.tokens.append(Token(token_type, attr_val, start_line, start_col))
        else:
            self.tokens.append(
                Token(TokenType.HTML_OPEN_TAG, tag_name, start_line, start_col)
            )
            for attr_type, attr_val in attributes:
                # Determine token type based on attribute type
                if attr_type == "name":
                    token_type = TokenType.ATTR_NAME
                elif attr_type == "name_dynamic":
                    token_type = TokenType.ATTR_NAME_DYNAMIC
                else:  # 'value'
                    token_type = TokenType.ATTR_VALUE
                self.tokens.append(Token(token_type, attr_val, start_line, start_col))

    def tokenize_attribute_value(self, opening_quote: str) -> str:
        """
        Tokenize an attribute value that may contain template syntax.

        Allows templates inside attributes with opposite quote type rule:
        - Double-quoted attributes can use single quotes in templates
        - Single-quoted attributes can use double quotes in templates

        Returns the attribute value as a string.
        """
        self.advance()  # Skip opening quote

        # Store which quote type is forbidden inside templates
        forbidden_quote = opening_quote

        value_buffer: list[str] = []

        while True:
            char = self.current_char()

            if char is None:
                raise SyntaxError(f"Unterminated attribute value at line {self.line}")

            # Check for closing quote
            if char == opening_quote:
                # Return the complete value
                self.advance()  # Skip closing quote
                return "".join(value_buffer)

            # Check for template variable: {{
            if char == "{" and self.peek() == "{":
                value_buffer.append(char)
                self.advance()  # {
                value_buffer.append(self.advance_checked())  # {

                # Validate and collect the variable content
                self._collect_template_var_in_attr(value_buffer, forbidden_quote)
                continue

            # Check for template tag: {%
            if char == "{" and self.peek() == "%":
                value_buffer.append(char)
                self.advance()  # {
                value_buffer.append(self.advance_checked())  # %

                # Validate and collect the tag content
                self._collect_template_tag_in_attr(value_buffer, forbidden_quote)
                continue

            # Regular character
            value_buffer.append(self.advance_checked())

    def _collect_template_var_in_attr(self, buffer: list, forbidden_quote: str):
        """Collect template variable content in attribute, checking quote rules."""
        while True:
            char = self.current_char()

            if char is None:
                raise SyntaxError(
                    f"Unterminated variable in attribute at line {self.line}"
                )

            # Check for forbidden quote
            if char == forbidden_quote:
                quote_type = "single" if forbidden_quote == '"' else "double"
                raise SyntaxError(
                    f"Line {self.line}: Cannot use {forbidden_quote} quotes inside template-in-attribute. "
                    f"Use {quote_type} quotes instead."
                )

            # Check for closing }}
            if char == "}" and self.peek() == "}":
                buffer.append(self.advance())  # }
                buffer.append(self.advance())  # }
                return

            buffer.append(self.advance())

    def _collect_template_tag_in_attr(self, buffer: list, forbidden_quote: str):
        """Collect template tag content in attribute, checking quote rules."""
        while True:
            char = self.current_char()

            if char is None:
                raise SyntaxError(
                    f"Unterminated template tag in attribute at line {self.line}"
                )

            # Check for forbidden quote
            if char == forbidden_quote:
                quote_type = "single" if forbidden_quote == '"' else "double"
                raise SyntaxError(
                    f"Line {self.line}: Cannot use {forbidden_quote} quotes inside template-in-attribute. "
                    f"Use {quote_type} quotes instead."
                )

            # Check for closing %}
            if char == "%" and self.peek() == "}":
                buffer.append(self.advance())  # %
                buffer.append(self.advance())  # }
                return

            buffer.append(self.advance())

    def tokenize_doctype(self):
        """Tokenize a DOCTYPE declaration."""
        start_line = self.line
        start_col = self.column

        # Read until >
        doctype = []
        while self.current_char() and self.current_char() != ">":
            doctype.append(self.advance())

        if self.current_char() == ">":
            doctype.append(self.advance())  # >
        else:
            raise SyntaxError(f"Unterminated DOCTYPE at line {self.line}")

        self.tokens.append(
            Token(TokenType.DOCTYPE, "".join(doctype), start_line, start_col)
        )

    def tokenize_html_comment(self):
        """Tokenize an HTML comment."""
        start_line = self.line
        start_col = self.column

        # Skip <!--
        self.advance()  # <
        self.advance()  # !
        self.advance()  # -
        self.advance()  # -

        comment = []
        while True:
            char = self.current_char()
            if char is None:
                raise SyntaxError(f"Unterminated HTML comment at line {self.line}")

            # Check for -->
            if char == "-" and self.peek() == "-" and self.peek(2) == ">":
                self.advance()  # -
                self.advance()  # -
                self.advance()  # >
                break

            comment.append(self.advance())

        self.tokens.append(
            Token(TokenType.HTML_COMMENT, "".join(comment), start_line, start_col)
        )

    def tokenize_cdata(self):
        """Tokenize a CDATA section."""
        start_line = self.line
        start_col = self.column

        # Skip <![CDATA[
        for _ in range(9):
            self.advance()

        cdata = []
        while True:
            char = self.current_char()
            if char is None:
                raise SyntaxError(f"Unterminated CDATA section at line {self.line}")

            # Check for ]]>
            if char == "]" and self.peek() == "]" and self.peek(2) == ">":
                self.advance()  # ]
                self.advance()  # ]
                self.advance()  # >
                break

            cdata.append(self.advance())

        self.tokens.append(
            Token(TokenType.CDATA, "".join(cdata), start_line, start_col)
        )

    def tokenize_var_mode(self):
        """Tokenize inside {{ ... }}."""
        while True:
            self.skip_whitespace()

            char = self.current_char()
            if char is None:
                raise SyntaxError(f"Unterminated variable at line {self.line}")

            # Check for closing }}
            if char == "}" and self.peek() == "}":
                self.advance()  # }
                self.advance()  # }
                self.add_token(TokenType.TEMPLATE_VAR_END, "}}")
                return

            self.tokenize_expression()

    def tokenize_tag_mode(self):
        """Tokenize inside {% ... %}."""
        # Check if this is a raw content tag (trans, blocktrans, etc.)
        # These tags need their content collected as-is, not tokenized as expressions
        saved_pos = self.pos
        saved_line = self.line
        saved_column = self.column

        self.skip_whitespace()

        # Peek at first identifier to see if it's a raw content tag
        if self.current_char() and (
            self.current_char().isalpha() or self.current_char() == "_"
        ):
            tag_name = self.read_identifier()

            # Known tags that contain raw content (not parsed as expressions)
            RAW_CONTENT_TAGS = {"trans", "blocktrans"}

            if tag_name in RAW_CONTENT_TAGS:
                # Emit the tag name as an identifier
                self.tokens.append(
                    Token(TokenType.IDENTIFIER, tag_name, saved_line, saved_column)
                )

                # Collect everything else as raw text until %}
                content = []
                while True:
                    char = self.current_char()
                    if char is None:
                        raise SyntaxError(
                            f"Unterminated template tag at line {self.line}"
                        )

                    # Check for closing %}
                    if char == "%" and self.peek() == "}":
                        break

                    content.append(self.advance())

                # Emit collected content as text if non-empty
                raw_content = "".join(content)
                if raw_content:
                    self.tokens.append(
                        Token(TokenType.TEXT, raw_content, self.line, self.column)
                    )

                # Emit closing %}
                self.advance()  # %
                self.advance()  # }
                self.add_token(TokenType.TEMPLATE_TAG_END, "%}")
                return

        # Not a raw content tag - restore position and do normal tokenization
        self.pos = saved_pos
        self.line = saved_line
        self.column = saved_column

        # Normal tokenization for template tags
        while True:
            self.skip_whitespace()

            char = self.current_char()
            if char is None:
                raise SyntaxError(f"Unterminated template tag at line {self.line}")

            # Check for closing %}
            if char == "%" and self.peek() == "}":
                self.advance()  # %
                self.advance()  # }
                self.add_token(TokenType.TEMPLATE_TAG_END, "%}")
                return

            self.tokenize_expression()

    def tokenize_comment_mode(self):
        """Tokenize inside {# ... #}."""
        text = []

        while True:
            char = self.current_char()
            if char is None:
                raise SyntaxError(f"Unterminated comment at line {self.line}")

            # Check for closing #}
            if char == "#" and self.peek() == "}":
                self.advance()  # #
                self.advance()  # }
                self.tokens.append(
                    Token(TokenType.TEXT, "".join(text), self.line, self.column)
                )
                self.add_token(TokenType.TEMPLATE_COMMENT_END, "#}")
                return

            text.append(self.advance())

    def tokenize_expression(self):
        """Tokenize an expression (inside template tags or variables)."""
        start_line = self.line
        start_col = self.column

        char = self.current_char()

        # String literal
        if char in ('"', "'"):
            value = self.read_string(char)
            self.tokens.append(Token(TokenType.STRING, value, start_line, start_col))
            return

        # Number
        if char.isdigit() or (char == "-" and self.peek() and self.peek().isdigit()):
            value = self.read_number()
            self.tokens.append(Token(TokenType.NUMBER, value, start_line, start_col))
            return

        # Identifier or keyword
        if char.isalpha() or char == "_":
            value = self.read_identifier()
            token_type = self.KEYWORDS.get(value, TokenType.IDENTIFIER)
            self.tokens.append(Token(token_type, value, start_line, start_col))
            return

        # Operators and symbols
        if char == "|":
            self.advance()
            self.add_token(TokenType.PIPE, "|")
        elif char == ":":
            self.advance()
            self.add_token(TokenType.COLON, ":")
        elif char == ",":
            self.advance()
            self.add_token(TokenType.COMMA, ",")
        elif char == ".":
            # Save position before advancing for accurate column tracking
            dot_col = self.column
            dot_line = self.line
            self.advance()
            self.tokens.append(Token(TokenType.DOT, ".", dot_line, dot_col))
        elif char == "(":
            self.advance()
            self.add_token(TokenType.LPAREN, "(")
        elif char == ")":
            self.advance()
            self.add_token(TokenType.RPAREN, ")")
        elif char == "[":
            self.advance()
            self.add_token(TokenType.LBRACKET, "[")
        elif char == "]":
            self.advance()
            self.add_token(TokenType.RBRACKET, "]")
        elif char == "=" and self.peek() == "=":
            self.advance()
            self.advance()
            self.add_token(TokenType.EQ, "==")
        elif char == "!" and self.peek() == "=":
            self.advance()
            self.advance()
            self.add_token(TokenType.NE, "!=")
        elif char == "<" and self.peek() == "=":
            self.advance()
            self.advance()
            self.add_token(TokenType.LE, "<=")
        elif char == ">" and self.peek() == "=":
            self.advance()
            self.advance()
            self.add_token(TokenType.GE, ">=")
        elif char == "<":
            self.advance()
            self.add_token(TokenType.LT, "<")
        elif char == ">":
            self.advance()
            self.add_token(TokenType.GT, ">")
        elif char == "=":
            self.advance()
            self.add_token(TokenType.EQUALS, "=")
        else:
            raise SyntaxError(
                f"Unexpected character '{char}' at line {self.line}, column {self.column}"
            )


def tokenize(content: str) -> list[Token]:
    """Convenience function to tokenize a template."""
    lexer = Lexer(content)
    return lexer.tokenize()


if __name__ == "__main__":
    # Test the lexer
    template = """
    <div class="container">
        {% if user %}
            <p>Hello {{ user.name|upper }}!</p>
        {% endif %}
    </div>
    """

    tokens = tokenize(template)
    for token in tokens:
        print(token)
