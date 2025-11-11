"""Test strict HTML mode."""

from rdtl.validator import validate_template

print("=" * 60)
print("TEST 1: Unclosed <p> tag (strict mode)")
print("=" * 60)
template1 = """
<div>
    <p>Content
</div>
"""
is_valid, errors = validate_template(template1, strict_html=True)
print(f"Valid: {is_valid}")
print(f"Errors: {errors}")
print()

print("=" * 60)
print("TEST 2: Unclosed <p> tag (lenient mode)")
print("=" * 60)
is_valid, errors = validate_template(template1, strict_html=False)
print(f"Valid: {is_valid}")
print(f"Errors: {errors}")
print()

print("=" * 60)
print("TEST 3: Misordered closing tags (strict mode)")
print("=" * 60)
template2 = """
<div>
    <p>
        <span>Text</p>
    </span>
</div>
"""
is_valid, errors = validate_template(template2, strict_html=True)
print(f"Valid: {is_valid}")
print(f"Errors: {errors}")
print()

print("=" * 60)
print("TEST 4: Properly nested (strict mode)")
print("=" * 60)
template3 = """
<div>
    <p>
        <span>Text</span>
    </p>
</div>
"""
is_valid, errors = validate_template(template3, strict_html=True)
print(f"Valid: {is_valid}")
print(f"Errors: {errors}")
print()

print("=" * 60)
print("TEST 5: Template block not closed before HTML (strict)")
print("=" * 60)
template4 = """
<div>
    {% if condition %}
        <p>Content</p>
</div>
{% endif %}
"""
is_valid, errors = validate_template(template4, strict_html=True)
print(f"Valid: {is_valid}")
print(f"Errors: {errors}")
print()

print("=" * 60)
print("TEST 6: Properly nested template and HTML (strict)")
print("=" * 60)
template5 = """
<div>
    {% if condition %}
        <p>Content</p>
    {% endif %}
</div>
"""
is_valid, errors = validate_template(template5, strict_html=True)
print(f"Valid: {is_valid}")
print(f"Errors: {errors}")
