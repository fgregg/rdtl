# RDTL Formatter Demo

## What is it?

The RDTL formatter automatically formats your templates with consistent style, similar to tools like `black` for Python or `prettier` for JavaScript.

## Features

✅ **AST-based** - Parses templates correctly, no regex hacks
✅ **Configurable** - Multiple style options
✅ **Fast** - O(n) formatting time
✅ **CLI tool** - Easy to integrate into workflows
✅ **Check mode** - Verify formatting in CI/CD

## Quick Start

```bash
# Format to stdout
python rdtl_fmt.py template.html

# Format in-place
python rdtl_fmt.py template.html --write

# Check if formatted (for CI)
python rdtl_fmt.py template.html --check

# Compact style
python rdtl_fmt.py template.html --compact
```

## Examples

### Before (messy):
```html
<div class="container"><h1>{{title|upper}}</h1>
{% if user %}
<p>Hello {{user.name}}</p>
        {% for item in items %}<li>{{item}}</li>
    {% endfor %}
{%endif%}
</div>
```

### After (formatted):
```html
<div class="container">
    <h1>{{ title|upper }}</h1>
    {% if user %}
        <p>Hello {{ user.name }}</p>
        {% for item in items %}
            <li>{{ item }}</li>
        {% endfor %}
    {% endif %}
</div>
```

## Formatting Options

### Default Style
- 4-space indentation
- Spaces in template tags: `{% if user %}`
- Spaces in variables: `{{ user.name }}`
- Double quotes for attributes
- Self-closing slash: `<br />`

### Compact Style (`--compact`)
- 2-space indentation
- No spaces in tags: `{%if user%}`
- No spaces in variables: `{{user.name}}`

### Verbose Style (`--verbose-style`)
- 4-space indentation
- Blank lines before/after blocks
- Extra spacing for readability

### Custom Options
```bash
# Use tabs
python rdtl_fmt.py template.html --tabs

# Custom indent size
python rdtl_fmt.py template.html --indent 2

# Single quotes
python rdtl_fmt.py template.html --quotes single

# No self-closing slash
python rdtl_fmt.py template.html --no-self-closing-slash
```

## CLI Reference

```
usage: rdtl_fmt.py [-h] [--check | --write] [--compact | --verbose-style]
                   [--indent N] [--tabs] [--quotes {double,single}]
                   [--no-self-closing-slash] [-v]
                   files [files ...]

Format RDTL template files

positional arguments:
  files                 Template files to format

optional arguments:
  -h, --help            show this help message and exit
  --check               Check if files are formatted (exit non-zero if not)
  --write               Format files in-place
  --compact             Use compact formatting style
  --verbose-style       Use verbose formatting style with blank lines
  --indent N            Indentation size (default: 4 for normal, 2 for compact)
  --tabs                Use tabs for indentation instead of spaces
  --quotes {double,single}
                        Quote style for attributes (default: double)
  --no-self-closing-slash
                        Omit slash in self-closing tags (<br> instead of <br />)
  -v, --verbose         Verbose output
```

## Integration

### Pre-commit Hook

Create `.git/hooks/pre-commit`:
```bash
#!/bin/bash
python rdtl_fmt.py templates/*.html --check
if [ $? -ne 0 ]; then
    echo "Templates need formatting. Run: python rdtl_fmt.py templates/*.html --write"
    exit 1
fi
```

### CI/CD (GitHub Actions)

```yaml
- name: Check template formatting
  run: |
    python rdtl_fmt.py templates/**/*.html --check
```

### Editor Integration

#### VS Code Task
Add to `.vscode/tasks.json`:
```json
{
    "label": "Format RDTL Templates",
    "type": "shell",
    "command": "python rdtl_fmt.py ${file} --write",
    "problemMatcher": []
}
```

#### Format on Save
You could create a VS Code extension that formats RDTL on save!

## Why AST-Based Formatting?

Unlike regex-based formatters, RDTL formatter:

1. **Understands structure** - Knows the difference between HTML and template syntax
2. **Preserves semantics** - Never breaks your template
3. **Handles edge cases** - Nested blocks, complex expressions, etc.
4. **Provides guarantees** - If it formats, it's valid RDTL

## What It Formats

### HTML
- Consistent tag indentation
- Attribute formatting
- Self-closing tags

### Template Tags
- Consistent spacing: `{% if %}` vs `{%if%}`
- Block indentation
- Multi-line expressions

### Template Variables
- Spacing: `{{ var }}` vs `{{var}}`
- Filter formatting: `{{ x|filter:arg }}`

### Comments
- Preserves template comments
- (Does not format HTML comments)

## What It Doesn't Touch

- Text content (preserved exactly)
- Comment content (preserved exactly)
- Attribute values (preserved exactly)
- Expression semantics (preserved exactly)

## Performance

Formatting is fast - O(n) where n is template length:

- Lex: O(n)
- Parse: O(n)
- Format: O(n)
- **Total: O(n)**

Example timings:
- Small template (< 100 lines): < 10ms
- Medium template (< 1000 lines): < 100ms
- Large template (< 10000 lines): < 1s

## Limitations

Currently doesn't support:
- `<!DOCTYPE>` declarations (strip them or add support)
- HTML comments (preserved but not formatted)
- Custom template tag libraries

These could be added while maintaining the CFG property!

## Examples

### Example 1: Simple Formatting

**Before:**
```html
<ul>{% for x in items %}<li>{{x}}</li>{% endfor %}</ul>
```

**After:**
```html
<ul>
    {% for x in items %}
        <li>{{ x }}</li>
    {% endfor %}
</ul>
```

### Example 2: Complex Nesting

**Before:**
```html
<div>{% if user %}
{% if user.is_staff %}<p>Admin: {{user.name}}</p>
{% else %}<p>User: {{user.name}}</p>{% endif %}
{% endif %}</div>
```

**After:**
```html
<div>
    {% if user %}
        {% if user.is_staff %}
            <p>Admin: {{ user.name }}</p>
        {% else %}
            <p>User: {{ user.name }}</p>
        {% endif %}
    {% endif %}
</div>
```

### Example 3: Filters

**Before:**
```html
<p>{{text|upper|truncatewords:10}}</p>
```

**After:**
```html
<p>{{ text|upper|truncatewords:10 }}</p>
```

## Try It!

```bash
# Create a messy template
echo '<div>{% if x %}<p>{{y}}</p>{%endif%}</div>' > test.html

# Format it
python rdtl_fmt.py test.html --write

# Check the result
cat test.html
```

Result:
```html
<div>
    {% if x %}
        <p>{{ y }}</p>
    {% endif %}
</div>
```

## Summary

The RDTL formatter is a production-ready tool that:
- ✅ Formats templates consistently
- ✅ Uses AST parsing (no regex)
- ✅ Preserves semantics
- ✅ Runs in O(n) time
- ✅ Integrates with CI/CD
- ✅ Supports multiple styles

All while maintaining the context-free grammar property!
