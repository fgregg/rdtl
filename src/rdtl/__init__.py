"""
RDTL - Restricted Django Template Language

A safer, context-free subset of Django templates with:
- Static parsing and validation
- Automatic formatting
- No arbitrary code execution
- Support for Django 5.2 built-in tags and filters
"""

__version__ = "0.1.0"

# Public API
# Export AST nodes for advanced usage and type hints
from rdtl.ast_nodes import (
    ASTNode,
    Attribute,
    BlockTag,
    Comparison,
    Condition,
    Document,
    Expression,
    ExtendsTag,
    Filter,
    FilteredExpression,
    ForBlock,
    GenericBlockTag,
    HTMLElement,
    IfBlock,
    IncludeTag,
    Literal,
    LoadTag,
    SingleTag,
    StaticTag,
    TextNode,
    UrlTag,
    Variable,
)
from rdtl.formatter import format_template
from rdtl.lexer import tokenize
from rdtl.parser import parse
from rdtl.validator import validate_template

__all__ = [
    # Version
    "__version__",
    # Main API functions
    "parse",
    "validate_template",
    "format_template",
    "tokenize",
    # AST nodes
    "ASTNode",
    "Document",
    "HTMLElement",
    "Attribute",
    "TextNode",
    "Variable",
    "Expression",
    "Literal",
    "Filter",
    "FilteredExpression",
    "IfBlock",
    "ForBlock",
    "BlockTag",
    "IncludeTag",
    "ExtendsTag",
    "LoadTag",
    "UrlTag",
    "StaticTag",
    "SingleTag",
    "GenericBlockTag",
    "Condition",
    "Comparison",
]
