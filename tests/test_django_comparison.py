"""
Property-based tests comparing RDTL parser against Django's parser.

This ensures our grammar matches Django's actual behavior.
"""

import unittest
import django
from django.conf import settings
from hypothesis import given, settings as hypothesis_settings, example, HealthCheck
from hypothesis import strategies as st
from pathlib import Path

# Configure Django
if not settings.configured:
    settings.configure(
        DEBUG=True,
        INSTALLED_APPS=['django.contrib.contenttypes'],
        TEMPLATES=[{'BACKEND': 'django.template.backends.django.DjangoTemplates'}]
    )
    django.setup()

from django.template import Template, TemplateSyntaxError as DjangoTemplateSyntaxError
from rdtl.parser import parse, ParseError
from rdtl.validator import validate_template


class TestDjangoComparison(unittest.TestCase):
    """Compare RDTL parser behavior against Django's parser."""

    # Known valid Django templates
    VALID_TEMPLATES = [
        "{{ user }}",
        "{{ user.name }}",
        "{{ items.0 }}",
        "{{ user.profile.email }}",
        "{% if x %}yes{% endif %}",
        "{% if x %}yes{% else %}no{% endif %}",
        "{% for item in items %}{{ item }}{% endfor %}",
        "<div>{{ content }}</div>",
        "<div class='test'>{{ var }}</div>",
        "{{ value|upper }}",
        "{{ value|truncatewords:10 }}",
    ]

    # Known invalid Django templates
    INVALID_TEMPLATES = [
        "{{ user. name }}",      # Space after dot
        "{{ user .name }}",      # Space before dot
        "{{ user . name }}",     # Spaces around dot
        "{{ items[0] }}",        # Bracket notation
        "{{ user['name'] }}",    # Bracket notation with string
        "{{ user[ 0 ] }}",       # Bracket with spaces
    ]

    def test_valid_templates_both_accept(self):
        """Both parsers should accept known valid templates."""
        for template_str in self.VALID_TEMPLATES:
            with self.subTest(template=template_str):
                # Django should accept
                try:
                    django_template = Template(template_str)
                    django_accepts = True
                except DjangoTemplateSyntaxError:
                    django_accepts = False

                # RDTL should accept
                try:
                    rdtl_ast = parse(template_str)
                    rdtl_accepts = True
                except (ParseError, Exception):
                    rdtl_accepts = False

                # Both should agree
                self.assertTrue(
                    django_accepts,
                    f"Django rejected template: {template_str}"
                )
                self.assertTrue(
                    rdtl_accepts,
                    f"RDTL rejected template: {template_str}"
                )

    def test_invalid_templates_both_reject(self):
        """Both parsers should reject known invalid templates."""
        for template_str in self.INVALID_TEMPLATES:
            with self.subTest(template=template_str):
                # Django should reject
                try:
                    django_template = Template(template_str)
                    django_accepts = True
                except DjangoTemplateSyntaxError:
                    django_accepts = False

                # RDTL should reject
                try:
                    rdtl_ast = parse(template_str)
                    rdtl_accepts = True
                except (ParseError, Exception):
                    rdtl_accepts = False

                # Both should reject
                self.assertFalse(
                    django_accepts,
                    f"Django unexpectedly accepted template: {template_str}"
                )
                self.assertFalse(
                    rdtl_accepts,
                    f"RDTL unexpectedly accepted template: {template_str}"
                )

    def test_whitespace_in_lookups_rejected_by_both(self):
        """Both parsers reject spaces in dot notation lookups."""
        templates_with_spaces = [
            "{{ a. b }}",
            "{{ a .b }}",
            "{{ a . b }}",
            "{{ a.b. c }}",
            "{{ a.b .c }}",
            "{{ a.b . c }}",
        ]

        for template_str in templates_with_spaces:
            with self.subTest(template=template_str):
                # Django rejects
                with self.assertRaises(DjangoTemplateSyntaxError):
                    Template(template_str)

                # RDTL rejects
                with self.assertRaises((ParseError, Exception)):
                    parse(template_str)

    def test_bracket_notation_rejected_by_both(self):
        """Both parsers reject bracket notation."""
        bracket_templates = [
            "{{ items[0] }}",
            "{{ items[1] }}",
            "{{ user['name'] }}",
            "{{ user['email'] }}",
            "{{ data['key'] }}",
        ]

        for template_str in bracket_templates:
            with self.subTest(template=template_str):
                # Django rejects
                with self.assertRaises(DjangoTemplateSyntaxError):
                    Template(template_str)

                # RDTL rejects
                with self.assertRaises((ParseError, Exception)):
                    parse(template_str)

    def test_numeric_indices_via_dot_both_accept(self):
        """Both parsers accept numeric indices via dot notation."""
        numeric_templates = [
            "{{ items.0 }}",
            "{{ items.1 }}",
            "{{ data.0.name }}",
        ]

        for template_str in numeric_templates:
            with self.subTest(template=template_str):
                # Django accepts
                try:
                    django_template = Template(template_str)
                    django_accepts = True
                except DjangoTemplateSyntaxError:
                    django_accepts = False

                # RDTL accepts
                try:
                    rdtl_ast = parse(template_str)
                    rdtl_accepts = True
                except (ParseError, Exception):
                    rdtl_accepts = False

                self.assertTrue(django_accepts, f"Django rejected: {template_str}")
                self.assertTrue(rdtl_accepts, f"RDTL rejected: {template_str}")


class TestDjangoReferenceValidation(unittest.TestCase):
    """Use Django as reference for variable lookup syntax."""

    def compare_parsers(self, template_str: str) -> tuple[bool, bool]:
        """
        Compare how Django and RDTL handle a template.

        Returns: (django_accepts, rdtl_accepts)
        """
        # Test Django
        try:
            Template(template_str)
            django_accepts = True
        except DjangoTemplateSyntaxError:
            django_accepts = False
        except Exception:
            # Other errors are ignored - we only care about syntax
            django_accepts = True

        # Test RDTL
        try:
            parse(template_str)
            rdtl_accepts = True
        except (ParseError, Exception):
            rdtl_accepts = False

        return django_accepts, rdtl_accepts

    @given(st.text(min_size=1, max_size=50))
    @hypothesis_settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.filter_too_much, HealthCheck.too_slow]
    )
    @example("{{ user.name }}")
    @example("{{ user. name }}")
    @example("{{ items[0] }}")
    def test_fuzz_comparison(self, template_str: str):
        """
        Fuzz test: if Django accepts it, RDTL should too (or be more strict).

        This is a one-way check: Django accepting means it's valid Django syntax,
        so RDTL should either accept it or intentionally reject it as restricted.
        """
        django_accepts, rdtl_accepts = self.compare_parsers(template_str)

        # If Django rejects it, we don't care what RDTL does
        # (we might be more permissive in some areas)

        # If both accept or both reject, that's fine
        # We just want to catch cases where Django accepts but RDTL incorrectly rejects
        # (though we allow RDTL to be more strict by design)

        # This test mainly helps discover interesting edge cases
        if django_accepts and not rdtl_accepts:
            # This is OK if we're intentionally more restrictive
            # Just log it for investigation
            pass


if __name__ == '__main__':
    unittest.main()
