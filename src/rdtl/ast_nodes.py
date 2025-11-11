"""
Abstract Syntax Tree (AST) node definitions for RDTL.

These classes represent the parsed structure of an RDTL template.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Any, Union
from abc import ABC, abstractmethod


class ASTNode(ABC):
    """Base class for all AST nodes."""

    @abstractmethod
    def __repr__(self) -> str:
        """Return string representation of the node."""
        pass


# ============================================================================
# Document and Element Nodes
# ============================================================================

@dataclass
class Document(ASTNode):
    """Root node of the AST representing the entire template."""
    children: List[ASTNode] = field(default_factory=list)

    def __repr__(self) -> str:
        return f"Document(children={len(self.children)})"


# ============================================================================
# HTML Nodes
# ============================================================================

@dataclass
class Attribute(ASTNode):
    """HTML attribute (name="value"). Supports dynamic attribute names with template syntax."""
    name: str  # Static name or template string (e.g., "{{ attr }}" or "data-{{ id }}")
    value: Optional[str] = None  # None for boolean attributes
    is_dynamic_name: bool = False  # True if name contains template syntax

    def __repr__(self) -> str:
        dynamic_marker = "[dynamic]" if self.is_dynamic_name else ""
        if self.value is None:
            return f"Attribute({dynamic_marker}{self.name})"
        return f"Attribute({dynamic_marker}{self.name}={self.value!r})"


@dataclass
class HTMLElement(ASTNode):
    """HTML element with opening/closing tags."""
    tag_name: str
    attributes: List[Attribute] = field(default_factory=list)
    children: List[ASTNode] = field(default_factory=list)
    self_closing: bool = False

    def __repr__(self) -> str:
        attrs = f", attrs={len(self.attributes)}" if self.attributes else ""
        children = f", children={len(self.children)}" if self.children else ""
        return f"HTMLElement({self.tag_name}{attrs}{children})"


@dataclass
class VoidElement(ASTNode):
    """HTML void element (br, img, input, etc.)."""
    tag_name: str
    attributes: List[Attribute] = field(default_factory=list)

    def __repr__(self) -> str:
        attrs = f", attrs={len(self.attributes)}" if self.attributes else ""
        return f"VoidElement({self.tag_name}{attrs})"


@dataclass
class DocType(ASTNode):
    """HTML DOCTYPE declaration."""
    content: str  # Full DOCTYPE content (e.g., "<!DOCTYPE html>")

    def __repr__(self) -> str:
        return f"DocType({self.content!r})"


@dataclass
class HTMLComment(ASTNode):
    """HTML comment: <!-- comment -->."""
    content: str

    def __repr__(self) -> str:
        preview = self.content[:30] + "..." if len(self.content) > 30 else self.content
        return f"HTMLComment({preview!r})"


@dataclass
class CDATA(ASTNode):
    """CDATA section: <![CDATA[...]]>."""
    content: str

    def __repr__(self) -> str:
        preview = self.content[:30] + "..." if len(self.content) > 30 else self.content
        return f"CDATA({preview!r})"


# ============================================================================
# Text Nodes
# ============================================================================

@dataclass
class TextNode(ASTNode):
    """Plain text content."""
    content: str

    def __repr__(self) -> str:
        preview = self.content[:30] + "..." if len(self.content) > 30 else self.content
        return f"TextNode({preview!r})"


# ============================================================================
# Template Variable Nodes
# ============================================================================

@dataclass
class Variable(ASTNode):
    """Template variable: {{ variable.name }}."""
    expression: 'Expression'
    filters: List['Filter'] = field(default_factory=list)

    def __repr__(self) -> str:
        filters_str = f"|{len(self.filters)} filters" if self.filters else ""
        return f"Variable({self.expression}{filters_str})"


@dataclass
class Expression(ASTNode):
    """Variable expression (e.g., user.name or items[0])."""
    base: str  # Base variable name
    lookups: List['Lookup'] = field(default_factory=list)

    def __repr__(self) -> str:
        lookups_str = "".join(str(l) for l in self.lookups)
        return f"{self.base}{lookups_str}"


@dataclass
class Lookup(ASTNode):
    """Attribute or index lookup."""
    type: str  # 'attribute' or 'index'
    value: Any  # str for attribute, int/str for index

    def __repr__(self) -> str:
        if self.type == 'attribute':
            return f".{self.value}"
        return f"[{self.value!r}]"


@dataclass
class Filter(ASTNode):
    """Template filter: |filter_name:arg1,arg2."""
    name: str
    args: List[Any] = field(default_factory=list)

    def __repr__(self) -> str:
        args_str = f":{','.join(repr(a) for a in self.args)}" if self.args else ""
        return f"|{self.name}{args_str}"


@dataclass
class FilteredExpression(ASTNode):
    """Expression with filters applied (e.g., field|length in conditions)."""
    expression: 'Expression'
    filters: List['Filter'] = field(default_factory=list)

    def __repr__(self) -> str:
        filters_str = "".join(str(f) for f in self.filters)
        return f"{self.expression}{filters_str}"


# ============================================================================
# Template Block Nodes
# ============================================================================

@dataclass
class IfBlock(ASTNode):
    """If/elif/else conditional block."""
    if_condition: 'Condition'
    if_children: List[ASTNode] = field(default_factory=list)
    elif_branches: List[tuple['Condition', List[ASTNode]]] = field(default_factory=list)
    else_children: Optional[List[ASTNode]] = None

    def __repr__(self) -> str:
        parts = [f"if({self.if_condition})"]
        if self.elif_branches:
            parts.append(f", {len(self.elif_branches)} elif")
        if self.else_children is not None:
            parts.append(", else")
        return f"IfBlock({''.join(parts)})"


@dataclass
class ForBlock(ASTNode):
    """For loop block."""
    loop_vars: List[str] = field(default_factory=list)  # Variable names (supports tuple unpacking)
    iterable: Expression = None  # What we're iterating over
    children: List[ASTNode] = field(default_factory=list)
    empty_children: Optional[List[ASTNode]] = None

    def __repr__(self) -> str:
        vars_str = ', '.join(self.loop_vars) if len(self.loop_vars) > 1 else self.loop_vars[0] if self.loop_vars else ''
        empty = ", empty" if self.empty_children else ""
        return f"ForBlock({vars_str} in {self.iterable}{empty})"


@dataclass
class BlockTag(ASTNode):
    """Block definition: {% block name %}...{% endblock %}."""
    name: str
    children: List[ASTNode] = field(default_factory=list)

    def __repr__(self) -> str:
        return f"BlockTag({self.name}, {len(self.children)} children)"


@dataclass
class WithBlock(ASTNode):
    """With block: {% with var=value %}...{% endwith %}."""
    assignments: List[tuple[str, Expression]] = field(default_factory=list)
    children: List[ASTNode] = field(default_factory=list)

    def __repr__(self) -> str:
        assigns = ", ".join(f"{k}={v}" for k, v in self.assignments)
        return f"WithBlock({assigns})"


# ============================================================================
# Single Template Tags
# ============================================================================

@dataclass
class IncludeTag(ASTNode):
    """Include tag: {% include "template.html" %}."""
    template_name: str
    context_vars: dict[str, Expression] = field(default_factory=dict)

    def __repr__(self) -> str:
        return f"IncludeTag({self.template_name!r})"


@dataclass
class ExtendsTag(ASTNode):
    """Extends tag: {% extends "base.html" %}."""
    parent_template: str

    def __repr__(self) -> str:
        return f"ExtendsTag({self.parent_template!r})"


@dataclass
class LoadTag(ASTNode):
    """Load tag: {% load static %}."""
    libraries: List[str] = field(default_factory=list)  # Support multiple libraries

    def __repr__(self) -> str:
        return f"LoadTag({', '.join(self.libraries)})"


@dataclass
class UrlTag(ASTNode):
    """URL tag: {% url 'view_name' arg1 arg2 key=val %}."""
    view_name: str
    args: List[Any] = field(default_factory=list)
    kwargs: dict = field(default_factory=dict)
    as_var: Optional[str] = None

    def __repr__(self) -> str:
        return f"UrlTag({self.view_name!r})"


@dataclass
class StaticTag(ASTNode):
    """Static tag: {% static 'path/to/file.css' %}."""
    path: str
    as_var: Optional[str] = None

    def __repr__(self) -> str:
        return f"StaticTag({self.path!r})"


@dataclass
class CsrfTokenTag(ASTNode):
    """CSRF token tag: {% csrf_token %}."""

    def __repr__(self) -> str:
        return "CsrfTokenTag()"


@dataclass
class CycleTag(ASTNode):
    """Cycle tag: {% cycle 'value1' 'value2' %}."""
    values: List[Any] = field(default_factory=list)
    cycle_name: Optional[str] = None  # Optional named cycle

    def __repr__(self) -> str:
        return f"CycleTag({len(self.values)} values)"


@dataclass
class ResetCycleTag(ASTNode):
    """Reset cycle tag: {% resetcycle cycle_name %}."""
    cycle_name: Optional[str] = None

    def __repr__(self) -> str:
        return f"ResetCycleTag({self.cycle_name!r})"


@dataclass
class DebugTag(ASTNode):
    """Debug tag: {% debug %}."""

    def __repr__(self) -> str:
        return "DebugTag()"


@dataclass
class LoremTag(ASTNode):
    """Lorem ipsum tag: {% lorem count method random %}."""
    count: int = 1
    method: str = 'w'  # 'w' for words, 'p' for paragraphs, 'b' for blocks
    random: bool = False

    def __repr__(self) -> str:
        return f"LoremTag(count={self.count}, method={self.method!r})"


@dataclass
class RegroupTag(ASTNode):
    """Regroup tag: {% regroup list by attribute as var %}."""
    list_expr: 'Expression'
    attribute: str
    var_name: str

    def __repr__(self) -> str:
        return f"RegroupTag({self.list_expr} by {self.attribute} as {self.var_name})"


@dataclass
class QueryStringTag(ASTNode):
    """Query string tag: {% querystring key=value %}."""
    updates: dict = field(default_factory=dict)  # Key-value pairs to update

    def __repr__(self) -> str:
        return f"QueryStringTag({len(self.updates)} updates)"


@dataclass
class SingleTag(ASTNode):
    """
    Generic single tag for arbitrary template tags.
    Examples: {% url 'name' %}, {% static 'path' %}, {% custom_tag args %}
    """
    tag_name: str
    raw_content: str  # Everything between {% tag_name and %}

    def __repr__(self) -> str:
        preview = self.raw_content[:30] + "..." if len(self.raw_content) > 30 else self.raw_content
        return f"SingleTag({self.tag_name!r}, {preview!r})"


@dataclass
class GenericBlockTag(ASTNode):
    """
    Generic block tag for custom/unknown block tags.
    Examples: {% myblock args %}...{% endmyblock %}
    """
    tag_name: str
    raw_args: str  # Arguments after tag name
    children: list[ASTNode] = field(default_factory=list)

    def __repr__(self) -> str:
        args_preview = self.raw_args[:20] + "..." if len(self.raw_args) > 20 else self.raw_args
        return f"GenericBlockTag({self.tag_name!r}, args={args_preview!r}, children={len(self.children)})"


# ============================================================================
# Comment Nodes
# ============================================================================

@dataclass
class Comment(ASTNode):
    """Template comment: {# comment #}."""
    content: str

    def __repr__(self) -> str:
        preview = self.content[:30] + "..." if len(self.content) > 30 else self.content
        return f"Comment({preview!r})"


@dataclass
class CommentBlock(ASTNode):
    """Django comment block: {% comment %}...{% endcomment %}."""
    children: List[ASTNode] = field(default_factory=list)

    def __repr__(self) -> str:
        return f"CommentBlock({len(self.children)} children)"


@dataclass
class IfChangedBlock(ASTNode):
    """If changed block: {% ifchanged %}...{% endifchanged %}."""
    watch_expressions: List['Expression'] = field(default_factory=list)  # Optional variables to watch
    children: List[ASTNode] = field(default_factory=list)

    def __repr__(self) -> str:
        watch_str = f", watching {len(self.watch_expressions)}" if self.watch_expressions else ""
        return f"IfChangedBlock({len(self.children)} children{watch_str})"


@dataclass
class FilterBlock(ASTNode):
    """Filter block: {% filter name %}...{% endfilter %}."""
    filter_name: str
    children: List[ASTNode] = field(default_factory=list)

    def __repr__(self) -> str:
        return f"FilterBlock({self.filter_name}, {len(self.children)} children)"


@dataclass
class SpacelessBlock(ASTNode):
    """Spaceless block: {% spaceless %}...{% endspaceless %}."""
    children: List[ASTNode] = field(default_factory=list)

    def __repr__(self) -> str:
        return f"SpacelessBlock({len(self.children)} children)"


@dataclass
class VerbatimBlock(ASTNode):
    """Verbatim block: {% verbatim %}...{% endverbatim %}."""
    content: str  # Raw content (not parsed)

    def __repr__(self) -> str:
        preview = self.content[:30] + "..." if len(self.content) > 30 else self.content
        return f"VerbatimBlock({preview!r})"


@dataclass
class AutoescapeBlock(ASTNode):
    """Autoescape block: {% autoescape on/off %}...{% endautoescape %}."""
    mode: str  # 'on' or 'off'
    children: List[ASTNode] = field(default_factory=list)

    def __repr__(self) -> str:
        return f"AutoescapeBlock({self.mode}, {len(self.children)} children)"


# ============================================================================
# Condition Nodes (for if/elif)
# ============================================================================

@dataclass
class Condition(ASTNode):
    """Boolean condition in if/elif statements."""
    pass


@dataclass
class SimpleCondition(Condition):
    """Simple condition: just a variable or expression."""
    expression: 'Union[Expression, Literal]'
    negated: bool = False

    def __repr__(self) -> str:
        not_str = "not " if self.negated else ""
        return f"{not_str}{self.expression}"


@dataclass
class Comparison(Condition):
    """Comparison condition: x == y, a < b, etc."""
    left: 'Union[Expression, Literal]'
    operator: str  # ==, !=, <, >, <=, >=, in, not in
    right: 'Union[Expression, Literal]'

    def __repr__(self) -> str:
        return f"{self.left} {self.operator} {self.right}"


@dataclass
class BooleanOp(Condition):
    """Boolean operation: and, or."""
    operator: str  # 'and' or 'or'
    operands: List[Condition] = field(default_factory=list)

    def __repr__(self) -> str:
        ops = f" {self.operator} ".join(str(o) for o in self.operands)
        return f"({ops})"


# ============================================================================
# Literal Values
# ============================================================================

@dataclass
class Literal(ASTNode):
    """Literal value (string, number, boolean)."""
    value: Any
    type: str  # 'string', 'number', 'boolean'

    def __repr__(self) -> str:
        return f"Literal({self.value!r})"


# ============================================================================
# AST Visitor Pattern
# ============================================================================

class ASTVisitor(ABC):
    """
    Base class for AST visitors.

    Subclass this and override visit_* methods to process the AST.
    """

    def visit(self, node: ASTNode) -> Any:
        """Visit a node and dispatch to the appropriate method."""
        method_name = f"visit_{node.__class__.__name__}"
        method = getattr(self, method_name, self.generic_visit)
        return method(node)

    def generic_visit(self, node: ASTNode) -> Any:
        """Called if no explicit visit_* method exists."""
        # Visit children if they exist
        if hasattr(node, 'children'):
            for child in node.children:
                self.visit(child)

    # Example visitor methods (subclasses should override)
    def visit_Document(self, node: Document) -> Any:
        for child in node.children:
            self.visit(child)

    def visit_HTMLElement(self, node: HTMLElement) -> Any:
        for child in node.children:
            self.visit(child)

    def visit_IfBlock(self, node: IfBlock) -> Any:
        for child in node.if_children:
            self.visit(child)
        for condition, children in node.elif_branches:
            for child in children:
                self.visit(child)
        if node.else_children:
            for child in node.else_children:
                self.visit(child)

    def visit_ForBlock(self, node: ForBlock) -> Any:
        for child in node.children:
            self.visit(child)
        if node.empty_children:
            for child in node.empty_children:
                self.visit(child)

    def visit_TextNode(self, node: TextNode) -> Any:
        pass

    def visit_Variable(self, node: Variable) -> Any:
        pass

    def visit_Comment(self, node: Comment) -> Any:
        pass


# ============================================================================
# Pretty Printer
# ============================================================================

class ASTPrinter(ASTVisitor):
    """Pretty-print the AST."""

    def __init__(self):
        self.indent_level = 0

    def print_node(self, node: ASTNode, extra: str = ""):
        """Print a node with current indentation."""
        indent = "  " * self.indent_level
        print(f"{indent}{node.__class__.__name__}{extra}")

    def visit(self, node: ASTNode):
        """Override to add indentation tracking."""
        self.print_node(node, f": {node}")
        self.indent_level += 1
        super().visit(node)
        self.indent_level -= 1

    def visit_TextNode(self, node: TextNode):
        # Don't indent further for text
        self.indent_level -= 1
        super().visit_TextNode(node)
        self.indent_level += 1

    def visit_Variable(self, node: Variable):
        # Don't indent further for variables
        self.indent_level -= 1
        super().visit_Variable(node)
        self.indent_level += 1

    def visit_Comment(self, node: Comment):
        # Don't indent further for comments
        self.indent_level -= 1
        super().visit_Comment(node)
        self.indent_level += 1
