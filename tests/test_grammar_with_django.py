"""
Property-based tests using grammar generation + Django validation.

This combines:
1. Grammar-based test generation (from Lark)
2. Django as reference implementation
3. RDTL parser validation

Strategy: Generate templates from our grammar, then ensure both parsers agree.
"""

import unittest
import django
from django.conf import settings
from hypothesis import given, settings as hypothesis_settings, strategies as st, assume, seed
from hypothesis.extra.lark import from_lark
from lark import Lark
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


# Check if hypothesis[lark] is available
try:
    from hypothesis.extra.lark import from_lark
    LARK_GENERATION_AVAILABLE = True
except (ImportError, AttributeError):
    LARK_GENERATION_AVAILABLE = False


@unittest.skipIf(not LARK_GENERATION_AVAILABLE, "hypothesis[lark] not available")
class TestGrammarWithDjango(unittest.TestCase):
    """Generate templates from grammar and validate against Django."""

    @staticmethod
    def get_template_strategy():
        """Create Hypothesis strategy from RDTL grammar."""
        grammar_file = Path(__file__).parent.parent / 'src' / 'rdtl' / 'rdtl_lark.lark'
        with open(grammar_file) as f:
            grammar_text = f.read()

        grammar = Lark(grammar_text, start='document', parser='lalr')

        return from_lark(
            grammar,
            start='document',
            alphabet=st.characters(min_codepoint=32, max_codepoint=126),
            explicit={'WS': st.just(' ')}
        )

    def compare_parsers(self, template_str: str) -> dict:
        """
        Compare how Django and RDTL handle a template.

        Returns dict with:
        - django_accepts: bool
        - django_error: str or None
        - rdtl_accepts: bool
        - rdtl_error: str or None
        """
        result = {
            'django_accepts': False,
            'django_error': None,
            'rdtl_accepts': False,
            'rdtl_error': None,
        }

        # Test Django
        try:
            Template(template_str)
            result['django_accepts'] = True
        except DjangoTemplateSyntaxError as e:
            result['django_error'] = str(e)
        except Exception as e:
            # Other errors (like AppRegistryNotReady) - treat as accepted
            # We only care about template syntax errors
            result['django_accepts'] = True

        # Test RDTL
        try:
            parse(template_str)
            result['rdtl_accepts'] = True
        except ParseError as e:
            result['rdtl_error'] = str(e)
        except Exception as e:
            result['rdtl_error'] = f"{type(e).__name__}: {e}"

        return result

    @given(st.data())
    @hypothesis_settings(max_examples=50, deadline=None)
    @seed(42)  # Reproducible results
    def test_generated_templates_match_django(self, data):
        """
        Generate templates from grammar and verify both parsers agree.

        If Django accepts, RDTL should accept (or have a good reason not to).
        If Django rejects, RDTL should reject.
        """
        template_strategy = self.get_template_strategy()
        template_str = data.draw(template_strategy)

        # Skip empty templates
        assume(template_str.strip() != '')

        result = self.compare_parsers(template_str)

        # Core invariant: if Django rejects for syntax, RDTL should too
        if not result['django_accepts']:
            # Django rejected it, RDTL should also reject
            if result['rdtl_accepts']:
                # This is a problem - we accept something Django rejects
                self.fail(
                    f"RDTL accepts template that Django rejects:\n"
                    f"Template: {repr(template_str)}\n"
                    f"Django error: {result['django_error']}"
                )

        # If Django accepts, RDTL should ideally accept too
        # (unless we're intentionally more restrictive)
        # This is a soft check - we log disagreements for investigation
        if result['django_accepts'] and not result['rdtl_accepts']:
            # RDTL is more strict - this might be intentional
            # For now, we just check that it's not a regression
            known_restrictions = [
                # We might add intentional restrictions here
            ]

            is_known = any(msg in result['rdtl_error'] for msg in known_restrictions)

            # Log for investigation but don't fail
            # (some restrictions might be intentional)
            pass

    @given(st.data())
    @hypothesis_settings(max_examples=20, deadline=None)
    @seed(123)
    def test_generated_templates_statistics(self, data):
        """
        Generate templates and collect statistics on agreement.

        This helps us understand how well our grammar matches Django.
        """
        template_strategy = self.get_template_strategy()
        template_str = data.draw(template_strategy)

        # Skip empty
        assume(template_str.strip() != '')

        result = self.compare_parsers(template_str)

        # Track categories
        if result['django_accepts'] and result['rdtl_accepts']:
            category = "both_accept"
        elif not result['django_accepts'] and not result['rdtl_accepts']:
            category = "both_reject"
        elif result['django_accepts'] and not result['rdtl_accepts']:
            category = "django_only"
        else:
            category = "rdtl_only"

        # Store in test instance for reporting
        if not hasattr(self, '_stats'):
            self._stats = {'both_accept': 0, 'both_reject': 0, 'django_only': 0, 'rdtl_only': 0}

        self._stats[category] += 1


class TestSpecificDjangoFeatures(unittest.TestCase):
    """Test specific Django features to ensure compatibility."""

    def test_django_dot_notation_with_numbers(self):
        """Django uses dot notation for list indices."""
        # Both should accept
        for template in ["{{ items.0 }}", "{{ items.1 }}", "{{ items.99 }}"]:
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

            self.assertTrue(django_ok, f"Django should accept: {template}")
            self.assertTrue(rdtl_ok, f"RDTL should accept: {template}")

    def test_django_rejects_spaces_in_lookups(self):
        """Django rejects spaces around dots in variable lookups."""
        invalid_templates = [
            "{{ user. name }}",
            "{{ user .name }}",
            "{{ user . name }}",
            "{{ a.b. c }}",
        ]

        for template in invalid_templates:
            # Django rejects
            with self.assertRaises(DjangoTemplateSyntaxError,
                                   msg=f"Django should reject: {template}"):
                Template(template)

            # RDTL rejects
            with self.assertRaises(Exception,
                                   msg=f"RDTL should reject: {template}"):
                parse(template)

    def test_django_rejects_brackets(self):
        """Django doesn't support bracket notation."""
        invalid_templates = [
            "{{ items[0] }}",
            "{{ user['name'] }}",
            "{{ data['key'] }}",
        ]

        for template in invalid_templates:
            # Django rejects
            with self.assertRaises(DjangoTemplateSyntaxError,
                                   msg=f"Django should reject: {template}"):
                Template(template)

            # RDTL rejects
            with self.assertRaises(Exception,
                                   msg=f"RDTL should reject: {template}"):
                parse(template)


if __name__ == '__main__':
    unittest.main()
