# Restricted Django Template Language (RDTL)

A formally verifiable subset of Django templates combined with HTML, designed to be expressible as a context-free grammar.

## Restrictions

### 1. Strict HTML
- All HTML tags must be properly closed (except void elements like `<br>`)
- Tags must close in LIFO (Last-In-First-Out) order
- No implicit closing or HTML5 "tag soup"

### 2. Proper Nesting
- Template block tags must be properly nested with respect to HTML
- No interleaving: if a template block opens inside an HTML element, it must close before that element closes

### 3. Template Syntax in Attributes (NEW!)
- ✅ Template syntax **IS** allowed in HTML attribute values!
- **Opposite quote rule**: Use opposite quote types for nested strings
  - Double-quoted attributes can use single quotes in templates
  - Single-quoted attributes can use double quotes in templates

### 4. Custom Block Tags (NEW!)
- ✅ **Custom block tags are automatically discovered!**
- No need to register or whitelist custom template tags
- Any tag with a corresponding `{% endX %}` is treated as a block tag
- Maintains CFG through two-pass parsing

**Example:**
```html
{% myblock arg1 arg2 %}
  <p>Custom block content</p>
  {% nested %}
    <span>Nested custom blocks work too!</span>
  {% endnested %}
{% endmyblock %}
```

### 5. Django 5.2 Built-in Tags and Filters Support

RDTL now supports **all Django 5.2 built-in template tags and filters** that can be expressed in a context-free grammar:

**Supported Django Block Tags:**
- Control flow: `{% if %}`, `{% for %}` (with tuple unpacking), `{% ifchanged %}`
- Output control: `{% filter %}`, `{% spaceless %}`, `{% autoescape %}`
- Content: `{% block %}`, `{% verbatim %}`, `{% comment %}`
- Custom blocks: Any `{% customtag %}...{% endcustomtag %}` pair

**Supported Django Single Tags:**
- Template: `{% extends %}`, `{% include %}`, `{% load %}` (multiple libraries)
- URLs: `{% url %}` (with args/kwargs), `{% static %}`
- Data: `{% cycle %}`, `{% resetcycle %}`, `{% regroup %}`, `{% querystring %}`
- Debugging: `{% debug %}`, `{% lorem %}`

**HTML Features:**
- `<!DOCTYPE html>` declarations
- HTML comments `<!-- ... -->`
- CDATA sections `<![CDATA[ ... ]]>`

**Dynamic Attribute Names (NEW!):**
- ✅ **Template syntax in attribute names!**
- Simple: `{{ attr_name }}="value"` - Entire name from variable
- Mixed: `data-{{ id }}-item="value"` - Static + dynamic parts
- Framework support: `hx-{{ action }}`, `x-{{ directive }}`, `data-*`
- Quote independence: Name templates can use any quotes
- Works with: HTMX, Alpine.js, Vue.js, and custom frameworks

**Filter Validation:**
- Optional validation against 58 Django built-in filters
- Catches typos in filter names
- Allows custom filters when validation is disabled

**Unsupported Django Tags (cannot be expressed in CFG):**
- `{% with %}` - Creates context-dependent variable scoping
- `{% widthratio %}` - Complex expression evaluation
- Template inheritance (`{% extends %}` with block overriding) - Requires multi-file context
- `{% csrf_token %}` - Runtime security token generation
- `{% now %}` - Runtime timestamp generation

These tags require runtime evaluation, multi-file context, or context-sensitive scoping that cannot be determined during parsing. RDTL focuses on tags that can be validated and formatted at parse time.

### 6. Allowed Constructs

**Valid:**
```html
<div>
  {% if user.is_authenticated %}
    <p>{{ user.name }}</p>
  {% endif %}
</div>
```

**Valid (template in attribute with opposite quotes):**
```html
<div class="{% if status == 'active' %}active{% endif %}">
<img src="{% if user %}{{ user.avatar }}{% else %}'/default.jpg'{% endif %}">
```

**Valid (custom block tags):**
```html
{% cache 500 sidebar %}
  <div class="sidebar">...</div>
{% endcache %}
```

**Valid (Dynamic attribute names):**
```html
<!-- Simple: entire name is template -->
<div {{ attr_name }}="value">Content</div>
<button {% if disabled %}disabled{% else %}enabled{% endif %}>Click</button>

<!-- Mixed: static + dynamic parts -->
<div data-user-{{ user.id }}="active">Profile</div>
<div hx-{{ http_method }}="/api/{{ endpoint }}">HTMX</div>
<div class="item-{{ status }}">Styled</div>

<!-- Framework directives -->
<div x-{{ alpine_directive }}="value">Alpine.js</div>
<div :{{ vue_prop }}="data">Vue.js</div>
<div @{{ event_name }}="handler">Event</div>
```

**Valid (Django built-in tags):**
```html
<!DOCTYPE html>
<html>
<!-- HTML comments work -->
<head>
  {% load static humanize %}
  <link rel="stylesheet" href="{% static 'css/style.css' %}">
</head>
<body>
  {% comment %}
  This is a Django comment block
  {% endcomment %}

  {% for key, value in items %}
    <p>{{ key }}: {{ value|upper }}</p>
  {% endfor %}

  {% ifchanged article.date %}
    <h2>{{ article.date|date:"F Y" }}</h2>
  {% endifchanged %}

  {% filter lower|truncatewords:10 %}
    {{ user_content }}
  {% endfilter %}
</body>
</html>
```

**Invalid (same quote type in nested strings):**
```html
<div class="{% if status == "active" %}active{% endif %}">
     ↑                       ↑                           ↑
   double                 double - ERROR!            double
```

**Invalid (interleaved nesting):**
```html
<div>
  {% if condition %}
</div>
{% endif %}
```

## Grammar Sketch

The language can be described by these production rules:

```
Document → Element*
Element → HtmlElement | TemplateBlock | Text | Variable
HtmlElement → OpenTag Element* CloseTag
TemplateBlock → IfBlock | ForBlock | BlockTag
IfBlock → IF_OPEN Element* (ELIF_OPEN Element*)* (ELSE_OPEN Element*)? IF_CLOSE
ForBlock → FOR_OPEN Element* (EMPTY_OPEN Element*)? FOR_CLOSE
BlockTag → BLOCK_OPEN Element* BLOCK_CLOSE
Text → TEXT_TOKEN
Variable → VAR_OPEN IDENTIFIER VAR_CLOSE
```

## Strict HTML Mode

RDTL enforces **strict HTML** by default to ensure context-free parseability:

- All HTML tags must be properly closed (except void elements)
- Tags must close in LIFO (Last-In-First-Out) order
- No implicit closing or tag soup allowed
- Example: `<div><p>text</div></p>` is **invalid** (misordered)
- Example: `<div><p>text</p></div>` is **valid** (properly nested)

This is required because lenient HTML5 parsing involves context-sensitive rules that cannot be expressed in a context-free grammar.

### Lenient Mode

For backwards compatibility, you can disable strict HTML:

```python
is_valid, errors = validate_template(content, strict_html=False)
```

However, lenient mode may accept templates that are not truly context-free parseable.

## How Custom Block Discovery Works

RDTL uses a clever **two-pass approach** to support arbitrary custom block tags while maintaining CFG properties:

**Pass 1: Vocabulary Discovery**
```python
# Scan for all {% endX %} tags
discovered_blocks = find_all(r'{%\s*end(\w+)')
# Result: {'myblock', 'customblock', 'cache', ...}
```

**Pass 2: Parsing**
```python
# Parse with discovered vocabulary
# Grammar rules stay the same, only vocabulary changes
parser = Parser(tokens, discovered_blocks=discovered_blocks)
```

**Why this maintains CFG:**
- ✅ Fixed structural rules (proper nesting, matching pairs)
- ✅ Finite vocabulary per document (discovered in pass 1)
- ✅ No context-sensitivity (grammar doesn't change based on surrounding code)
- ✅ Similar to how compilers discover identifiers before parsing

This is analogous to lexical analysis in compilers - discovering the vocabulary before applying grammar rules.

## Pre-Parse Validation

Before attempting to parse, validate:

1. **Bracket Matching**: All `{%`, `%}`, `{{`, `}}`, `<`, `>` properly paired
2. **Block Tag Discovery**: Scan for `{% endX %}` patterns to identify block tags
3. **Proper Nesting**: Stack-based validation of both HTML and template blocks
4. **Tag Validation**: Ensure end tags match discovered or known block tags
5. **Strict HTML** (default): Enforce LIFO closing order for HTML tags

## Implementation Status

- [x] Grammar specification (EBNF) - see `grammar.ebnf`
- [x] Pre-parse validator with strict HTML mode - see `validator.py`
- [x] Example templates (valid and invalid) - see `examples/`
- [x] Comprehensive test suite - see `test_validator.py`, `test_parser.py`, `test_integration.py`
- [x] Theoretical foundations documentation - see `THEORY.md`
- [x] Lexer implementation - see `lexer.py`
- [x] Parser implementation - see `parser.py`
- [x] AST definition - see `ast_nodes.py`
- [x] **Template formatter** - see `formatter.py` and `rdtl_fmt.py` CLI tool
- [x] Template renderer - see `renderer.py` (basic implementation)
- [x] **Django 5.2 built-in tags support** - 12 block tags, 6 single tags
- [x] **HTML features** - DOCTYPE, comments, CDATA
- [x] **Dynamic attribute names** - Full support for template syntax in attribute names
- [x] **Hyphenated attributes** - data-*, aria-*, hx-*, x-*, and framework directives
- [x] **Filter validation** - Optional validation against 58 Django built-in filters
- [x] **Enhanced tag parsing** - url with expressions, for with tuple unpacking, load with multiple libraries

## Installation

```bash
# Install from source
pip install -e .

# Install with development dependencies
pip install -e ".[dev]"
```

## Usage

### Formatting Templates

```bash
# Format a template file to stdout
rdtl-fmt template.html

# Format in-place
rdtl-fmt template.html --write

# Check if formatted (for CI/CD)
rdtl-fmt template.html --check

# Compact style
rdtl-fmt template.html --compact

# Custom indentation
rdtl-fmt template.html --indent 2

# Single quotes for attributes
rdtl-fmt template.html --quotes single
```

See [docs/FORMAT_DEMO.md](docs/FORMAT_DEMO.md) for complete formatter documentation and [docs/CLI_IMPROVEMENTS.md](docs/CLI_IMPROVEMENTS.md) for CLI details.

### Validating Templates

```python
from validator import validate_template

template = "<div>{% if user %}<p>{{ user.name }}</p>{% endif %}</div>"
is_valid, errors = validate_template(template, strict_html=True)

if is_valid:
    print("Valid RDTL!")
else:
    for error in errors:
        print(error)
```

### Validating with Filter Checking

```python
from validator import validate_template

# Enable filter validation to catch typos
template = "{{ value|unknown_filter }}"
is_valid, errors = validate_template(template, validate_filters=True)

if not is_valid:
    print(errors)  # ['Unknown filter: unknown_filter']

# Disable for custom filters
template = "{{ value|my_custom_filter }}"
is_valid, errors = validate_template(template, validate_filters=False)
print(is_valid)  # True
```

### Rendering Templates (Basic)

```python
from renderer import render

template = """
<div>
    {% if user %}
        <p>Hello {{ user.name|upper }}!</p>
    {% endif %}
</div>
"""

context = {'user': {'name': 'Alice'}}
output = render(template, context)
print(output)
```

## Documentation

Comprehensive documentation is available in the [`docs/`](docs/) directory:

- **[Quick Start Guide](docs/QUICKSTART.md)** - Get started in 5 minutes
- **[Formatter Guide](docs/FORMAT_DEMO.md)** - Formatting examples and style guide
- **[CLI Reference](docs/CLI_IMPROVEMENTS.md)** - Command-line interface documentation
- **[Theory & Design](docs/THEORY.md)** - Why RDTL is context-free and how it works
- **[Django Validation](docs/DJANGO_VALIDATION.md)** - How we validate against Django's parser
- **[Dynamic Attributes](docs/DYNAMIC_ATTRIBUTES.md)** - Deep dive into dynamic attribute names
- **[Full Documentation Index](docs/README.md)** - Complete documentation overview

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=rdtl

# Run specific test file
pytest tests/test_parser.py

# Run Django comparison tests
pytest tests/test_django_comparison.py
```

## Contributing

RDTL is designed to be a formally verifiable subset of Django templates. Contributions that maintain the context-free grammar property are welcome!

## License

MIT
