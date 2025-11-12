"""
Template tag parsing for RDTL templates.

Handles Django template tags, control flow, and conditions.
Extracted from main Parser to improve modularity and maintainability.
"""

from rdtl import ast_nodes
from rdtl.lexer import TokenType


class TemplateParser:
    """Specialized parser for Django template tags and control structures.

    This parser handles:
    - Template tag dispatching
    - Control flow (if/elif/else, for loops)
    - Block tags (block, with, filter, comment, etc.)
    - Single tags (include, extends, load, url, static, etc.)
    - Condition parsing (comparisons, boolean logic)

    The TemplateParser works in conjunction with the main Parser,
    accessing its token stream and delegating expression parsing.
    """

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

    def __init__(self, parser, expression_parser):
        """Initialize with references to parsers.

        Args:
            parser: Main Parser instance for token access and element parsing.
            expression_parser: ExpressionParser instance for expression parsing.
        """
        self.parser = parser
        self.expression_parser = expression_parser

    def parse_block_body(self, end_tokens: list[TokenType]) -> list[ast_nodes.ASTNode]:
        """Parse the body of a block until we hit an end token."""
        children = []

        while not self.parser.match(TokenType.EOF):
            # Check if we've hit an end token
            if self.parser.match(TokenType.TEMPLATE_TAG_START):
                next_token = self.parser.peek()
                if next_token.type in end_tokens:
                    break

            child = self.parser.parse_element()
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

        if self.parser.match(TokenType.OR):
            operands = [left]
            while self.parser.match(TokenType.OR):
                self.parser.advance()
                operands.append(self.parse_and_condition())
            return ast_nodes.BooleanOp(operator="or", operands=operands)

        return left

    def parse_and_condition(self) -> ast_nodes.Condition:
        """Parse AND conditions."""
        left = self.parse_not_condition()

        if self.parser.match(TokenType.AND):
            operands = [left]
            while self.parser.match(TokenType.AND):
                self.parser.advance()
                operands.append(self.parse_not_condition())
            return ast_nodes.BooleanOp(operator="and", operands=operands)

        return left

    def parse_not_condition(self) -> ast_nodes.Condition:
        """Parse NOT conditions."""
        if self.parser.match(TokenType.NOT):
            self.parser.advance()
            condition = self.parse_primary_condition()
            # If it's already a SimpleCondition, just toggle its negation
            if isinstance(condition, ast_nodes.SimpleCondition):
                return ast_nodes.SimpleCondition(
                    expression=condition.expression, negated=not condition.negated
                )
            return condition

        return self.parse_primary_condition()

    def parse_primary_condition(self) -> ast_nodes.Condition:
        """Parse the primary unit of a condition: comparison or truthiness check."""
        # Parse left side (with optional filters)
        left = self.expression_parser.parse_expression_with_filters()

        # Check for comparison operator
        if self.parser.match(
            TokenType.EQ,
            TokenType.NE,
            TokenType.LT,
            TokenType.GT,
            TokenType.LE,
            TokenType.GE,
        ):
            op_token = self.parser.advance()
            right = self.expression_parser.parse_expression_with_filters()

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
        if self.parser.match(TokenType.IN):
            self.parser.advance()
            right = self.expression_parser.parse_expression_with_filters()
            return ast_nodes.Comparison(left=left, operator="in", right=right)

        # Check for 'is' and 'is not' operators
        if self.parser.match(TokenType.IS):
            self.parser.advance()
            # Check for 'is not'
            if self.parser.match(TokenType.NOT):
                self.parser.advance()
                right = self.expression_parser.parse_expression_with_filters()
                return ast_nodes.Comparison(left=left, operator="is not", right=right)
            # Just 'is'
            right = self.expression_parser.parse_expression_with_filters()
            return ast_nodes.Comparison(left=left, operator="is", right=right)

        # Simple expression (truthy check)
        return ast_nodes.SimpleCondition(expression=left, negated=False)
