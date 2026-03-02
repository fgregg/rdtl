"""
Pre-parse validator for Restricted Django Template Language (RDTL).

This validator performs fast checks to determine if a template conforms
to the restrictions that make it parseable as a context-free grammar.
"""

import re
from dataclasses import dataclass
from enum import Enum


class ValidationError(Exception):
    """Raised when a template violates RDTL restrictions."""

    pass


class TokenType(Enum):
    """Token types for the validator."""

    HTML_OPEN = "html_open"
    HTML_CLOSE = "html_close"
    HTML_VOID = "html_void"
    TEMPLATE_BLOCK_OPEN = "template_block_open"
    TEMPLATE_BLOCK_CLOSE = "template_block_close"
    TEMPLATE_VARIABLE = "template_variable"
    COMMENT = "comment"
    TEXT = "text"


@dataclass
class Token:
    """A token found during validation."""

    type: TokenType
    value: str
    position: int
    line: int
    column: int


@dataclass
class StackFrame:
    """A frame on the nesting validation stack."""

    type: str  # 'html' or template tag name like 'if', 'for', 'block'
    name: str  # tag name for HTML, block name for templates
    position: int
    line: int
    column: int


class RDTLValidator:
    """Validates that a template conforms to RDTL restrictions."""

    # Void HTML elements that don't need closing tags
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

    # Known Django built-in block tags (for validation)
    KNOWN_BLOCK_TAGS = {
        "if": "endif",
        "for": "endfor",
        "block": "endblock",
        "with": "endwith",
        "autoescape": "endautoescape",
        "filter": "endfilter",
        "spaceless": "endspaceless",
        "verbatim": "endverbatim",
    }

    # Known Django built-in single tags (for reference only - not used for validation)
    # The validator now accepts ANY simple tag by default (two-phase approach)
    SINGLE_TAGS = {
        "include",
        "extends",
        "load",
        "csrf_token",
        "else",
        "elif",
        "empty",
        "url",
        "static",
        "now",
        "templatetag",
        "widthratio",
        "firstof",
        "cycle",
        "resetcycle",
        "debug",
        "lorem",
        "regroup",
        "querystring",
    }

    # Django built-in filters (60+ filters)
    KNOWN_FILTERS = {
        # String manipulation
        "add",
        "addslashes",
        "capfirst",
        "center",
        "cut",
        "lower",
        "upper",
        "slugify",
        "title",
        "truncatechars",
        "truncatechars_html",
        "truncatewords",
        "truncatewords_html",
        "wordcount",
        "wordwrap",
        # Formatting
        "date",
        "time",
        "timesince",
        "timeuntil",
        "floatformat",
        "filesizeformat",
        "stringformat",
        "phone2numeric",
        "linenumbers",
        "linebreaks",
        "linebreaksbr",
        # List/sequence
        "dictsort",
        "dictsortreversed",
        "first",
        "join",
        "last",
        "length",
        "length_is",
        "random",
        "slice",
        "unordered_list",
        "make_list",
        # Logic/comparison
        "default",
        "default_if_none",
        "divisibleby",
        "pluralize",
        "yesno",
        # HTML/escaping
        "escape",
        "escapejs",
        "force_escape",
        "safe",
        "safeseq",
        "striptags",
        "removetags",
        # URL handling
        "iriencode",
        "urlencode",
        "urlize",
        "urlizetrunc",
        # Utility
        "get_digit",
        "json_script",
        "pprint",
        # Additional common filters
        "ljust",
        "rjust",
        "cut",
        "filesizeformat",
        "floatformat",
        "get_digit",
        "iriencode",
        "join",
        "length_is",
        "ljust",
        "make_list",
        "phone2numeric",
        "pluralize",
        "pprint",
        "random",
        "removetags",
        "rjust",
        "slice",
        "stringformat",
        "striptags",
        "time",
        "timesince",
        "timeuntil",
        "title",
        "truncatechars",
        "truncatechars_html",
        "truncatewords",
        "truncatewords_html",
        "unordered_list",
        "urlencode",
        "urlize",
        "urlizetrunc",
        "wordcount",
        "wordwrap",
        "yesno",
    }

    def __init__(
        self,
        template_content: str,
        strict_html: bool = True,
        validate_filters: bool = False,
    ):
        self.content = template_content
        self.position = 0
        self.line = 1
        self.column = 1
        self.errors: list[str] = []
        self.strict_html = strict_html
        self.validate_filters = validate_filters

        # Discover block tags by finding all {% endX %} patterns
        self.discovered_block_tags = self._discover_block_tags()

        # Merge known and discovered block tags
        self.ALLOWED_BLOCKS = {**self.KNOWN_BLOCK_TAGS}
        for tag in self.discovered_block_tags:
            if tag not in self.ALLOWED_BLOCKS:
                self.ALLOWED_BLOCKS[tag] = f"end{tag}"

    def _discover_block_tags(self) -> set:
        """
        Discover block tags by scanning for {% endX %} patterns.

        Returns a set of tag names that have corresponding end tags.
        This allows automatic support for custom block tags.
        """
        block_tags = set()
        pattern = re.compile(r"\{%\s*end(\w+)")

        for match in pattern.finditer(self.content):
            tag_name = match.group(1).lower()
            block_tags.add(tag_name)

        return block_tags

    def validate(self) -> bool:
        """
        Perform all validation checks.

        Returns:
            True if template is valid RDTL, False otherwise.
            Errors are stored in self.errors.
        """
        self.errors = []

        try:
            # Check 1: Proper bracket matching
            self._check_bracket_matching()

            # Check 2: Proper nesting of HTML and template blocks
            self._check_proper_nesting()

            # Check 3: Only allowed template tags
            self._check_allowed_tags()

            # Check 4: Validate filters (if enabled)
            if self.validate_filters:
                self._check_filters()

            return len(self.errors) == 0

        except ValidationError as e:
            self.errors.append(str(e))
            return False

    def _check_bracket_matching(self):
        """Check that all brackets are properly matched."""
        stack = []
        i = 0
        in_raw_text_element = None  # tracks <script> or <style> content
        entering_raw_text = None  # set when we see <script/<style, activated on ">"

        # Use masked content to avoid matching brackets inside attribute values
        masked = self._mask_attribute_values(self.content)

        while i < len(masked):
            char = masked[i]

            # Check for template variable opening
            if i + 1 < len(masked) and masked[i : i + 2] == "{{":
                stack.append(("{", i, "variable"))
                i += 2
                continue

            # Check for template tag opening
            if i + 1 < len(masked) and masked[i : i + 2] == "{%":
                stack.append(("{", i, "tag"))
                i += 2
                continue

            # Check for comment opening
            if i + 1 < len(masked) and masked[i : i + 2] == "{#":
                stack.append(("{", i, "comment"))
                i += 2
                continue

            # Check for template variable closing
            if i + 1 < len(masked) and masked[i : i + 2] == "}}":
                if not stack or stack[-1][2] != "variable":
                    line, col = self._get_line_col(i)
                    self.errors.append(f"Line {line}, col {col}: Unmatched '}}}}'")
                else:
                    stack.pop()
                i += 2
                continue

            # Check for template tag closing
            if i + 1 < len(masked) and masked[i : i + 2] == "%}":
                if not stack or stack[-1][2] != "tag":
                    line, col = self._get_line_col(i)
                    self.errors.append(f"Line {line}, col {col}: Unmatched '%}}'")
                else:
                    stack.pop()
                i += 2
                continue

            # Check for comment closing
            if i + 1 < len(masked) and masked[i : i + 2] == "#}":
                if not stack or stack[-1][2] != "comment":
                    line, col = self._get_line_col(i)
                    self.errors.append(f"Line {line}, col {col}: Unmatched '#}}'")
                else:
                    stack.pop()
                i += 2
                continue

            # Check for closing </script> or </style> tag to exit raw text mode
            if in_raw_text_element and char == "<":
                close_tag = f"</{in_raw_text_element}"
                end = i + len(close_tag)
                if masked[i:end].lower() == close_tag:
                    in_raw_text_element = None
                    # Fall through to normal HTML bracket matching for the closing tag
                else:
                    i += 1
                    continue

            # Inside <script> or <style>, skip HTML bracket matching
            if in_raw_text_element:
                i += 1
                continue

            # Check for HTML tag opening (skip inside template tags where < is a comparison operator)
            if char == "<" and i + 1 < len(masked):
                if masked[i + 1] not in "{":
                    if not stack or stack[-1][2] != "tag":
                        stack.append(("<", i, "html"))
                        # Check if this opens a <script> or <style> tag
                        for tag_name in ("script", "style"):
                            end = i + 1 + len(tag_name)
                            if (
                                end <= len(masked)
                                and masked[i + 1 : end].lower() == tag_name
                                and (end == len(masked) or not masked[end].isalpha())
                            ):
                                entering_raw_text = tag_name
                                break

            # Check for HTML tag closing (skip inside template tags where > is a comparison operator)
            elif char == ">" and stack and stack[-1][2] == "html":
                stack.pop()
                # Enter raw text mode after the opening tag closes
                if entering_raw_text:
                    in_raw_text_element = entering_raw_text
                    entering_raw_text = None

            i += 1

        # Check for unclosed brackets
        for bracket, pos, bracket_type in stack:
            line, col = self._get_line_col(pos)
            type_name = {"variable": "{{", "tag": "{%", "comment": "{#", "html": "<"}[
                bracket_type
            ]
            self.errors.append(f"Line {line}, col {col}: Unclosed '{type_name}'")

    def _handle_html_opening_tag(
        self,
        stack: list[StackFrame],
        html_tag: str,
        match_start: int,
        line: int,
        col: int,
    ) -> None:
        """Handle an HTML opening tag during nesting validation.

        Args:
            stack: The current nesting stack to push onto.
            html_tag: The HTML tag name.
            match_start: Position in the content where the tag was found.
            line: Line number of the tag.
            col: Column number of the tag.
        """
        tag_lower = html_tag.lower()
        stack.append(StackFrame("html", tag_lower, match_start, line, col))

    def _handle_html_closing_tag(
        self, stack: list[StackFrame], html_tag: str, line: int, col: int
    ) -> None:
        """Handle an HTML closing tag during nesting validation.

        Checks for proper nesting in both strict and lenient modes.
        In strict mode, requires LIFO matching (most recent opening tag).
        In lenient mode, finds the most recent matching opening tag and
        detects incorrectly interleaved template blocks.

        Args:
            stack: The current nesting stack to pop from.
            html_tag: The HTML tag name.
            line: Line number of the closing tag.
            col: Column number of the closing tag.
        """
        tag_lower = html_tag.lower()

        if not stack:
            self.errors.append(
                f"Line {line}, col {col}: Closing tag </{html_tag}> "
                "without matching opening tag"
            )
            return

        # In strict mode, require exact LIFO matching
        if self.strict_html:
            # The closing tag must match the most recent opening tag
            if stack[-1].type != "html" or stack[-1].name != tag_lower:
                expected = (
                    f"</{stack[-1].name}>"
                    if stack[-1].type == "html"
                    else f"{{%% end{stack[-1].name} %%}}"
                )
                self.errors.append(
                    f"Line {line}, col {col}: Expected {expected} but found </{html_tag}>"
                )
                return

            # Pop the matching tag
            stack.pop()
        else:
            # Lenient mode: Find matching opening tag
            found = False
            for i in range(len(stack) - 1, -1, -1):
                if stack[i].type == "html" and stack[i].name == tag_lower:
                    # Check if any template blocks are incorrectly interleaved
                    for j in range(i + 1, len(stack)):
                        if stack[j].type != "html":
                            self.errors.append(
                                f"Line {line}, col {col}: HTML tag </{html_tag}> "
                                f"closes before template block '{{{{% {stack[j].name} %}}}}' "
                                f"from line {stack[j].line}"
                            )

                    # Pop everything from i onwards
                    stack[:] = stack[:i]
                    found = True
                    break

            if not found:
                self.errors.append(
                    f"Line {line}, col {col}: Closing tag </{html_tag}> "
                    "without matching opening tag"
                )

    def _handle_template_opening_tag(
        self,
        stack: list[StackFrame],
        template_tag: str,
        match_start: int,
        line: int,
        col: int,
    ) -> None:
        """Handle a template block opening tag during nesting validation.

        Args:
            stack: The current nesting stack to push onto.
            template_tag: The template tag name (e.g., 'if', 'for', 'block').
            match_start: Position in the content where the tag was found.
            line: Line number of the tag.
            col: Column number of the tag.
        """
        tag_lower = template_tag.lower()
        stack.append(StackFrame("template", tag_lower, match_start, line, col))

    def _handle_template_closing_tag(
        self, stack: list[StackFrame], template_tag: str, line: int, col: int
    ) -> None:
        """Handle a template block closing tag during nesting validation.

        Validates that the closing tag matches an opening tag and detects
        incorrectly interleaved HTML or other template blocks.

        Args:
            stack: The current nesting stack to pop from.
            template_tag: The template tag name (e.g., 'endif', 'endfor').
            line: Line number of the closing tag.
            col: Column number of the closing tag.
        """
        tag_lower = template_tag.lower()
        block_type = tag_lower[3:]  # Remove 'end' prefix

        # Look for matching opening block in stack
        found = False
        for i in range(len(stack) - 1, -1, -1):
            if stack[i].type == "template" and stack[i].name == block_type:
                # Check if any HTML or other template blocks are incorrectly interleaved
                for j in range(i + 1, len(stack)):
                    if stack[j].type == "html":
                        self.errors.append(
                            f"Line {line}, col {col}: Template block '{{{{% end{block_type} %}}}}' "
                            f"closes before HTML tag <{stack[j].name}> "
                            f"from line {stack[j].line}"
                        )
                    elif stack[j].type == "template":
                        self.errors.append(
                            f"Line {line}, col {col}: Template block '{{{{% end{block_type} %}}}}' "
                            f"closes before template block '{{{{% {stack[j].name} %}}}}' "
                            f"from line {stack[j].line}"
                        )
                # Pop everything from i onwards
                stack[:] = stack[:i]
                found = True
                break

        if not found:
            expected = (
                f"end{stack[-1].name}"
                if stack and stack[-1].type == "template"
                else "nothing"
            )
            self.errors.append(
                f"Line {line}, col {col}: Unexpected '{{{{% {template_tag} %}}}}', "
                f"expected '{expected}'"
            )

    def _handle_contextual_tag(
        self, stack: list[StackFrame], template_tag: str, line: int, col: int
    ) -> None:
        """Handle contextual template tags (else, elif, empty) during nesting validation.

        These tags are only valid within specific block contexts:
        - else/elif: must be inside an 'if' block
        - empty: must be inside a 'for' block

        Args:
            stack: The current nesting stack to check for parent blocks.
            template_tag: The template tag name ('else', 'elif', or 'empty').
            line: Line number of the tag.
            col: Column number of the tag.
        """
        tag_lower = template_tag.lower()

        # Validate contextual requirements
        if tag_lower in ("else", "elif"):
            if not any(f.type == "template" and f.name == "if" for f in stack):
                self.errors.append(
                    f"Line {line}, col {col}: '{{{{% {template_tag} %}}}}' "
                    "outside of if block"
                )
        elif tag_lower == "empty":
            if not any(f.type == "template" and f.name == "for" for f in stack):
                self.errors.append(
                    f"Line {line}, col {col}: '{{{{% empty %}}}}' outside of for block"
                )

    def _check_proper_nesting(self):
        """Verify proper nesting of HTML and template blocks.

        This method validates that all HTML tags and Django template blocks are
        properly nested and closed. It operates in two modes:

        - Strict mode: Requires perfect LIFO nesting (every closing tag must
          match the most recently opened tag).
        - Lenient mode: Allows HTML tags to close out of strict order, but
          still detects incorrectly interleaved HTML and template blocks.

        The validation process:
        1. Masks attribute values to prevent false matches from template
           syntax within attributes.
        2. Scans the template for HTML tags, template block tags, and
           contextual tags (else, elif, empty).
        3. Maintains a stack of open tags and validates each closing tag
           against the stack.
        4. Reports errors for unclosed tags, mismatched nesting, and
           contextual tags appearing outside their required blocks.
        """
        stack: list[StackFrame] = []

        # Create a version of content with attribute values masked
        # This prevents template syntax inside attributes from being matched
        masked_content = self._mask_attribute_values(self.content)

        # Pattern to find HTML tags and template tags
        pattern = re.compile(
            r"<(/?)([a-zA-Z][a-zA-Z0-9]*)[^>]*(/?)>|"  # HTML tags
            r"\{%\s*(\w+)\s*[^%]*%\}|"  # Template tags
            r"\{\{[^}]*\}\}|"  # Template variables (skip)
            r"\{#[^}]*#\}"  # Comments (skip)
        )

        for match in pattern.finditer(masked_content):
            html_close, html_tag, html_self_close, template_tag = match.groups()
            line, col = self._get_line_col(match.start())

            # Handle HTML tags
            if html_tag:
                tag_lower = html_tag.lower()

                # Self-closing or void element
                if html_self_close or tag_lower in self.VOID_ELEMENTS:
                    continue

                # Opening tag
                if not html_close:
                    self._handle_html_opening_tag(
                        stack, html_tag, match.start(), line, col
                    )
                # Closing tag
                else:
                    self._handle_html_closing_tag(stack, html_tag, line, col)

            # Handle template tags
            elif template_tag:
                tag_lower = template_tag.lower()

                # Opening block tag
                if tag_lower in self.ALLOWED_BLOCKS:
                    self._handle_template_opening_tag(
                        stack, template_tag, match.start(), line, col
                    )
                # Closing block tag
                elif tag_lower.startswith("end"):
                    self._handle_template_closing_tag(stack, template_tag, line, col)
                # Context-dependent single tags that must appear inside specific blocks
                elif tag_lower in ("else", "elif", "empty"):
                    self._handle_contextual_tag(stack, template_tag, line, col)
                # All other simple tags are accepted (two-phase approach)

        # Check for unclosed blocks
        for frame in stack:
            if frame.type == "html":
                self.errors.append(
                    f"Line {frame.line}, col {frame.column}: "
                    f"Unclosed HTML tag <{frame.name}>"
                )
            elif frame.type == "template":
                self.errors.append(
                    f"Line {frame.line}, col {frame.column}: "
                    f"Unclosed template block '{{{{% {frame.name} %}}}}'"
                )

    def _check_allowed_tags(self):
        """
        Check that template tags are structurally valid.

        Two-phase approach:
        1. Block tags are discovered by scanning for {% endX %} patterns
        2. Any tag not identified as a block tag is treated as a valid simple tag

        This only validates that end tags match discovered/known block tags.
        """
        pattern = re.compile(r"\{%\s*(\w+)")

        for match in pattern.finditer(self.content):
            tag = match.group(1).lower()

            # Only validate end tags - they must match a known/discovered block tag
            if tag.startswith("end"):
                base_tag = tag[3:]
                if base_tag not in self.ALLOWED_BLOCKS:
                    line, col = self._get_line_col(match.start())
                    self.errors.append(
                        f"Line {line}, col {col}: Unknown end tag '{{{{% {tag} %}}}}' without matching block tag"
                    )
            # If tag is in ALLOWED_BLOCKS, it's a block opener (validated elsewhere for matching end tag)
            # Otherwise, it's a simple tag - accept it (no validation needed)

    def _mask_attribute_values(self, content: str) -> str:
        """
        Mask quoted attribute values to prevent template syntax inside them
        from being matched by the nesting checker.

        Replaces content inside quotes with spaces to preserve positions.
        """
        result = []
        i = 0

        while i < len(content):
            char = content[i]

            # Check for HTML tag opening (both <tag and </tag)
            if char == "<" and i + 1 < len(content):
                next_char = content[i + 1]
                # Check if it's a tag (starts with letter or /)
                if next_char.isalpha() or (
                    next_char == "/"
                    and i + 2 < len(content)
                    and content[i + 2].isalpha()
                ):
                    # We're in an HTML tag
                    result.append(char)
                    i += 1

                    # Scan through the tag
                    while i < len(content):
                        char = content[i]

                        # If we hit a quote, mask the value
                        if char in ('"', "'"):
                            quote = char
                            result.append(char)
                            i += 1

                            # Mask everything until the closing quote
                            # Track when we're inside template tags/variables to handle nested quotes
                            inside_template = False
                            template_string_delimiter = None

                            while i < len(content):
                                # Check for template tag/variable start
                                if i + 1 < len(content) and content[i : i + 2] in (
                                    "{{",
                                    "{%",
                                    "{#",
                                ):
                                    inside_template = True
                                    result.append(" ")
                                    i += 1
                                    result.append(" ")
                                    i += 1
                                    continue

                                # Check for template tag/variable end
                                if (
                                    inside_template
                                    and i + 1 < len(content)
                                    and content[i : i + 2] in ("}}", "%}", "#}")
                                ):
                                    inside_template = False
                                    template_string_delimiter = None
                                    result.append(" ")
                                    i += 1
                                    result.append(" ")
                                    i += 1
                                    continue

                                # Track string literals inside templates
                                if inside_template and content[i] in ('"', "'"):
                                    if template_string_delimiter is None:
                                        # Entering a string literal in the template
                                        template_string_delimiter = content[i]
                                    elif content[i] == template_string_delimiter:
                                        # Check for escape sequence
                                        if i > 0 and content[i - 1] != "\\":
                                            # Exiting the string literal
                                            template_string_delimiter = None
                                    result.append(" ")
                                    i += 1
                                    continue

                                # Check for attribute-delimiting quote (only when not in template string)
                                if content[i] == quote and (
                                    not inside_template
                                    or template_string_delimiter is None
                                ):
                                    result.append(content[i])
                                    i += 1
                                    break

                                # Preserve newlines for line counting
                                if content[i] == "\n":
                                    result.append("\n")
                                    i += 1
                                else:
                                    result.append(" ")
                                    i += 1
                            continue

                        # End of tag
                        if char == ">":
                            result.append(char)
                            i += 1
                            break

                        result.append(char)
                        i += 1
                    continue

            result.append(char)
            i += 1

        return "".join(result)

    def _check_filters(self):
        """Validate that all filters used are in the KNOWN_FILTERS set."""
        # Find all {{ ... }} variable expressions
        pattern = re.compile(r"\{\{([^}]+)\}\}")

        for match in pattern.finditer(self.content):
            var_content = match.group(1)
            position = match.start()

            # Check for filters (indicated by |)
            if "|" in var_content:
                # Split by | to get filters
                parts = var_content.split("|")

                # Skip the first part (variable name)
                for filter_part in parts[1:]:
                    filter_part = filter_part.strip()

                    # Extract filter name (before : if args present)
                    if ":" in filter_part:
                        filter_name = filter_part.split(":")[0].strip()
                    else:
                        filter_name = filter_part.split()[0] if filter_part else ""

                    # Check if filter is known
                    if filter_name and filter_name not in self.KNOWN_FILTERS:
                        line, col = self._get_line_col(position)
                        self.errors.append(
                            f"Line {line}, col {col}: Unknown filter '{filter_name}'. "
                            f"Use a Django built-in filter or disable filter validation."
                        )

    def _get_line_col(self, position: int) -> tuple[int, int]:
        """Get line and column number for a position in the content."""
        line = 1
        col = 1

        for i in range(min(position, len(self.content))):
            if self.content[i] == "\n":
                line += 1
                col = 1
            else:
                col += 1

        return line, col


def validate_template(
    template_content: str, strict_html: bool = True, validate_filters: bool = False
) -> tuple[bool, list[str]]:
    """
    Validate a template against RDTL restrictions.

    Args:
        template_content: The template string to validate
        strict_html: If True (default), require strict HTML with proper LIFO nesting.
                     If False, allow HTML5-style lenient tag closing.
        validate_filters: If True, validate that all filters are Django built-ins.
                         If False (default), allow any filter names.

    Returns:
        A tuple of (is_valid, errors) where errors is a list of error messages
    """
    validator = RDTLValidator(
        template_content, strict_html=strict_html, validate_filters=validate_filters
    )
    is_valid = validator.validate()
    return is_valid, validator.errors


if __name__ == "__main__":
    # Example usage
    valid_template = """
    <html>
        <body>
            {% if user.is_authenticated %}
                <p>Hello {{ user.name }}</p>
            {% endif %}

            <ul>
                {% for item in items %}
                    <li>{{ item }}</li>
                {% empty %}
                    <li>No items</li>
                {% endfor %}
            </ul>
        </body>
    </html>
    """

    invalid_template = """
    <div class="{% if active %}active{% endif %}">
        Bad template
    </div>
    """

    print("Validating valid template:")
    is_valid, errors = validate_template(valid_template)
    print(f"Valid: {is_valid}")
    if errors:
        for error in errors:
            print(f"  - {error}")

    print("\nValidating invalid template:")
    is_valid, errors = validate_template(invalid_template)
    print(f"Valid: {is_valid}")
    if errors:
        for error in errors:
            print(f"  - {error}")
