"""
Expression parsing for RDTL templates.

Handles Django variable expressions, filters, and filter arguments.
Extracted from main Parser to improve modularity and maintainability.
"""

from rdtl import ast_nodes
from rdtl.lexer import TokenType


class ExpressionParser:
    """Specialized parser for Django template expressions and filters.

    This parser handles:
    - Variable expressions with dot-notation lookups
    - Literal values (strings, numbers, booleans)
    - Template filters with arguments
    - Filter chaining

    The ExpressionParser works in conjunction with the main Parser,
    accessing its token stream through delegation.
    """

    def __init__(self, parser):
        """Initialize with reference to main parser.

        Args:
            parser: Main Parser instance for token access.
        """
        self.parser = parser

    def parse_expression(self) -> ast_nodes.Expression | ast_nodes.Literal:
        """Parse variable expressions with Django's dot-notation lookups or literal values.

        Django templates use a unique lookup syntax where dots perform multiple types
        of lookups in order: dictionary key, attribute, list index. This parser
        enforces Django's restrictions:

        Supported:
            - Literals: 42, 3.14, "string", True
            - Simple variables: user, items, data
            - Dot lookups: user.name, items.0, obj.attr.nested
            - Keywords as attributes: obj.as, obj.if, obj.for

        NOT Supported (Django restriction):
            - Bracket notation: user['key'], items[0]
            - Spaces in lookups: user. name, user .name, user . name
            - Method calls: user.get_name()

        Space Restrictions:
            Django requires no spaces around dots in lookups. This parser validates
            token positions to reject invalid spacing:
            - {{ user.name }} ✓
            - {{ user .name }} ✗
            - {{ user. name }} ✗

        Keyword Handling:
            Django allows Python/template keywords as attribute names since they're
            used as strings for lookups: {{ obj.as }}, {{ obj.if }}, {{ obj.for }}.
            See is_identifier_like() for the full list.

        Returns:
            Expression: For variable lookups with base and optional attribute chain.
            Literal: For numbers, strings, and booleans.

        Raises:
            ParseError: For invalid spacing, bracket syntax, or unknown tokens.

        Examples:
            user → Expression(base='user', lookups=[])
            user.name → Expression(base='user', lookups=[Lookup('attribute', 'name')])
            items.0 → Expression(base='items', lookups=[Lookup('attribute', '0')])
            42 → Literal(value=42, type='number')
        """
        # Handle literals
        if self.parser.match(TokenType.STRING):
            token = self.parser.advance()
            return ast_nodes.Literal(value=token.value, type="string")

        if self.parser.match(TokenType.NUMBER):
            token = self.parser.advance()
            # Convert to int or float
            value = float(token.value) if "." in token.value else int(token.value)
            return ast_nodes.Literal(value=value, type="number")

        # Variable expression
        if not self.parser.is_identifier_like():
            from rdtl.parser import ParseError  # noqa: PLC0415 (avoid circular import)

            raise ParseError(
                f"Expected expression at line {self.parser.current().line}, "
                f"column {self.parser.current().column}"
            )

        base_token = self.parser.advance()
        base = base_token.value

        # Parse lookups (attribute.attr or item.0)
        lookups: list[ast_nodes.Lookup] = []

        while self.parser.match(TokenType.DOT):
            dot_token = self.parser.current()

            # Check for space before dot (user .name)
            if base_token.column + len(str(base_token.value)) < dot_token.column:
                from rdtl.parser import (  # noqa: PLC0415 (avoid circular import)
                    ParseError,
                )

                raise ParseError(
                    f"No spaces allowed before '.' in variable lookup at "
                    f"line {dot_token.line}, column {dot_token.column}"
                )

            self.parser.advance()  # consume DOT

            # Check for space after dot (user. name)
            next_token = self.parser.current()
            if dot_token.column + 1 < next_token.column:
                from rdtl.parser import (  # noqa: PLC0415 (avoid circular import)
                    ParseError,
                )

                raise ParseError(
                    f"No spaces allowed after '.' in variable lookup at "
                    f"line {next_token.line}, column {next_token.column}"
                )

            # Parse the lookup part
            if self.parser.match(TokenType.NUMBER):
                # Numeric index: items.0
                # Django treats numeric lookups as attributes (string-based lookup)
                num_token = self.parser.advance()
                lookups.append(
                    ast_nodes.Lookup(type="attribute", value=num_token.value)
                )
                base_token = num_token
            elif self.parser.is_identifier_like():
                # Attribute: user.name
                attr_token = self.parser.advance()
                lookups.append(
                    ast_nodes.Lookup(type="attribute", value=attr_token.value)
                )
                base_token = attr_token
            else:
                from rdtl.parser import (  # noqa: PLC0415 (avoid circular import)
                    ParseError,
                )

                raise ParseError(
                    f"Expected attribute or index after '.' at "
                    f"line {next_token.line}, column {next_token.column}"
                )

        return ast_nodes.Expression(base=base, lookups=lookups)

    def parse_expression_with_filters(
        self,
    ) -> ast_nodes.Expression | ast_nodes.Literal | ast_nodes.FilteredExpression:
        """Parse an expression optionally followed by filters.

        This is used in contexts where filters are allowed but not inside {{ }}.
        For example: {% if value|length > 0 %}

        Returns:
            Expression, Literal, or FilteredExpression depending on filters.
        """
        expr = self.parse_expression()

        # Check for filters
        filters = []
        while self.parser.match(TokenType.PIPE):
            self.parser.advance()  # consume |
            filters.append(self.parse_filter())

        if filters:
            return ast_nodes.FilteredExpression(expression=expr, filters=filters)
        return expr

    def parse_filter(self) -> ast_nodes.Filter:
        """Parse Django template filters with optional arguments.

        Syntax:
            |filter_name
            |filter_name:arg
            |filter_name:arg1,arg2,arg3

        Filters:
            Filters transform variable values during template rendering.
            They follow the pipe (|) symbol and can take arguments separated
            by colons and commas.

        Filter Name:
            Must be a valid identifier matching a registered filter function:
            - Built-in: upper, lower, title, length, date, truncatewords, etc.
            - Custom: Registered via template library loading

        Arguments:
            Filters can take zero or more arguments:
            - No args: {{ value|upper }} - Just the filter name
            - One arg: {{ text|truncatewords:10 }} - Colon separates arg
            - Multiple args: {{ text|slice:1,3 }} - Comma separates args

        Argument Types:
            Filter arguments can be:
            - Strings: |default:"no value"
            - Numbers: |truncatewords:30
            - Identifiers: |default:fallback_var (variable reference)
            - Booleans: Not commonly used in Django filters

        Chaining:
            Multiple filters can be chained; each is parsed separately:
            {{ text|lower|truncatewords:5 }}
            Parsed as: Variable with filters [lower, truncatewords(5)]

        Common Examples:
            |upper - Uppercase transformation
            |lower - Lowercase transformation
            |title - Title case transformation
            |length - Get length of sequence
            |default:"N/A" - Default value if variable is falsy
            |truncatewords:10 - Truncate to 10 words
            |date:"Y-m-d" - Format date
            |join:", " - Join list with separator

        Returns:
            Filter AST node with name and optional args list.

        Raises:
            ParseError: If filter syntax is malformed.

        Examples:
            {{ value|upper }}
            → Filter(name='upper', args=[])

            {{ text|truncatewords:30 }}
            → Filter(name='truncatewords', args=[30])

            {{ items|slice:1,3 }}
            → Filter(name='slice', args=[1, 3])
        """
        name_token = self.parser.expect(TokenType.IDENTIFIER)
        name = name_token.value

        args: list[
            str | int | float | bool | ast_nodes.Expression | ast_nodes.Literal
        ] = []
        if self.parser.match(TokenType.COLON):
            self.parser.advance()  # :

            # Parse first argument
            args.append(self.parse_filter_arg())

            # Parse additional arguments
            while self.parser.match(TokenType.COMMA):
                self.parser.advance()  # ,
                args.append(self.parse_filter_arg())

        return ast_nodes.Filter(name=name, args=args)

    def parse_filter_arg(
        self,
    ) -> str | int | float | ast_nodes.Expression | ast_nodes.Literal:
        """Parse individual filter arguments (strings, numbers, or expressions).

        Filter arguments can be:
        1. String literals: "value" or 'value'
        2. Numeric literals: 42 or 3.14
        3. Variable expressions: variable names with optional dot lookups

        String Arguments:
            Quoted strings are used for literal values:
            |default:"N/A" - String literal "N/A"
            |date:"Y-m-d" - Format string "Y-m-d"

        Numeric Arguments:
            Numbers specify counts, indices, or sizes:
            |truncatewords:10 - Integer 10
            |slice:1,5 - Integers 1 and 5
            |pluralize:2.5 - Float 2.5 (less common)

        Expression Arguments:
            Expressions reference variables with optional attribute lookups:
            |default:fallback_var - Use value of fallback_var
            |join:separator - Use value of separator variable
            |get_item:property.name - Use value of property.name

        Type Coercion:
            - Strings remain as strings
            - Numbers are parsed as int or float based on decimal point
            - Expressions are returned as Expression AST nodes

        Returns:
            String (for string literals), int/float (for numeric literals),
            or Expression (for variable references with optional lookups).

        Raises:
            ParseError: If argument token is not STRING, NUMBER, or IDENTIFIER.

        Examples:
            "N/A" → "N/A" (string)
            10 → 10 (int)
            3.14 → 3.14 (float)
            my_var → Expression(base='my_var', lookups=[])
            obj.attr → Expression(base='obj', lookups=[Lookup('attribute', 'attr')])
        """
        if self.parser.match(TokenType.STRING):
            return self.parser.advance().value
        elif self.parser.match(TokenType.NUMBER):
            value = self.parser.advance().value
            return float(value) if "." in value else int(value)
        elif self.parser.is_identifier_like():
            # Parse as a full expression to support dot lookups like property.name
            return self.parse_expression()
        else:
            from rdtl.parser import ParseError  # noqa: PLC0415 (avoid circular import)

            raise ParseError(
                f"Expected filter argument at line {self.parser.current().line}"
            )
