"""
Template renderer for RDTL.

Evaluates the AST and produces HTML output.
"""

from typing import Any

from rdtl.ast_nodes import *


class RenderContext:
    """
    Rendering context holding variables and state.
    """

    def __init__(self, context: dict[str, Any] | None = None):
        self.stack = [context or {}]

    def push(self, new_context: dict[str, Any] | None = None):
        """Push a new context frame."""
        self.stack.append(new_context or {})

    def pop(self):
        """Pop the topmost context frame."""
        if len(self.stack) > 1:
            self.stack.pop()

    def get(self, name: str, default=None):
        """Get a variable from the context."""
        # Search from innermost to outermost
        for frame in reversed(self.stack):
            if name in frame:
                return frame[name]
        return default

    def set(self, name: str, value: Any):
        """Set a variable in the current context."""
        self.stack[-1][name] = value


class Renderer(ASTVisitor):
    """
    Renders an RDTL template AST to HTML.

    Usage:
        renderer = Renderer(context={'user': {'name': 'Alice'}})
        output = renderer.render(ast)
    """

    def __init__(self, context: dict[str, Any] | None = None):
        self.context = RenderContext(context)
        self.output = []

        # Built-in filters
        self.filters = {
            "upper": lambda x: str(x).upper(),
            "lower": lambda x: str(x).lower(),
            "title": lambda x: str(x).title(),
            "length": lambda x: len(x) if hasattr(x, "__len__") else 0,
            "default": lambda x, d="": x if x else d,
            "truncatewords": self._filter_truncatewords,
            "date": self._filter_date,
        }

    def render(self, node: ASTNode) -> str:
        """Render a template AST to HTML string."""
        self.output = []
        self.visit(node)
        return "".join(self.output)

    def write(self, text: str):
        """Append text to output."""
        self.output.append(text)

    # ========================================================================
    # Visitor methods
    # ========================================================================

    def visit_Document(self, node: Document):
        """Render the document."""
        for child in node.children:
            self.visit(child)

    def visit_HTMLElement(self, node: HTMLElement):
        """Render an HTML element."""
        # Opening tag
        self.write(f"<{node.tag_name}")

        # Attributes
        for attr in node.attributes:
            if attr.value is not None:
                # Escape attribute values
                escaped_value = self._escape_attr(attr.value)
                self.write(f' {attr.name}="{escaped_value}"')
            else:
                # Boolean attribute
                self.write(f" {attr.name}")

        self.write(">")

        # Children
        for child in node.children:
            self.visit(child)

        # Closing tag
        self.write(f"</{node.tag_name}>")

    def visit_VoidElement(self, node: VoidElement):
        """Render a void HTML element."""
        self.write(f"<{node.tag_name}")

        for attr in node.attributes:
            if attr.value is not None:
                escaped_value = self._escape_attr(attr.value)
                self.write(f' {attr.name}="{escaped_value}"')
            else:
                self.write(f" {attr.name}")

        self.write(">")

    def visit_TextNode(self, node: TextNode):
        """Render plain text."""
        self.write(node.content)

    def visit_Variable(self, node: Variable):
        """Render a template variable."""
        # Evaluate the expression
        value = self._eval_expression(node.expression)

        # Apply filters
        for filter_node in node.filters:
            value = self._apply_filter(value, filter_node)

        # Convert to string and escape
        self.write(self._escape_html(str(value)))

    def visit_IfBlock(self, node: IfBlock):
        """Render an if/elif/else block."""
        # Evaluate if condition
        if self._eval_condition(node.if_condition):
            for child in node.if_children:
                self.visit(child)
            return

        # Try elif branches
        for condition, children in node.elif_branches:
            if self._eval_condition(condition):
                for child in children:
                    self.visit(child)
                return

        # Else branch
        if node.else_children is not None:
            for child in node.else_children:
                self.visit(child)

    def visit_ForBlock(self, node: ForBlock):
        """Render a for loop."""
        # Evaluate the iterable
        iterable = self._eval_expression(node.iterable)

        # Convert to list if needed
        if not hasattr(iterable, "__iter__"):
            iterable = []

        items = list(iterable)

        # If empty, render empty block
        if not items and node.empty_children is not None:
            for child in node.empty_children:
                self.visit(child)
            return

        # Render loop
        for item in items:
            # Push new context with loop variable
            self.context.push({node.loop_var: item})

            # Render children
            for child in node.children:
                self.visit(child)

            # Pop context
            self.context.pop()

    def visit_BlockTag(self, node: BlockTag):
        """Render a block tag (simplified - no inheritance)."""
        # For now, just render the children
        for child in node.children:
            self.visit(child)

    def visit_WithBlock(self, node: WithBlock):
        """Render a with block."""
        # Create new context with assignments
        new_context = {}
        for var_name, expr in node.assignments:
            new_context[var_name] = self._eval_expression(expr)

        self.context.push(new_context)

        # Render children
        for child in node.children:
            self.visit(child)

        self.context.pop()

    def visit_IncludeTag(self, node: IncludeTag):
        """Render an include tag."""
        # Simplified: just output a comment
        self.write(f"<!-- include: {node.template_name} -->")

    def visit_ExtendsTag(self, node: ExtendsTag):
        """Render an extends tag."""
        # Simplified: just output a comment
        self.write(f"<!-- extends: {node.parent_template} -->")

    def visit_LoadTag(self, node: LoadTag):
        """Render a load tag."""
        # Simplified: no output (load tags don't produce HTML)
        pass

    def visit_CsrfTokenTag(self, node: CsrfTokenTag):
        """Render a CSRF token tag."""
        # Simplified: output a placeholder
        self.write(
            '<input type="hidden" name="csrfmiddlewaretoken" value="csrf_token_placeholder">'
        )

    def visit_Comment(self, node: Comment):
        """Render a template comment (don't output anything)."""
        # Template comments are not rendered
        pass

    # ========================================================================
    # Expression evaluation
    # ========================================================================

    def _eval_expression(self, expr: Union[Expression, Literal]) -> Any:
        """Evaluate an expression to a value."""
        if isinstance(expr, Literal):
            return expr.value

        if isinstance(expr, Expression):
            # Get base variable
            value = self.context.get(expr.base)

            # Apply lookups
            for lookup in expr.lookups:
                if lookup.type == "attribute":
                    # Attribute access - prioritize dict keys over attributes
                    if isinstance(value, dict) and lookup.value in value:
                        value = value[lookup.value]
                    elif hasattr(value, lookup.value):
                        value = getattr(value, lookup.value)
                    else:
                        value = None
                        break

                elif lookup.type == "index":
                    # Index access
                    try:
                        value = value[lookup.value]
                    except (KeyError, IndexError, TypeError):
                        value = None
                        break

            return value

        return None

    def _eval_condition(self, condition: Condition) -> bool:
        """Evaluate a condition to a boolean."""
        if isinstance(condition, SimpleCondition):
            value = self._eval_expression(condition.expression)
            result = self._is_truthy(value)
            return not result if condition.negated else result

        elif isinstance(condition, Comparison):
            left = self._eval_expression(condition.left)
            right = self._eval_expression(condition.right)

            if condition.operator == "==":
                return left == right
            elif condition.operator == "!=":
                return left != right
            elif condition.operator == "<":
                return left < right
            elif condition.operator == ">":
                return left > right
            elif condition.operator == "<=":
                return left <= right
            elif condition.operator == ">=":
                return left >= right
            elif condition.operator == "in":
                return left in right if right else False

        elif isinstance(condition, BooleanOp):
            if condition.operator == "and":
                return all(self._eval_condition(c) for c in condition.operands)
            elif condition.operator == "or":
                return any(self._eval_condition(c) for c in condition.operands)

        return False

    def _is_truthy(self, value: Any) -> bool:
        """Determine if a value is truthy."""
        if value is None or value is False:
            return False
        if value == 0 or value == "":
            return False
        if hasattr(value, "__len__") and len(value) == 0:
            return False
        return True

    # ========================================================================
    # Filters
    # ========================================================================

    def _apply_filter(self, value: Any, filter_node: Filter) -> Any:
        """Apply a filter to a value."""
        filter_name = filter_node.name

        if filter_name not in self.filters:
            # Unknown filter - just return the value
            return value

        filter_func = self.filters[filter_name]

        # Apply filter with arguments
        if filter_node.args:
            return filter_func(value, *filter_node.args)
        else:
            return filter_func(value)

    def _filter_truncatewords(self, value: str, num_words: int = 30) -> str:
        """Truncate text to a number of words."""
        words = str(value).split()
        if len(words) <= num_words:
            return str(value)
        return " ".join(words[:num_words]) + "..."

    def _filter_date(self, value: Any, format_str: str = "%Y-%m-%d") -> str:
        """Format a date (simplified)."""
        # Simplified: just return string representation
        return str(value)

    # ========================================================================
    # HTML escaping
    # ========================================================================

    def _escape_html(self, text: str) -> str:
        """Escape HTML special characters."""
        return (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#x27;")
        )

    def _escape_attr(self, text: str) -> str:
        """Escape attribute values."""
        return (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
        )


def render(template: str, context: dict[str, Any] | None = None) -> str:
    """
    Convenience function to parse and render a template.

    Args:
        template: RDTL template string
        context: Dictionary of variables for the template

    Returns:
        Rendered HTML string
    """
    from rdtl.parser import parse

    ast = parse(template)
    renderer = Renderer(context)
    return renderer.render(ast)


if __name__ == "__main__":
    # Test the renderer
    template = """
    <div class="container">
        {% if user %}
            <h1>Hello {{ user.name|upper }}!</h1>
            <p>Email: {{ user.email }}</p>

            <h2>Items</h2>
            <ul>
                {% for item in user.items %}
                    <li>{{ item.title }} - {{ item.price }}</li>
                {% empty %}
                    <li>No items found</li>
                {% endfor %}
            </ul>
        {% else %}
            <p>Please log in</p>
        {% endif %}
    </div>
    """

    context = {
        "user": {
            "name": "Alice",
            "email": "alice@example.com",
            "items": [
                {"title": "Book", "price": "$10"},
                {"title": "Pen", "price": "$2"},
            ],
        }
    }

    output = render(template, context)
    print(output)
