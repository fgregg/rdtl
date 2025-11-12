"""
Template formatter for RDTL.

Pretty-prints templates with consistent indentation and spacing.
"""

from dataclasses import dataclass

from rdtl import ast_nodes
from rdtl.parser import parse


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


class Formatter(ast_nodes.ASTVisitor):
    """
    Formats RDTL templates with consistent style.

    Usage:
        formatter = Formatter(options)
        formatted = formatter.format(ast)
    """

    def __init__(self, options: FormatOptions | None = None):
        self.options = options or FormatOptions()
        self.output: list[str] = []
        self.indent_level = 0
        self.needs_indent = True
        self.last_was_block = False
        self.inline_context_depth = (
            0  # Track nesting depth of inline formatting contexts
        )

    def format(self, node: ast_nodes.ASTNode) -> str:
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

    def _has_block_children(self, node) -> bool:
        """Check if node has block-level children (vs inline children only)."""
        if not hasattr(node, "children"):
            return False

        # Inline HTML elements that should not trigger block formatting
        INLINE_ELEMENTS = {
            "a",
            "abbr",
            "b",
            "bdi",
            "bdo",
            "cite",
            "code",
            "data",
            "dfn",
            "em",
            "i",
            "kbd",
            "mark",
            "q",
            "s",
            "samp",
            "small",
            "span",
            "strong",
            "sub",
            "sup",
            "time",
            "u",
            "var",
            "wbr",
            "button",
            "label",
            "output",
            "select",
            "textarea",
        }

        for child in node.children:
            # Check for block-level Django template tags
            if isinstance(
                child, (ast_nodes.IfBlock, ast_nodes.ForBlock, ast_nodes.BlockTag)
            ):
                return True

            # Check for block-level HTML elements (not inline)
            if isinstance(child, ast_nodes.HTMLElement):
                if child.tag_name.lower() not in INLINE_ELEMENTS:
                    return True

        return False

    def _format_block_tag(
        self, node, opening_tag: str, closing_tag: str, format_children: bool = True
    ):
        """
        Generic formatter for block tags with inline/block detection.

        Args:
            node: The AST node to format
            opening_tag: Opening tag string (e.g., "{% spaceless %}")
            closing_tag: Closing tag string (e.g., "{% endspaceless %}")
            format_children: If True, visit children; if False, use node.content directly
        """
        has_block_children = self._has_block_children(node)

        if has_block_children:
            # Block formatting - add newlines and indentation
            self.writeln(opening_tag)

            if format_children:
                self._increase_indent()
                for child in node.children:
                    self.visit(child)
                self._decrease_indent()
            else:
                # For verbatim blocks that have raw content
                self.write(node.content)

            self.writeln(closing_tag)
        else:
            # Inline formatting - enter inline context to suppress newlines
            self.write(opening_tag)

            # Enter inline context - this will prevent nested elements from adding newlines
            self.inline_context_depth += 1
            try:
                if format_children:
                    # Visit children normally - they'll respect inline_context_depth
                    for child in node.children:
                        self.visit(child)
                else:
                    # For verbatim blocks that have raw content
                    self.output.append(node.content)
            finally:
                self.inline_context_depth -= 1

            self.write(closing_tag)

    def _serialize_unformatted(self, node):
        """Serialize a node as-is without formatting (for script tags)."""
        if isinstance(node, ast_nodes.Variable):
            self.output.append("{{ ")
            self.output.append(str(node.expression))
            for filter_obj in node.filters:
                self.output.append("|")
                self.output.append(filter_obj.name)
                if filter_obj.args:
                    self.output.append(":")
                    self.output.append(",".join(str(arg) for arg in filter_obj.args))
            self.output.append(" }}")
        elif isinstance(node, ast_nodes.IfBlock):
            # Output if block
            self.output.append("{% if ")
            self.output.append(self._format_condition(node.if_condition))
            self.output.append(" %}")
            for child in node.if_children:
                if isinstance(child, ast_nodes.TextNode):
                    self.output.append(child.content)
                else:
                    self._serialize_unformatted(child)
            self.output.append("{% endif %}")
        elif isinstance(node, ast_nodes.SingleTag):
            self.output.append("{% ")
            self.output.append(node.tag_name)
            if node.raw_content:
                self.output.append(" ")
                self.output.append(node.raw_content)
            self.output.append(" %}")
        else:
            # Fallback: use regular formatting
            self.visit(node)

    def _increase_indent(self):
        """Increase indentation level."""
        self.indent_level += 1

    def _decrease_indent(self):
        """Decrease indentation level."""
        self.indent_level = max(0, self.indent_level - 1)

    # ========================================================================
    # Visitor methods
    # ========================================================================

    def visit_Document(self, node: ast_nodes.Document):
        """Format the document."""
        for i, child in enumerate(node.children):
            # Skip pure whitespace text nodes at document level
            if isinstance(child, ast_nodes.TextNode) and not child.content.strip():
                continue

            self.visit(child)

    def visit_HTMLElement(self, node: ast_nodes.HTMLElement):
        """Format an HTML element."""
        tag = node.tag_name

        # Special case: script and pre tags - output children as-is without formatting
        # These preserve whitespace, so we can't reformat their contents
        if tag in ("script", "pre"):
            # Serialize script tag manually
            self.write(f"<{tag}")
            for attr in node.attributes:
                self.write(" ")
                self.write(attr.name)
                if attr.value is not None:
                    # Use simple quoting for script attributes
                    quote = '"' if self.options.quotes == "double" else "'"
                    self.write(f"={quote}{attr.value}{quote}")
            self.write(">")

            # Output children as-is without any formatting
            for child in node.children:
                if isinstance(child, ast_nodes.TextNode):
                    self.output.append(child.content)
                else:
                    # For non-text nodes (variables, tags), output them directly
                    self._serialize_unformatted(child)

            self.write(f"</{tag}>")
            self.writeln()
            return

        # Opening tag
        self.write(f"<{tag}")

        # Attributes
        for attr in node.attributes:
            self.write(" ")
            self.write(attr.name)
            if attr.value is not None:
                # Choose quote style: if value contains the preferred quote, use the other
                preferred_quote = '"' if self.options.quotes == "double" else "'"
                alternate_quote = "'" if preferred_quote == '"' else '"'

                if preferred_quote in attr.value and alternate_quote not in attr.value:
                    # Use alternate quote if value has preferred but not alternate
                    quote = alternate_quote
                elif preferred_quote not in attr.value:
                    # Use preferred if it's not in the value
                    quote = preferred_quote
                else:
                    # Both quotes present - escape the preferred one
                    quote = preferred_quote
                    # Escape the quote character in the value
                    escaped_value = attr.value.replace(quote, f"\\{quote}")
                    self.write(f"={quote}{escaped_value}{quote}")
                    continue

                self.write(f"={quote}{attr.value}{quote}")

        self.write(">")

        # Determine if we should format children inline or block
        has_block_children = any(
            isinstance(
                child,
                (
                    ast_nodes.HTMLElement,
                    ast_nodes.IfBlock,
                    ast_nodes.ForBlock,
                    ast_nodes.BlockTag,
                ),
            )
            for child in node.children
        )

        if (
            has_block_children
            and self.options.indent_html
            and self.inline_context_depth == 0
        ):
            # Block formatting (only if not in inline context)
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
                if isinstance(child, ast_nodes.TextNode):
                    self.output.append(child.content)
                else:
                    self.visit(child)

            self.output.append(f"</{tag}>")
            # Only add newline if not in inline context
            if self.inline_context_depth == 0:
                self.writeln()

    def visit_VoidElement(self, node: ast_nodes.VoidElement):
        """Format a void element."""
        self.write(f"<{node.tag_name}")

        for attr in node.attributes:
            self.write(" ")
            self.write(attr.name)
            if attr.value is not None:
                # Choose quote style: if value contains the preferred quote, use the other
                preferred_quote = '"' if self.options.quotes == "double" else "'"
                alternate_quote = "'" if preferred_quote == '"' else '"'

                if preferred_quote in attr.value and alternate_quote not in attr.value:
                    # Use alternate quote if value has preferred but not alternate
                    quote = alternate_quote
                elif preferred_quote not in attr.value:
                    # Use preferred if it's not in the value
                    quote = preferred_quote
                else:
                    # Both quotes present - escape the preferred one
                    quote = preferred_quote
                    # Escape the quote character in the value
                    escaped_value = attr.value.replace(quote, f"\\{quote}")
                    self.write(f"={quote}{escaped_value}{quote}")
                    continue

                self.write(f"={quote}{attr.value}{quote}")

        if self.options.self_closing_slash:
            self.write(" />")
        else:
            self.write(">")

        # Only add newline if not in inline context
        if self.inline_context_depth == 0:
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

    def visit_TextNode(self, node: ast_nodes.TextNode):
        """Format text node."""
        # For text nodes inside block elements, write as-is
        # The parent element handles indentation
        content = node.content

        # If it's just whitespace, skip it (parent handles spacing)
        if not content.strip():
            return

        self.write(content)

    def visit_Variable(self, node: ast_nodes.Variable):
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

    def visit_IfBlock(self, node: ast_nodes.IfBlock):
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

    def visit_ForBlock(self, node: ast_nodes.ForBlock):
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

    def visit_BlockTag(self, node: ast_nodes.BlockTag):
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

    def visit_WithBlock(self, node: ast_nodes.WithBlock):
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

    def visit_IncludeTag(self, node: ast_nodes.IncludeTag):
        """Format an include tag with optional 'with' clause."""
        quote = '"' if self.options.quotes == "double" else "'"

        # Build the tag content
        parts = [f"include {quote}{node.template_name}{quote}"]

        # Add 'with' clause if context variables are present
        if node.context_vars:
            var_assignments = []
            for key, value in node.context_vars.items():
                # Format the value expression - repr() works because AST nodes have proper __repr__
                var_assignments.append(f"{key}={value!r}")
            parts.append("with " + " ".join(var_assignments))

        tag_content = " ".join(parts)

        # Use write() instead of writeln() - surrounding TextNodes have the newlines
        if self.options.space_in_template_tags:
            self.write(f"{{% {tag_content} %}}")
        else:
            self.write(f"{{%{tag_content}%}}")

    def visit_ExtendsTag(self, node: ast_nodes.ExtendsTag):
        """Format an extends tag."""
        quote = '"' if self.options.quotes == "double" else "'"

        if self.options.space_in_template_tags:
            self.writeln(f"{{% extends {quote}{node.parent_template}{quote} %}}")
        else:
            self.writeln(f"{{%extends {quote}{node.parent_template}{quote}%}}")

    def visit_LoadTag(self, node: ast_nodes.LoadTag):
        """Format a load tag."""
        libraries = " ".join(node.libraries)
        if self.options.space_in_template_tags:
            self.writeln(f"{{% load {libraries} %}}")
        else:
            self.writeln(f"{{%load {libraries}%}}")

    def visit_UrlTag(self, node):
        """Format a url tag."""

        def format_arg(arg):
            """Format an argument (string, number, expression, or literal)."""
            if isinstance(arg, str):
                return repr(arg)
            elif isinstance(arg, ast_nodes.Expression):
                return str(arg)
            elif isinstance(arg, ast_nodes.Literal):
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

    def visit_CsrfTokenTag(self, node: ast_nodes.CsrfTokenTag):
        """Format a csrf_token tag."""
        if self.options.space_in_template_tags:
            self.writeln("{% csrf_token %}")
        else:
            self.writeln("{%csrf_token%}")

    def visit_CycleTag(self, node):
        """Format a cycle tag."""

        def format_value(v):
            """Format a cycle value (Literal or Expression)."""
            if isinstance(v, ast_nodes.Literal):
                if v.type == "string":
                    return repr(v.value)  # Adds quotes
                return str(v.value)
            elif isinstance(v, ast_nodes.Expression):
                # Variable reference - just use the base name
                return v.base
            else:
                raise TypeError(f"Invalid cycle value type: {type(v)}")

        values_str = " ".join(format_value(v) for v in node.values)

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
        # Use write() instead of writeln() to avoid adding extra newlines
        # The surrounding TextNodes will have the newlines if needed
        if self.options.space_in_template_tags:
            if node.raw_content:
                self.write(f"{{% {node.tag_name} {node.raw_content} %}}")
            else:
                self.write(f"{{% {node.tag_name} %}}")
        else:
            if node.raw_content:
                self.write(f"{{%{node.tag_name} {node.raw_content}%}}")
            else:
                self.write(f"{{%{node.tag_name}%}}")

    def visit_GenericBlockTag(self, node):
        """Format a generic block tag."""

        # Determine if this should be inline or block formatting
        has_block_children = any(
            isinstance(
                child,
                (
                    ast_nodes.HTMLElement,
                    ast_nodes.IfBlock,
                    ast_nodes.ForBlock,
                    ast_nodes.BlockTag,
                ),
            )
            for child in node.children
        )

        # Opening tag
        if has_block_children:
            # Block formatting - add newlines
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
        else:
            # Inline formatting - no newlines
            if self.options.space_in_template_tags:
                if node.raw_args:
                    self.write(f"{{% {node.tag_name} {node.raw_args} %}}")
                else:
                    self.write(f"{{% {node.tag_name} %}}")
            else:
                if node.raw_args:
                    self.write(f"{{%{node.tag_name} {node.raw_args}%}}")
                else:
                    self.write(f"{{%{node.tag_name}%}}")

            # Children - output directly without indentation
            for child in node.children:
                if isinstance(child, ast_nodes.TextNode):
                    self.output.append(child.content)
                else:
                    self.visit(child)

            # Closing tag
            if self.options.space_in_template_tags:
                self.write(f"{{% end{node.tag_name} %}}")
            else:
                self.write(f"{{%end{node.tag_name}%}}")

    def visit_CommentBlock(self, node):
        """Format a comment block."""
        if self.options.space_in_template_tags:
            opening = "{% comment %}"
            closing = "{% endcomment %}"
        else:
            opening = "{%comment%}"
            closing = "{%endcomment%}"

        self._format_block_tag(node, opening, closing)

    def visit_IfChangedBlock(self, node):
        """Format an ifchanged block."""
        if self.options.space_in_template_tags:
            if node.watch_expressions:
                watch = " ".join(str(e) for e in node.watch_expressions)
                opening = f"{{% ifchanged {watch} %}}"
            else:
                opening = "{% ifchanged %}"
            closing = "{% endifchanged %}"
        else:
            if node.watch_expressions:
                watch = " ".join(str(e) for e in node.watch_expressions)
                opening = f"{{%ifchanged {watch}%}}"
            else:
                opening = "{%ifchanged%}"
            closing = "{%endifchanged%}"

        self._format_block_tag(node, opening, closing)

    def visit_FilterBlock(self, node):
        """Format a filter block."""
        if self.options.space_in_template_tags:
            opening = f"{{% filter {node.filter_name} %}}"
            closing = "{% endfilter %}"
        else:
            opening = f"{{%filter {node.filter_name}%}}"
            closing = "{%endfilter%}"

        self._format_block_tag(node, opening, closing)

    def visit_SpacelessBlock(self, node):
        """Format a spaceless block."""
        if self.options.space_in_template_tags:
            opening = "{% spaceless %}"
            closing = "{% endspaceless %}"
        else:
            opening = "{%spaceless%}"
            closing = "{%endspaceless%}"

        self._format_block_tag(node, opening, closing)

    def visit_VerbatimBlock(self, node):
        """Format a verbatim block."""
        if self.options.space_in_template_tags:
            opening = "{% verbatim %}"
            closing = "{% endverbatim %}"
        else:
            opening = "{%verbatim%}"
            closing = "{%endverbatim%}"

        # Verbatim uses raw content, not children
        self._format_block_tag(node, opening, closing, format_children=False)

    def visit_AutoescapeBlock(self, node):
        """Format an autoescape block."""
        if self.options.space_in_template_tags:
            opening = f"{{% autoescape {node.mode} %}}"
            closing = "{% endautoescape %}"
        else:
            opening = f"{{%autoescape {node.mode}%}}"
            closing = "{%endautoescape%}"

        self._format_block_tag(node, opening, closing)

    def visit_Comment(self, node: ast_nodes.Comment):
        """Format a template comment."""
        if self.options.preserve_comments:
            self.writeln(f"{{# {node.content} #}}")

    def _format_condition(self, condition: ast_nodes.Condition) -> str:
        """Format a condition to string."""
        if isinstance(condition, ast_nodes.SimpleCondition):
            not_str = "not " if condition.negated else ""
            return f"{not_str}{condition.expression!r}"

        elif isinstance(condition, ast_nodes.Comparison):
            return f"{condition.left!r} {condition.operator} {condition.right!r}"

        elif isinstance(condition, ast_nodes.BooleanOp):
            parts = [self._format_condition(c) for c in condition.operands]
            return f" {condition.operator} ".join(parts)

        return str(condition)


def format_template(template: str, options: FormatOptions | None = None) -> str:
    """
    Format an RDTL template string.

    Args:
        template: RDTL template string
        options: Formatting options

    Returns:
        Formatted template string
    """
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
