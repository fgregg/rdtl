#!/usr/bin/env python3
"""
Verify RDTL parser against grammar using Lark parser generator.

This script:
1. Loads the Lark grammar (generated from EBNF)
2. Parses test templates with both parsers
3. Compares results to find discrepancies
"""

import sys
from pathlib import Path
from typing import List, Tuple

try:
    from lark import Lark, Tree
    from lark.exceptions import LarkError
except ImportError:
    print("ERROR: lark-parser not installed")
    print("Install with: pip install lark-parser")
    sys.exit(1)

try:
    from rdtl.parser import parse as manual_parse
except ImportError:
    print("ERROR: Could not import RDTL parser")
    sys.exit(1)


class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'


def load_lark_grammar() -> Lark:
    """Load the Lark grammar from file."""
    # Grammar file is in src/rdtl/ relative to project root
    project_root = Path(__file__).parent.parent
    grammar_file = project_root / 'src' / 'rdtl' / 'rdtl_lark.lark'
    if not grammar_file.exists():
        raise FileNotFoundError(f"Grammar file not found: {grammar_file}")

    with open(grammar_file) as f:
        grammar = f.read()

    return Lark(grammar, start='document', parser='lalr')


def test_template_with_both_parsers(template: str, description: str, lark_parser: Lark) -> Tuple[bool, str]:
    """
    Parse template with both manual and generated parsers.
    Returns (success, message).
    """
    print(f"\n{Colors.BLUE}Testing:{Colors.RESET} {description}")
    print(f"  Template: {template[:60]}...")

    # Try manual parser
    manual_success = False
    manual_error = None
    try:
        manual_ast = manual_parse(template)
        manual_success = True
        print(f"  {Colors.GREEN}✓{Colors.RESET} Manual parser: Success")
    except Exception as e:
        manual_error = str(e)
        print(f"  {Colors.RED}✗{Colors.RESET} Manual parser: {manual_error[:50]}")

    # Try Lark parser
    lark_success = False
    lark_error = None
    try:
        lark_tree = lark_parser.parse(template)
        lark_success = True
        print(f"  {Colors.GREEN}✓{Colors.RESET} Lark parser: Success")
        # print(f"    Tree: {lark_tree.pretty()[:100]}")
    except LarkError as e:
        lark_error = str(e)
        print(f"  {Colors.RED}✗{Colors.RESET} Lark parser: {lark_error[:50]}")

    # Compare results
    if manual_success and lark_success:
        print(f"  {Colors.GREEN}✓✓{Colors.RESET} Both parsers agree: VALID")
        return True, "Agreement: VALID"
    elif not manual_success and not lark_success:
        print(f"  {Colors.GREEN}✓✓{Colors.RESET} Both parsers agree: INVALID")
        return True, "Agreement: INVALID"
    elif manual_success and not lark_success:
        print(f"  {Colors.YELLOW}⚠{Colors.RESET} Discrepancy: Manual accepts, Lark rejects")
        print(f"    → Grammar may be too strict or incomplete")
        return False, f"Discrepancy: Manual OK, Lark error: {lark_error}"
    else:  # lark_success and not manual_success
        print(f"  {Colors.YELLOW}⚠{Colors.RESET} Discrepancy: Lark accepts, Manual rejects")
        print(f"    → Implementation may be too strict or buggy")
        return False, f"Discrepancy: Lark OK, Manual error: {manual_error}"


def run_verification():
    """Run verification tests."""
    print(f"{Colors.BLUE}{'=' * 70}{Colors.RESET}")
    print(f"{Colors.BLUE}GRAMMAR-PARSER VERIFICATION WITH LARK{Colors.RESET}")
    print(f"{Colors.BLUE}{'=' * 70}{Colors.RESET}")

    # Load Lark grammar
    print(f"\nLoading Lark grammar from rdtl_lark.lark...")
    try:
        lark_parser = load_lark_grammar()
        print(f"{Colors.GREEN}✓{Colors.RESET} Grammar loaded successfully")
    except Exception as e:
        print(f"{Colors.RED}✗{Colors.RESET} Failed to load grammar: {e}")
        return 1

    # Test cases
    test_cases = [
        # Basic features
        ('<div>Hello</div>', "Simple HTML"),
        ('{{ variable }}', "Simple variable"),
        ('{{ variable|filter }}', "Variable with filter"),
        ('{% if condition %}yes{% endif %}', "Simple if block"),
        ('{% for x in items %}{{ x }}{% endfor %}', "Simple for loop"),

        # New features we added
        ('{% if field|length > 1 %}yes{% endif %}', "Filter in condition"),
        ('{% include "template.html" %}', "Simple include"),
        ('{% include "x" with a=b %}', "Include with context"),
        ('{% trans Hello %}', "Trans tag"),
        # Note: Custom tags require two-phase parsing, can't express in pure CFG
        # ('{% mytag %}', "Custom simple tag"),

        # Complex cases
        ('{% if a|length == b|length %}equal{% endif %}', "Filters on both sides"),
        ('<div class="{{ value }}">text</div>', "Template in attribute"),

        # Should fail
        ('{% if condition %}', "Unclosed if block"),
        ('<div>{% if x %}</div>{% endif %}', "Interleaved nesting"),
    ]

    results = []
    for template, description in test_cases:
        success, message = test_template_with_both_parsers(template, description, lark_parser)
        results.append((description, success, message))

    # Summary
    print(f"\n{Colors.BLUE}{'=' * 70}{Colors.RESET}")
    print(f"{Colors.BLUE}SUMMARY{Colors.RESET}")
    print(f"{Colors.BLUE}{'=' * 70}{Colors.RESET}\n")

    agreements = sum(1 for _, success, _ in results if success)
    total = len(results)

    print(f"Agreement rate: {agreements}/{total} ({100*agreements//total}%)\n")

    discrepancies = [(desc, msg) for desc, success, msg in results if not success]
    if discrepancies:
        print(f"{Colors.YELLOW}Discrepancies found:{Colors.RESET}")
        for desc, msg in discrepancies:
            print(f"  - {desc}")
            print(f"    {msg}")
    else:
        print(f"{Colors.GREEN}No discrepancies! Grammar and implementation are aligned.{Colors.RESET}")

    print(f"\n{Colors.BLUE}INTERPRETATION:{Colors.RESET}")
    print("• If both parsers agree (both accept or both reject): ✓ Good")
    print("• If manual accepts but Lark rejects: Grammar may be incomplete")
    print("• If Lark accepts but manual rejects: Implementation bug or too strict")

    return 0 if agreements == total else 1


def main():
    """Main entry point."""
    try:
        return run_verification()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        return 130
    except Exception as e:
        print(f"\n{Colors.RED}ERROR:{Colors.RESET} {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
