"""
Template formatter for RDTL.

Pretty-prints templates with consistent indentation and spacing.
"""

from dataclasses import dataclass
from typing import Optional

from rdtl.ast_nodes import *

# Note: Many visit methods use lazy imports for specific node types.
# This is intentional to avoid circular imports and keep the visitor pattern clean.


@dataclass
class FormatOptions:
    """Configuration options for the formatter."""

    # Indentation
    indent_size: int = 4
    use_tabs: bool = False

    # HTML formatting
    indent_html: bool = True
    max_line_length: int = 100

    # Template tag formatting
    indent_template_blocks: bool = True
    space_in_template_tags: bool = True  # {% if %} vs {%if%}
    space_in_variables: bool = True  # {{ x }} vs {{x}}

    # Newlines
    blank_line_before_block: bool = False
    blank_line_after_block: bool = False
    preserve_blank_lines: bool = True

    # HTML tag formatting
    self_closing_slash: bool = True  # <br /> vs <br>
    quotes: str = "double"  # "double" or "single"

    # Comments
    preserve_comments: bool = True


class Formatter(ASTVisitor):
    """
    Formats RDTL templates with consistent style.

    Usage:
        formatter = Formatter(options)
        formatted = formatter.format(ast)
    """

    def __init__(self, options: Optional[FormatOptions] = None):
        self.options = options or FormatOptions()
        self.output = []
        self.indent_level = 0
        self.needs_indent = True
        self.last_was_block = False

    def format(self, node: ASTNode) -> str:
        """Format an AST to a pretty-printed string."""
        self.output = []
        self.indent_level = 0
        self.needs_indent = True
        self.last_was_block = False

        self.visit(node)

        result = "".join(self.output)

        # Clean up excessive blank lines
        lines = result.split("\n")
        cleaned = []
        blank_count = 0

        for line in lines:
            if line.strip() == "":
                blank_count += 1
                if blank_count <= 1:  # Allow max 1 blank line
                    cleaned.append(line)
            else:
                blank_count = 0
                cleaned.append(line)

        return "\n".join(cleaned)

    def write(self, text: str):
        """Write text to output."""
        if self.needs_indent and text.strip():
            self.output.append(self._get_indent())
            self.needs_indent = False
        self.output.append(text)

    def writeln(self, text: str = ""):
        """Write text followed by newline."""
        if text:
            self.write(text)
        self.output.append("\n")
        self.needs_indent = True

    def _get_indent(self) -> str:
        """Get current indentation string."""
        if self.options.use_tabs:
            return "\t" * self.indent_level
        return " " * (self.indent_level * self.options.indent_size)

    def _increase_indent(self):
        """Increase indentation level."""
        self.indent_level += 1

    def _decrease_indent(self):
        """Decrease indentation level."""
        self.indent_level = max(0, self.indent_level - 1)

    # ========================================================================
    # Visitor methods
    # ========================================================================

    def visit_Document(self, node: Document):
        """Format the document."""
        for i, child in enumerate(node.children):
            # Skip pure whitespace text nodes at document level
            if isinstance(child, TextNode) and not child.content.strip():
                continue

            self.visit(child)

    def visit_HTMLElement(self, node: HTMLElement):
        """Format an HTML element."""
        tag = node.tag_name

        # Opening tag
        self.write(f"<{tag}")

        # Attributes
        for attr in node.attributes:
            self.write(" ")
            self.write(attr.name)
            if attr.value is not None:
                quote = '"' if self.options.quotes == "double" else "'"
                self.write(f"={quote}{attr.value}{quote}")

        self.write(">")

        # Determine if we should format children inline or block
        has_block_children = any(
            isinstance(child, (HTMLElement, IfBlock, ForBlock, BlockTag))
            for child in node.children
        )

        if has_block_children and self.options.indent_html:
            # Block formatting
            self.writeln()
            self._increase_indent()

            for child in node.children:
                self.visit(child)

            self._decrease_indent()
            self.write(f"</{tag}>")
            self.writeln()
        else:
            # Inline formatting
            for child in node.children:
                if isinstance(child, TextNode):
                    self.output.append(child.content)
                else:
                    self.visit(child)

            self.output.append(f"</{tag}>")
            self.writeln()

    def visit_VoidElement(self, node: VoidElement):
        """Format a void element."""
        self.write(f"<{node.tag_name}")

        for attr in node.attributes:
            self.write(" ")
            self.write(attr.name)
            if attr.value is not None:
                quote = '"' if self.options.quotes == "double" else "'"
                self.write(f"={quote}{attr.value}{quote}")

        if self.options.self_closing_slash:
            self.write(" />")
        else:
            self.write(">")

        self.writeln()

    def visit_DocType(self, node):
        """Format a DOCTYPE declaration."""

        self.writeln(node.content)

    def visit_HTMLComment(self, node):
        """Format an HTML comment."""

        self.writeln(f"<!-- {node.content} -->")

    def visit_CDATA(self, node):
        """Format a CDATA section."""

        self.writeln(f"<![CDATA[{node.content}]]>")

    def visit_TextNode(self, node: TextNode):
        """Format text node."""
        # For text nodes inside block elements, write as-is
        # The parent element handles indentation
        content = node.content

        # If it's just whitespace, skip it (parent handles spacing)
        if not content.strip():
            return

        self.write(content)

    def visit_Variable(self, node: Variable):
        """Format a template variable."""
        if self.options.space_in_variables:
            self.write("{{ ")
        else:
            self.write("{{")

        # Write expression
        self.write(str(node.expression))

        # Write filters
        for filter_node in node.filters:
            self.write("|")
            self.write(filter_node.name)
            if filter_node.args:
                self.write(":")
                self.write(
                    ",".join(
                        repr(arg) if isinstance(arg, str) else str(arg)
                        for arg in filter_node.args
                    )
                )

        if self.options.space_in_variables:
            self.write(" }}")
        else:
            self.write("}}")

    def visit_IfBlock(self, node: IfBlock):
        """Format an if block."""
        if self.options.blank_line_before_block and self.last_was_block:
            self.writeln()

        # Opening if
        if self.options.space_in_template_tags:
            self.write("{% if ")
        else:
            self.write("{%if ")

        self.write(self._format_condition(node.if_condition))

        if self.options.space_in_template_tags:
            self.writeln(" %}")
        else:
            self.writeln("%}")

        # If body
        if self.options.indent_template_blocks:
            self._increase_indent()

        for child in node.if_children:
            self.visit(child)

        if self.options.indent_template_blocks:
            self._decrease_indent()

        # Elif branches
        for condition, children in node.elif_branches:
            if self.options.space_in_template_tags:
                self.write("{% elif ")
            else:
                self.write("{%elif ")

            self.write(self._format_condition(condition))

            if self.options.space_in_template_tags:
                self.writeln(" %}")
            else:
                self.writeln("%}")

            if self.options.indent_template_blocks:
                self._increase_indent()

            for child in children:
                self.visit(child)

            if self.options.indent_template_blocks:
                self._decrease_indent()

        # Else branch
        if node.else_children is not None:
            if self.options.space_in_template_tags:
                self.writeln("{% else %}")
            else:
                self.writeln("{%else%}")

            if self.options.indent_template_blocks:
                self._increase_indent()

            for child in node.else_children:
                self.visit(child)

            if self.options.indent_template_blocks:
                self._decrease_indent()

        # Closing endif
        if self.options.space_in_template_tags:
            self.writeln("{% endif %}")
        else:
            self.writeln("{%endif%}")

        if self.options.blank_line_after_block:
            self.writeln()

        self.last_was_block = True

    def visit_ForBlock(self, node: ForBlock):
        """Format a for loop."""
        if self.options.blank_line_before_block and self.last_was_block:
            self.writeln()

        # Format loop variables (supports tuple unpacking)
        loop_vars_str = ", ".join(node.loop_vars)

        # Opening for
        if self.options.space_in_template_tags:
            self.write(f"{{% for {loop_vars_str} in {node.iterable} ")
            self.writeln("%}")
        else:
            self.write(f"{{%for {loop_vars_str} in {node.iterable}")
            self.writeln("%}")

        # Loop body
        if self.options.indent_template_blocks:
            self._increase_indent()

        for child in node.children:
            self.visit(child)

        if self.options.indent_template_blocks:
            self._decrease_indent()

        # Empty clause
        if node.empty_children is not None:
            if self.options.space_in_template_tags:
                self.writeln("{% empty %}")
            else:
                self.writeln("{%empty%}")

            if self.options.indent_template_blocks:
                self._increase_indent()

            for child in node.empty_children:
                self.visit(child)

            if self.options.indent_template_blocks:
                self._decrease_indent()

        # Closing endfor
        if self.options.space_in_template_tags:
            self.writeln("{% endfor %}")
        else:
            self.writeln("{%endfor%}")

        if self.options.blank_line_after_block:
            self.writeln()

        self.last_was_block = True

    def visit_BlockTag(self, node: BlockTag):
        """Format a block tag."""
        if self.options.blank_line_before_block and self.last_was_block:
            self.writeln()

        # Opening block
        if self.options.space_in_template_tags:
            self.writeln(f"{{% block {node.name} %}}")
        else:
            self.writeln(f"{{%block {node.name}%}}")

        # Block body
        if self.options.indent_template_blocks:
            self._increase_indent()

        for child in node.children:
            self.visit(child)

        if self.options.indent_template_blocks:
            self._decrease_indent()

        # Closing endblock
        if self.options.space_in_template_tags:
            self.writeln(f"{{% endblock {node.name} %}}")
        else:
            self.writeln(f"{{%endblock {node.name}%}}")

        if self.options.blank_line_after_block:
            self.writeln()

        self.last_was_block = True

    def visit_WithBlock(self, node: WithBlock):
        """Format a with block."""
        if self.options.space_in_template_tags:
            self.write("{% with ")
        else:
            self.write("{%with ")

        # Write assignments
        assignments = []
        for var_name, expr in node.assignments:
            assignments.append(f"{var_name}={expr}")

        self.write(" ".join(assignments))

        if self.options.space_in_template_tags:
            self.writeln(" %}")
        else:
            self.writeln("%}")

        # Body
        if self.options.indent_template_blocks:
            self._increase_indent()

        for child in node.children:
            self.visit(child)

        if self.options.indent_template_blocks:
            self._decrease_indent()

        # Closing
        if self.options.space_in_template_tags:
            self.writeln("{% endwith %}")
        else:
            self.writeln("{%endwith%}")

        self.last_was_block = True

    def visit_IncludeTag(self, node: IncludeTag):
        """Format an include tag with optional 'with' clause."""
        quote = '"' if self.options.quotes == "double" else "'"

        # Build the tag content
        parts = [f"include {quote}{node.template_name}{quote}"]

        # Add 'with' clause if context variables are present
        if node.context_vars:
            var_assignments = []
            for key, value in node.context_vars.items():
                # Format the value expression (use str() to convert Expression to string)
                value_str = str(value)
                var_assignments.append(f"{key}={value_str}")
            parts.append("with " + " ".join(var_assignments))

        tag_content = " ".join(parts)

        if self.options.space_in_template_tags:
            self.writeln(f"{{% {tag_content} %}}")
        else:
            self.writeln(f"{{%{tag_content}%}}")

    def visit_ExtendsTag(self, node: ExtendsTag):
        """Format an extends tag."""
        quote = '"' if self.options.quotes == "double" else "'"

        if self.options.space_in_template_tags:
            self.writeln(f"{{% extends {quote}{node.parent_template}{quote} %}}")
        else:
            self.writeln(f"{{%extends {quote}{node.parent_template}{quote}%}}")

    def visit_LoadTag(self, node: LoadTag):
        """Format a load tag."""
        libraries = " ".join(node.libraries)
        if self.options.space_in_template_tags:
            self.writeln(f"{{% load {libraries} %}}")
        else:
            self.writeln(f"{{%load {libraries}%}}")

    def visit_UrlTag(self, node):
        """Format a url tag."""
        from rdtl.ast_nodes import Expression, Literal

        def format_arg(arg):
            """Format an argument (string, number, expression, or literal)."""
            if isinstance(arg, str):
                return repr(arg)
            elif isinstance(arg, Expression):
                return str(arg)
            elif isinstance(arg, Literal):
                # For literals, format the value directly
                if arg.type == "string":
                    return repr(arg.value)
                else:
                    return str(arg.value)
            else:
                return str(arg)

        # Build args string
        parts = [repr(node.view_name)]
        parts.extend(format_arg(arg) for arg in node.args)
        parts.extend(f"{k}={format_arg(v)}" for k, v in node.kwargs.items())

        if node.as_var:
            parts.append(f"as {node.as_var}")

        args_str = " ".join(parts)

        if self.options.space_in_template_tags:
            self.writeln(f"{{% url {args_str} %}}")
        else:
            self.writeln(f"{{%url {args_str}%}}")

    def visit_StaticTag(self, node):
        """Format a static tag."""

        path_str = repr(node.path) if isinstance(node.path, str) else node.path

        if self.options.space_in_template_tags:
            if node.as_var:
                self.writeln(f"{{% static {path_str} as {node.as_var} %}}")
            else:
                self.writeln(f"{{% static {path_str} %}}")
        else:
            if node.as_var:
                self.writeln(f"{{%static {path_str} as {node.as_var}%}}")
            else:
                self.writeln(f"{{%static {path_str}%}}")

    def visit_CsrfTokenTag(self, node: CsrfTokenTag):
        """Format a csrf_token tag."""
        if self.options.space_in_template_tags:
            self.writeln("{% csrf_token %}")
        else:
            self.writeln("{%csrf_token%}")

    def visit_CycleTag(self, node):
        """Format a cycle tag."""

        values_str = " ".join(
            repr(v) if isinstance(v, str) else str(v) for v in node.values
        )

        if self.options.space_in_template_tags:
            if node.cycle_name:
                self.writeln(f"{{% cycle {values_str} as {node.cycle_name} %}}")
            else:
                self.writeln(f"{{% cycle {values_str} %}}")
        else:
            if node.cycle_name:
                self.writeln(f"{{%cycle {values_str} as {node.cycle_name}%}}")
            else:
                self.writeln(f"{{%cycle {values_str}%}}")

    def visit_ResetCycleTag(self, node):
        """Format a resetcycle tag."""

        if self.options.space_in_template_tags:
            if node.cycle_name:
                self.writeln(f"{{% resetcycle {node.cycle_name} %}}")
            else:
                self.writeln("{% resetcycle %}")
        else:
            if node.cycle_name:
                self.writeln(f"{{%resetcycle {node.cycle_name}%}}")
            else:
                self.writeln("{%resetcycle%}")

    def visit_DebugTag(self, node):
        """Format a debug tag."""

        if self.options.space_in_template_tags:
            self.writeln("{% debug %}")
        else:
            self.writeln("{%debug%}")

    def visit_LoremTag(self, node):
        """Format a lorem tag."""

        parts = ["lorem"]
        if node.count != 1:
            parts.append(str(node.count))
        if node.method != "w":
            parts.append(node.method)
        if node.random:
            parts.append("random")

        if self.options.space_in_template_tags:
            self.writeln(f'{{% {" ".join(parts)} %}}')
        else:
            self.writeln(f'{{%{" ".join(parts)}%}}')

    def visit_RegroupTag(self, node):
        """Format a regroup tag."""

        if self.options.space_in_template_tags:
            self.writeln(
                f"{{% regroup {node.list_expr} by {node.attribute} as {node.var_name} %}}"
            )
        else:
            self.writeln(
                f"{{%regroup {node.list_expr} by {node.attribute} as {node.var_name}%}}"
            )

    def visit_QueryStringTag(self, node):
        """Format a querystring tag."""

        updates_str = " ".join(f"{k}={v}" for k, v in node.updates.items())

        if self.options.space_in_template_tags:
            self.writeln(f"{{% querystring {updates_str} %}}")
        else:
            self.writeln(f"{{%querystring {updates_str}%}}")

    def visit_SingleTag(self, node):
        """Format a generic single tag."""

        if self.options.space_in_template_tags:
            if node.raw_content:
                self.writeln(f"{{% {node.tag_name} {node.raw_content} %}}")
            else:
                self.writeln(f"{{% {node.tag_name} %}}")
        else:
            if node.raw_content:
                self.writeln(f"{{%{node.tag_name} {node.raw_content}%}}")
            else:
                self.writeln(f"{{%{node.tag_name}%}}")

    def visit_GenericBlockTag(self, node):
        """Format a generic block tag."""

        # Opening tag
        if self.options.space_in_template_tags:
            if node.raw_args:
                self.writeln(f"{{% {node.tag_name} {node.raw_args} %}}")
            else:
                self.writeln(f"{{% {node.tag_name} %}}")
        else:
            if node.raw_args:
                self.writeln(f"{{%{node.tag_name} {node.raw_args}%}}")
            else:
                self.writeln(f"{{%{node.tag_name}%}}")

        # Children
        self._increase_indent()
        for child in node.children:
            self.visit(child)
        self._decrease_indent()

        # Closing tag
        if self.options.space_in_template_tags:
            self.writeln(f"{{% end{node.tag_name} %}}")
        else:
            self.writeln(f"{{%end{node.tag_name}%}}")

    def visit_CommentBlock(self, node):
        """Format a comment block."""

        if self.options.space_in_template_tags:
            self.writeln("{% comment %}")
        else:
            self.writeln("{%comment%}")

        self._increase_indent()
        for child in node.children:
            self.visit(child)
        self._decrease_indent()

        if self.options.space_in_template_tags:
            self.writeln("{% endcomment %}")
        else:
            self.writeln("{%endcomment%}")

    def visit_IfChangedBlock(self, node):
        """Format an ifchanged block."""

        if self.options.space_in_template_tags:
            if node.watch_expressions:
                watch = " ".join(str(e) for e in node.watch_expressions)
                self.writeln(f"{{% ifchanged {watch} %}}")
            else:
                self.writeln("{% ifchanged %}")
        else:
            if node.watch_expressions:
                watch = " ".join(str(e) for e in node.watch_expressions)
                self.writeln(f"{{%ifchanged {watch}%}}")
            else:
                self.writeln("{%ifchanged%}")

        self._increase_indent()
        for child in node.children:
            self.visit(child)
        self._decrease_indent()

        if self.options.space_in_template_tags:
            self.writeln("{% endifchanged %}")
        else:
            self.writeln("{%endifchanged%}")

    def visit_FilterBlock(self, node):
        """Format a filter block."""

        if self.options.space_in_template_tags:
            self.writeln(f"{{% filter {node.filter_name} %}}")
        else:
            self.writeln(f"{{%filter {node.filter_name}%}}")

        self._increase_indent()
        for child in node.children:
            self.visit(child)
        self._decrease_indent()

        if self.options.space_in_template_tags:
            self.writeln("{% endfilter %}")
        else:
            self.writeln("{%endfilter%}")

    def visit_SpacelessBlock(self, node):
        """Format a spaceless block."""

        if self.options.space_in_template_tags:
            self.writeln("{% spaceless %}")
        else:
            self.writeln("{%spaceless%}")

        self._increase_indent()
        for child in node.children:
            self.visit(child)
        self._decrease_indent()

        if self.options.space_in_template_tags:
            self.writeln("{% endspaceless %}")
        else:
            self.writeln("{%endspaceless%}")

    def visit_VerbatimBlock(self, node):
        """Format a verbatim block."""

        if self.options.space_in_template_tags:
            self.writeln("{% verbatim %}")
        else:
            self.writeln("{%verbatim%}")

        # Write raw content without parsing
        self.write(node.content)

        if self.options.space_in_template_tags:
            self.writeln("{% endverbatim %}")
        else:
            self.writeln("{%endverbatim%}")

    def visit_AutoescapeBlock(self, node):
        """Format an autoescape block."""

        if self.options.space_in_template_tags:
            self.writeln(f"{{% autoescape {node.mode} %}}")
        else:
            self.writeln(f"{{%autoescape {node.mode}%}}")

        self._increase_indent()
        for child in node.children:
            self.visit(child)
        self._decrease_indent()

        if self.options.space_in_template_tags:
            self.writeln("{% endautoescape %}")
        else:
            self.writeln("{%endautoescape%}")

    def visit_Comment(self, node: Comment):
        """Format a template comment."""
        if self.options.preserve_comments:
            self.writeln(f"{{# {node.content} #}}")

    def _format_condition(self, condition: Condition) -> str:
        """Format a condition to string."""
        if isinstance(condition, SimpleCondition):
            not_str = "not " if condition.negated else ""
            return f"{not_str}{condition.expression}"

        elif isinstance(condition, Comparison):
            return f"{condition.left} {condition.operator} {condition.right}"

        elif isinstance(condition, BooleanOp):
            parts = [self._format_condition(c) for c in condition.operands]
            return f" {condition.operator} ".join(parts)

        return str(condition)


def format_template(template: str, options: Optional[FormatOptions] = None) -> str:
    """
    Format an RDTL template string.

    Args:
        template: RDTL template string
        options: Formatting options

    Returns:
        Formatted template string
    """
    from rdtl.parser import parse

    ast = parse(template)
    formatter = Formatter(options)
    return formatter.format(ast)


if __name__ == "__main__":
    # Test the formatter
    messy_template = """
<div class="container"><h1>{{title|upper}}</h1>
{% if user %}
<p>Hello {{user.name}}</p>
        {% for item in items %}<li>{{item}}</li>
    {% endfor %}
{%endif%}
</div>
    """

    print("=" * 80)
    print("ORIGINAL (messy):")
    print("=" * 80)
    print(messy_template)

    print("\n" + "=" * 80)
    print("FORMATTED (default options):")
    print("=" * 80)
    formatted = format_template(messy_template)
    print(formatted)

    print("\n" + "=" * 80)
    print("FORMATTED (compact style):")
    print("=" * 80)
    compact_options = FormatOptions(
        indent_size=2,
        space_in_template_tags=False,
        space_in_variables=False,
    )
    formatted_compact = format_template(messy_template, compact_options)
    print(formatted_compact)
