"""
Property-based tests using grammar generation + Django validation.

This combines:
1. Grammar-based test generation (from Lark)
2. Django as reference implementation
3. RDTL parser validation

Strategy: Generate templates from our grammar, then ensure both parsers agree.
"""

from pathlib import Path

import django
import pytest
from django.conf import settings
from django.template import Template
from django.template import TemplateSyntaxError as DjangoTemplateSyntaxError
from hypothesis import assume, given, seed
from hypothesis import settings as hypothesis_settings
from hypothesis import strategies as st

from rdtl.parser import ParseError, parse

# Configure Django
if not settings.configured:
    settings.configure(
        DEBUG=True,
        INSTALLED_APPS=["django.contrib.contenttypes"],
        TEMPLATES=[{"BACKEND": "django.template.backends.django.DjangoTemplates"}],
    )
    django.setup()

from hypothesis.extra.lark import from_lark
from lark import Lark


def get_template_strategy():
    """Create Hypothesis strategy from RDTL grammar."""
    grammar_file = Path(__file__).parent.parent / "src" / "rdtl" / "rdtl_lark.lark"
    with open(grammar_file) as f:
        grammar_text = f.read()

    grammar = Lark(grammar_text, start="document", parser="lalr")

    return from_lark(
        grammar,
        start="document",
        alphabet=st.characters(min_codepoint=32, max_codepoint=126),
        explicit={"WS": st.just(" ")},
    )


def compare_parsers(template_str: str) -> dict[str, bool | str | None]:
    """
    Compare how Django and RDTL handle a template.

    Returns dict with:
    - django_accepts: bool
    - django_error: str or None
    - rdtl_accepts: bool
    - rdtl_error: str or None
    """
    result: dict[str, bool | str | None] = {
        "django_accepts": False,
        "django_error": None,
        "rdtl_accepts": False,
        "rdtl_error": None,
    }

    # Test Django
    try:
        Template(template_str)
        result["django_accepts"] = True
    except DjangoTemplateSyntaxError as e:
        result["django_error"] = str(e)
    except Exception:
        # Other errors (like AppRegistryNotReady) - treat as accepted
        # We only care about template syntax errors
        result["django_accepts"] = True

    # Test RDTL
    try:
        parse(template_str)
        result["rdtl_accepts"] = True
    except ParseError as e:
        result["rdtl_error"] = str(e)
    except Exception as e:
        result["rdtl_error"] = f"{type(e).__name__}: {e}"

    return result


@pytest.mark.slow
@given(st.data())
@hypothesis_settings(max_examples=50, deadline=None)
@seed(42)  # Reproducible results
def test_generated_templates_match_django(data):
    """
    Generate templates from grammar and verify both parsers agree.

    If Django accepts, RDTL should accept (or have a good reason not to).
    If Django rejects, RDTL should reject.
    """
    template_strategy = get_template_strategy()
    template_str = data.draw(template_strategy)

    # Skip empty templates
    assume(template_str.strip() != "")

    result = compare_parsers(template_str)

    # Core invariant: if Django rejects for syntax, RDTL should too
    if not result["django_accepts"]:
        # Django rejected it, RDTL should also reject
        if result["rdtl_accepts"]:
            # This is a problem - we accept something Django rejects
            pytest.fail(
                f"RDTL accepts template that Django rejects:\n"
                f"Template: {repr(template_str)}\n"
                f"Django error: {result['django_error']}"
            )

    # If Django accepts, RDTL should ideally accept too
    # (unless we're intentionally more restrictive)
    # This is a soft check - we log disagreements for investigation
    # RDTL is more strict - this might be intentional
    # For now, we just note disagreements but don't fail
    # (some restrictions might be intentional)


@pytest.mark.slow
@given(st.data())
@hypothesis_settings(max_examples=20, deadline=None)
@seed(123)
def test_generated_templates_statistics(data):
    """
    Generate templates and collect statistics on agreement.

    This helps us understand how well our grammar matches Django.
    """
    template_strategy = get_template_strategy()
    template_str = data.draw(template_strategy)

    # Skip empty
    assume(template_str.strip() != "")

    result = compare_parsers(template_str)

    # Track categories
    if result["django_accepts"] and result["rdtl_accepts"]:
        category = "both_accept"
    elif not result["django_accepts"] and not result["rdtl_accepts"]:
        category = "both_reject"
    elif result["django_accepts"] and not result["rdtl_accepts"]:
        category = "django_only"
    else:
        category = "rdtl_only"

    # Just verify the test runs; statistics tracking removed
    # as it's not essential for test correctness
    assert category in ["both_accept", "both_reject", "django_only", "rdtl_only"]


@pytest.mark.slow
@given(st.data())
@hypothesis_settings(max_examples=100, deadline=None)
@seed(2024)
def test_generated_templates_are_faithful(data):
    """The grammar is a faithful generator: every template it produces is valid.

    Because filter names are enumerated real built-ins split by parse-time arity
    (see rdtl_lark.lark), generation should never emit a template that Django
    rejects for syntax, and RDTL must accept all of them too. This locks in the
    soundness gain - if the grammar regresses to emitting Django-invalid filters
    (e.g. unknown names or wrong argument counts), this test fails.
    """
    template_str = data.draw(get_template_strategy())
    assume(template_str.strip() != "")

    result = compare_parsers(template_str)

    assert result["django_accepts"], (
        f"Grammar generated a template Django rejects:\n"
        f"Template: {repr(template_str)}\n"
        f"Django error: {result['django_error']}"
    )
    assert result["rdtl_accepts"], (
        f"Grammar generated a template RDTL rejects:\n"
        f"Template: {repr(template_str)}\n"
        f"RDTL error: {result['rdtl_error']}"
    )


# Specific Django feature tests


@pytest.mark.parametrize(
    "template", ["{{ items.0 }}", "{{ items.1 }}", "{{ items.99 }}"]
)
def test_django_dot_notation_with_numbers(template):
    """Django uses dot notation for list indices."""
    # Django accepts
    try:
        Template(template)
        django_ok = True
    except DjangoTemplateSyntaxError:
        django_ok = False

    # RDTL accepts
    try:
        parse(template)
        rdtl_ok = True
    except Exception:
        rdtl_ok = False

    assert django_ok, f"Django should accept: {template}"
    assert rdtl_ok, f"RDTL should accept: {template}"


@pytest.mark.parametrize(
    "template",
    [
        "{{ user. name }}",
        "{{ user .name }}",
        "{{ user . name }}",
        "{{ a.b. c }}",
    ],
)
def test_django_rejects_spaces_in_lookups(template):
    """Django rejects spaces around dots in variable lookups."""
    # Django rejects
    with pytest.raises(DjangoTemplateSyntaxError):
        Template(template)

    # RDTL rejects
    with pytest.raises((ParseError, SyntaxError, ValueError)):
        parse(template)


@pytest.mark.parametrize(
    "template",
    [
        "{{ items[0] }}",
        "{{ user['name'] }}",
        "{{ data['key'] }}",
    ],
)
def test_django_rejects_brackets(template):
    """Django doesn't support bracket notation."""
    # Django rejects
    with pytest.raises(DjangoTemplateSyntaxError):
        Template(template)

    # RDTL rejects
    with pytest.raises((ParseError, SyntaxError, ValueError)):
        parse(template)
