# Django Reference Validation

This document explains how we use Django's built-in template parser as a reference implementation to validate our RDTL grammar.

## Why Use Django as Reference?

Django's template system is the **ground truth** for template syntax. By comparing our parser against Django's, we ensure:

1. **Correctness**: We accurately implement Django's template syntax
2. **Completeness**: We catch edge cases we might have missed
3. **Confidence**: We have validation that our grammar matches real-world Django behavior

## How It Works

### 1. Direct Comparison Tests

**File**: `tests/test_django_comparison.py`

These tests directly compare specific templates against both parsers:

```python
# Both parsers should accept valid templates
template = "{{ user.name }}"
django_accepts = Template(template)  # ✓
rdtl_accepts = parse(template)       # ✓

# Both parsers should reject invalid templates
template = "{{ user. name }}"
django_rejects = Template(template)  # ✗ TemplateSyntaxError
rdtl_rejects = parse(template)       # ✗ ParseError
```

**What we verify**:
- ✓ Dot notation: `user.name`, `items.0`
- ✓ Numeric indices: `items.0.name`
- ✗ Spaces in lookups: `user. name`, `user .name`
- ✗ Bracket notation: `items[0]`, `user['key']`

### 2. Grammar-Based Generation + Django Validation

**File**: `tests/test_grammar_with_django.py`

This combines Hypothesis grammar generation with Django validation:

```python
@given(template_from_lark_grammar)
def test_generated_templates_match_django(template):
    django_result = parse_with_django(template)
    rdtl_result = parse_with_rdtl(template)

    # Key invariant: if Django rejects syntax, RDTL should too
    if not django_result.accepts:
        assert not rdtl_result.accepts
```

**Benefits**:
- Automatically tests thousands of generated templates
- Discovers edge cases we didn't think of
- Ensures our grammar doesn't accept invalid Django syntax

### 3. Interactive Demo

**File**: `demo_django_validation.py`

Run this to see side-by-side comparison:

```bash
python demo_django_validation.py
```

Output example:
```
Template: '{{ user.name }}'
  Django: ACCEPT  RDTL: ACCEPT  ✓ AGREE

Template: '{{ user. name }}'
  Django: REJECT  RDTL: REJECT  ✓ AGREE
    Django: Could not parse the remainder: ' name' from 'user. name'
    RDTL:   No spaces allowed after '.' in lookups at line 1
```

## Key Findings

### ✓ Our Parser Matches Django

Both parsers **agree** on:

1. **Valid syntax**:
   - `{{ user.name }}` - dot notation
   - `{{ items.0 }}` - numeric index via dot
   - `{{ a.b.c.d }}` - deep nesting
   - `{{ value|upper }}` - filters
   - `{% if x %}{% endif %}` - control flow

2. **Invalid syntax**:
   - `{{ user. name }}` - space after dot
   - `{{ user .name }}` - space before dot
   - `{{ items[0] }}` - bracket notation
   - `{{ user['key'] }}` - bracket with string

### Expected Differences

**Filter validation**: Django validates filter names at parse time, RDTL validates only syntax:

```python
# Django: REJECT (filter 'foo' not registered)
# RDTL: ACCEPT (syntactically valid)
template = "{{ value|foo }}"
```

This is **intentional** - RDTL performs static syntax analysis without runtime context. This is correct behavior for a syntax validator.

## Running Tests

```bash
# Run all Django comparison tests
python -m pytest tests/test_django_comparison.py -v

# Run grammar generation with Django validation
python -m pytest tests/test_grammar_with_django.py -v

# Run interactive demo
python demo_django_validation.py
```

## Implementation Details

### Django Setup

Django requires minimal configuration:

```python
import django
from django.conf import settings

settings.configure(
    DEBUG=True,
    INSTALLED_APPS=['django.contrib.contenttypes'],
    TEMPLATES=[{'BACKEND': 'django.template.backends.django.DjangoTemplates'}]
)
django.setup()

from django.template import Template, TemplateSyntaxError
```

### Comparison Function

```python
def compare_parsers(template_str: str) -> dict:
    """Compare Django and RDTL on a template."""
    # Test Django
    try:
        Template(template_str)
        django_accepts = True
    except TemplateSyntaxError:
        django_accepts = False

    # Test RDTL
    try:
        parse(template_str)
        rdtl_accepts = True
    except ParseError:
        rdtl_accepts = False

    return {'django_accepts': django_accepts, 'rdtl_accepts': rdtl_accepts}
```

## Benefits for Development

### 1. Confidence in Grammar Changes

When modifying the grammar, run Django comparison tests to ensure you haven't diverged from Django's behavior.

### 2. Bug Discovery

Example: The whitespace-in-lookups bug was discovered through grammar generation:

```python
# Generated: {{ user. name }}
# Django: REJECT ✗
# RDTL: ACCEPT ✓ (BUG!)

# After fix:
# Django: REJECT ✗
# RDTL: REJECT ✗ (FIXED!)
```

### 3. Documentation

Django comparison tests serve as **executable specification** - they document exactly which features we support.

## Continuous Validation

These tests run as part of CI/CD to ensure ongoing compatibility with Django's template syntax.

## Dependencies

Django is a **development-only** dependency for testing:

```toml
[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "hypothesis>=6.0",
    "lark-parser>=0.12",
    "django>=5.0",  # For reference implementation testing
]
```

RDTL has **zero runtime dependencies** - Django is only used in tests.

## Summary

Using Django as a reference implementation ensures our RDTL grammar accurately reflects real Django template syntax. This approach:

- ✓ Validates correctness against ground truth
- ✓ Discovers edge cases through property-based testing
- ✓ Documents supported features with executable tests
- ✓ Provides confidence when modifying grammar

The result: **RDTL reliably parses exactly what Django accepts** (for syntax validation).
