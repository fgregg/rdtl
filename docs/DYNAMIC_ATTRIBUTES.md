# Dynamic Attribute Names in RDTL

## Overview

RDTL now supports **full dynamic attribute names** with Django template syntax! This feature enables modern web development patterns with frameworks like HTMX, Alpine.js, and Vue.js while maintaining context-free grammar properties.

## Features

### 1. Simple Dynamic Names
Entire attribute name is a template expression:

```html
<!-- Variable -->
<div {{ attr_name }}="value">Content</div>

<!-- With filter -->
<div {{ attr|safe }}="value">Content</div>

<!-- Conditional -->
<button {% if disabled %}disabled{% else %}enabled{% endif %}>Click</button>
```

### 2. Mixed Dynamic Names
Static text combined with template expressions:

```html
<!-- Data attributes -->
<div data-user-{{ user.id }}="active">Profile</div>
<div data-{{ attr_type }}-value="123">Dynamic data-*</div>

<!-- HTMX -->
<div hx-{{ http_method }}="/api/{{ endpoint }}">Load</div>
<button hx-post="/users/{{ user.id }}/follow">Follow</button>

<!-- Alpine.js -->
<div x-{{ directive }}="value">Alpine directive</div>
<div x-on:{{ event }}="handler">Event handler</div>

<!-- Multiple dynamic parts -->
<div {{ prefix }}-item-{{ id }}-{{ suffix }}="value">Complex</div>
```

### 3. Framework Support

#### HTMX
```html
<div hx-{{ action }}="/api/endpoint"
     hx-target="#result"
     hx-swap="innerHTML">
    Load Data
</div>
```

#### Alpine.js
```html
<div x-data="{ open: false }"
     x-{{ show_directive }}="open"
     x-on:{{ event_name }}="open = true">
    Toggle
</div>
```

#### Vue.js
```html
<div :{{ prop_name }}="value"
     @{{ event_name }}="handler"
     v-{{ directive }}="data">
    Vue Component
</div>
```

### 4. Hyphenated Attributes
Full support for HTML5 and framework attributes:

```html
<!-- HTML5 -->
<div data-item-id="123" aria-label="Close">Content</div>

<!-- HTMX -->
<div hx-get="/api" hx-target="#result">Load</div>

<!-- Alpine.js -->
<div x-data="{}" x-show="open" x-on:click="toggle">Click</div>

<!-- Vue.js -->
<div v-model.trim="text" v-bind:class="classes">Input</div>
```

## Quote Rules

### Independent Quote Rules
Attribute name templates and value templates have **independent** quote rules:

```html
<!-- ✓ VALID: Double quotes in name, single quotes in value template -->
<div {{ "attr" }}="{{ 'value' }}">Content</div>

<!-- ✓ VALID: Single quotes in name, double quotes in value template -->
<div {{ 'attr' }}='{{ "value" }}'>Content</div>

<!-- ✓ VALID: Mixed with static parts -->
<div data-{{ "id" }}="{{ 'name' }}">Content</div>
```

### Attribute Value Opposite-Quote Rule
Attribute *values* still follow the opposite-quote rule:

```html
<!-- ✓ VALID: Single quotes in template inside double-quoted value -->
<div class="{{ 'active' }}">Content</div>

<!-- ✗ INVALID: Double quotes in template inside double-quoted value -->
<div class="{{ "active" }}">Content</div>

<!-- ✓ VALID: Double quotes in template inside single-quoted value -->
<div class='{{ "active" }}'>Content</div>
```

## Real-World Examples

### User Profile Card
```html
<div class="profile-card"
     data-user-{{ user.id }}="active"
     data-role-{{ user.role }}="member">
    <h3>{{ user.name }}</h3>
    <span class="badge-{{ user.status }}">{{ user.status|title }}</span>
</div>
```

### HTMX-Powered Form
```html
<form hx-{{ form_method }}="/api/users/{{ user.id }}"
      hx-target="#result"
      hx-swap="outerHTML">
    <input type="text"
           name="username"
           hx-{{ validation_trigger }}="/validate/username">
    <button type="submit"
            {% if submitting %}disabled{% endif %}>
        Submit
    </button>
</form>
```

### Alpine.js Component
```html
<div x-data="{ tab: 'home' }">
    <button x-on:click="tab = '{{ tab_name }}'"
            x-bind:class="{ 'active': tab === '{{ tab_name }}' }"
            :{{ accessibility_attr }}="{{ tab_name }}">
        {{ tab_label }}
    </button>

    <div x-{{ show_directive }}="tab === '{{ tab_name }}'">
        {{ tab_content }}
    </div>
</div>
```

### Dynamic Data Attributes
```html
{% for item in items %}
    <div class="item"
         data-item-{{ item.id }}="{{ item.name }}"
         data-category-{{ item.category.slug }}="active"
         data-index-{{ forloop.counter }}="{{ forloop.counter }}">
        {{ item.name }}
    </div>
{% endfor %}
```

## Technical Details

### CFG Preservation
Dynamic attribute names maintain context-free grammar properties:

1. **Fixed Structure**: Attribute syntax follows fixed rules
2. **Character-Level Detection**: Template detection is purely syntactic
3. **No Context Sensitivity**: Parsing doesn't depend on surrounding elements
4. **Finite Vocabulary**: Template variables are finite per document

### Implementation

**Lexer** (`lexer.py`):
- `read_attribute_name()`: Reads static names with hyphens, colons, etc.
- `_attribute_name_has_template()`: Peeks ahead to detect templates
- `tokenize_dynamic_attribute_name()`: Collects mixed static/dynamic parts
- Produces `ATTR_NAME` or `ATTR_NAME_DYNAMIC` tokens

**Parser** (`parser.py`):
- `parse_attributes()`: Handles both token types
- Creates `Attribute` objects with `is_dynamic_name` flag

**AST** (`ast_nodes.py`):
- `Attribute` class enhanced with:
  - `name`: String (static or with template syntax)
  - `is_dynamic_name`: Boolean flag
  - `value`: Optional string (as before)

**Formatter** (`formatter.py`):
- Outputs attribute names as-is (template syntax preserved)
- Round-trip parsing maintains templates

## Testing

Comprehensive test suites verify:

### Phase 1: Hyphenated Attributes
- `test_hyphenated_attributes.py`
- data-*, aria-*, hx-*, x-* attributes
- Colons, dots, @ symbols

### Phase 2: Simple Dynamic Names
- `test_dynamic_attribute_names_phase2.py`
- `{{ attr }}="value"` patterns
- Template tags in names
- Boolean dynamic attributes
- Independent quote rules

### Phase 3: Mixed Dynamic Names
- `test_dynamic_attribute_names_phase3.py`
- `data-{{ id }}-item` patterns
- HTMX, Alpine.js, Vue.js examples
- Multiple dynamic parts
- Complex real-world templates

## Compatibility

### Backward Compatibility
✅ All existing RDTL templates continue to work
✅ Static attribute names unchanged
✅ Attribute value templates unchanged

### Framework Support
✅ **HTMX**: `hx-get`, `hx-post`, `hx-target`, etc.
✅ **Alpine.js**: `x-data`, `x-show`, `x-on:click`, etc.
✅ **Vue.js**: `:prop`, `@event`, `v-model`, etc.
✅ **HTML5**: `data-*`, `aria-*` attributes
✅ **Custom**: Any framework with dynamic attributes

## Performance

- **Lexer**: Single character lookahead for template detection
- **Parser**: No additional complexity for dynamic names
- **Formatter**: Direct string output (no re-parsing)
- **Round-Trip**: Parse → Format → Re-parse is idempotent

## Limitations

### Still Unsupported
The following remain unsupported (as before):
- Multi-file template inheritance
- Runtime-only constructs (`{% csrf_token %}`, `{% now %}`)
- Context-dependent scoping (`{% with %}`)

### By Design
These work as intended:
✅ Templates in attribute names
✅ Templates in attribute values
✅ Mixed static/dynamic parts
✅ Any quote combination in names
✅ Opposite-quote rule in values

## Examples

See test files for comprehensive examples:
- `test_hyphenated_attributes.py`
- `test_dynamic_attribute_names_phase2.py`
- `test_dynamic_attribute_names_phase3.py`
- `test_integration.py`

## Summary

Dynamic attribute names bring RDTL to parity with modern web development needs while maintaining its core strength: **context-free parseability for reliable tooling**.

Use cases include:
- ✅ HTMX-powered applications
- ✅ Alpine.js components
- ✅ Vue.js templates
- ✅ Dynamic data attributes
- ✅ Conditional attribute names
- ✅ Framework-agnostic dynamic HTML

All while preserving:
- ✅ Context-free grammar
- ✅ Reliable parsing
- ✅ Formatting and linting
- ✅ Static analysis capabilities
