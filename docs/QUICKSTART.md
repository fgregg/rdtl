# RDTL Quick Start Guide

## What is RDTL?

**Restricted Django Template Language (RDTL)** is a formally verifiable subset of Django templates combined with HTML. Unlike standard Django templates, RDTL can be parsed using a **context-free grammar**, making it suitable for:

- Static analysis and validation
- Fast, predictable parsing
- Security analysis
- Editor tooling (syntax highlighting, auto-complete)
- Educational purposes (teaching parsing theory)

## Key Restrictions

RDTL enforces 4 main restrictions to achieve context-free parsing:

### 1. Strict HTML (LIFO Nesting)
```html
✓ <div><p>text</p></div>
✗ <div><p>text</div></p>
```

### 2. No Template Syntax in HTML Tags
```html
✗ <div class="{% if active %}active{% endif %}">
✗ <img src="{{ user.avatar }}">
```

### 3. Proper Nesting (No Interleaving)
```html
✓ <div>{% if x %}<p>ok</p>{% endif %}</div>
✗ <div>{% if x %}</div>{% endif %}
```

### 4. Whitelisted Template Tags Only
- Allowed: `if`, `for`, `block`, `with`, `include`, etc.
- Disallowed: Custom template tags

## Installation & Usage

### Basic Usage

```python
from validator import validate_template

template = """
<div>
    {% if user %}
        <p>{{ user.name }}</p>
    {% endif %}
</div>
"""

is_valid, errors = validate_template(template)

if is_valid:
    print("✓ Valid RDTL template")
else:
    for error in errors:
        print(f"✗ {error}")
```

### Strict vs Lenient HTML

```python
# Strict mode (default) - enforces LIFO nesting
is_valid, errors = validate_template(template, strict_html=True)

# Lenient mode - allows some HTML5 flexibility
is_valid, errors = validate_template(template, strict_html=False)
```

**Recommendation**: Use strict mode for true context-free parsing.

## Examples

### Valid Template

```html
<!DOCTYPE html>
<html>
<head>
    <title>Dashboard</title>
</head>
<body>
    {% if user.is_authenticated %}
        <h1>Welcome, {{ user.name }}!</h1>
        <ul>
            {% for item in items %}
                <li>{{ item.title }}</li>
            {% empty %}
                <li>No items</li>
            {% endfor %}
        </ul>
    {% else %}
        <p>Please log in</p>
    {% endif %}
</body>
</html>
```

### Invalid Templates

**❌ Template in attribute:**
```html
<div class="{% if active %}active{% endif %}">
    Content
</div>
```

**Workaround:**
```html
{% if active %}
    <div class="active">Content</div>
{% else %}
    <div>Content</div>
{% endif %}
```

**❌ Interleaved nesting:**
```html
<div>
    {% if condition %}
</div>
{% endif %}
```

**Fix:**
```html
<div>
    {% if condition %}
        <!-- content -->
    {% endif %}
</div>
```

## Try It Out

```bash
# Run the example usage script
python example_usage.py

# Run the test suite
python -m unittest test_validator.py

# Test strict HTML mode
python test_strict_html.py
```

## Files Overview

| File | Description |
|------|-------------|
| `validator.py` | Pre-parse validator implementation |
| `grammar.ebnf` | Context-free grammar specification |
| `test_validator.py` | Comprehensive test suite (26 tests) |
| `example_usage.py` | Usage examples and demonstrations |
| `examples/` | Valid and invalid template examples |
| `THEORY.md` | Theoretical foundations and proof |
| `README.md` | Project overview and documentation |

## When to Use RDTL

### Good Use Cases

✓ Security-critical applications (prevents many XSS vectors)
✓ Static analysis pipelines
✓ High-performance template rendering
✓ Code generation from templates
✓ Teaching/learning parsing theory

### Not Recommended For

✗ Existing Django projects with complex templates
✗ When you need maximum template flexibility
✗ Quick prototyping with frequent template changes

## Performance Characteristics

- **Validation**: O(n) time, where n = template length
- **Memory**: O(d) space, where d = maximum nesting depth
- **No backtracking**: Predictable, linear performance

## Next Steps

1. **Read** `THEORY.md` to understand why RDTL is context-free
2. **Explore** `examples/` directory for template examples
3. **Run** `python example_usage.py` to see validator in action
4. **Experiment** with your own templates

## Contributing

Future work:
- [ ] Implement actual parser (lexer + parser)
- [ ] Build AST (Abstract Syntax Tree)
- [ ] Create template renderer
- [ ] Add more template tags (csrf_token, url, static, etc.)
- [ ] Performance benchmarks
- [ ] Editor plugins (VS Code, etc.)

## License

This is a demonstration project for educational purposes.

## Questions?

See `THEORY.md` for detailed explanation of the theoretical foundations.
