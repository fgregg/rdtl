#!/usr/bin/env python3
"""
Verify relationship between grammar.ebnf and parser.py implementation.

This script checks:
1. Grammar rules have corresponding parser methods
2. Test coverage for each grammar feature
3. Round-trip consistency (parse -> format -> parse)
"""

import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Set

# Color codes for output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'

def check(condition: bool, label: str) -> bool:
    """Print check result and return condition."""
    if condition:
        print(f"{Colors.GREEN}✓{Colors.RESET} {label}")
    else:
        print(f"{Colors.RED}✗{Colors.RESET} {label}")
    return condition

def info(message: str):
    """Print info message."""
    print(f"{Colors.BLUE}ℹ{Colors.RESET} {message}")

def warn(message: str):
    """Print warning message."""
    print(f"{Colors.YELLOW}⚠{Colors.RESET} {message}")

def extract_grammar_productions(grammar_file: Path) -> Dict[str, str]:
    """Extract production rules from EBNF grammar."""
    rules = {}
    with open(grammar_file) as f:
        content = f.read()

    # Match EBNF productions: identifier = ... ;
    pattern = r'^(\w+)\s*=\s*([^;]+);'
    for match in re.finditer(pattern, content, re.MULTILINE):
        rule_name = match.group(1)
        rule_body = match.group(2).strip()
        rules[rule_name] = rule_body

    return rules

def extract_parser_methods(parser_file: Path) -> Set[str]:
    """Extract parsing method names from parser.py."""
    methods = set()
    with open(parser_file) as f:
        content = f.read()

    # Match method definitions
    pattern = r'def\s+(parse_\w+|tokenize_\w+)\s*\('
    for match in re.finditer(pattern, content):
        methods.add(match.group(1))

    return methods

def verify_grammar_coverage():
    """Verify critical grammar rules have implementations."""
    print("\n" + "=" * 70)
    print("1. GRAMMAR RULE COVERAGE")
    print("=" * 70 + "\n")

    # Define expected mappings (grammar rule -> parser method)
    expected_mappings = {
        'document': 'parse',  # Root method
        'element': 'parse_element',
        'html_element': 'parse_html_element',
        'template_variable': 'parse_variable',
        'if_block': 'parse_if_block',
        'for_block': 'parse_for_block',
        'include_tag': 'parse_include_tag',
        'expression': 'parse_expression',
        'expression_or_filtered': 'parse_expression_with_filters',
        'condition': 'parse_condition',
        'filter': 'parse_filter',
    }

    # Parser file is now in src/rdtl/
    project_root = Path(__file__).parent.parent
    parser_file = project_root / 'src' / 'rdtl' / 'parser.py'
    if not parser_file.exists():
        warn(f"parser.py not found at {parser_file}")
        return False

    parser_methods = extract_parser_methods(parser_file)

    all_found = True
    for rule, expected_method in expected_mappings.items():
        found = expected_method in parser_methods
        all_found = all_found and found
        check(found, f"{rule:30} -> {expected_method}")

    return all_found

def verify_new_features():
    """Verify recently added features are implemented."""
    print("\n" + "=" * 70)
    print("2. NEW FEATURES VERIFICATION")
    print("=" * 70 + "\n")

    features = [
        ("Filters in conditions", "parse_expression_with_filters", "parser.py"),
        ("Include with context", "context_vars =", "parser.py"),
        ("Trans raw content", "RAW_CONTENT_TAGS", "lexer.py"),
        ("Two-phase tag discovery", "_discover_block_tags", "validator.py"),
    ]

    all_found = True
    project_root = Path(__file__).parent.parent
    for feature_name, search_term, file_name in features:
        # Files are now in src/rdtl/
        file_path = project_root / 'src' / 'rdtl' / file_name
        if not file_path.exists():
            check(False, f"{feature_name:30} ({file_name} not found at {file_path})")
            all_found = False
            continue

        with open(file_path) as f:
            content = f.read()
            found = search_term in content
            all_found = all_found and found
            check(found, f"{feature_name:30} ({search_term} in {file_name})")

    return all_found

def verify_round_trip_tests():
    """Check for round-trip consistency tests."""
    print("\n" + "=" * 70)
    print("3. ROUND-TRIP TESTING")
    print("=" * 70 + "\n")

    test_cases = [
        ("{% if field|length > 1 %}yes{% endif %}", "Filters in conditions"),
        ('{% include "x" with a=b %}', "Include with context"),
        ("{% trans ✓ Hello! %}", "Trans with emoji"),
        ("{% mytag arg %}", "Custom simple tag"),
    ]

    info("Suggested round-trip test cases:")
    print()

    try:
        from rdtl.parser import parse
        from rdtl.formatter import format_template

        all_passed = True
        for template, description in test_cases:
            try:
                # Parse
                ast = parse(template)
                # Format
                formatted = format_template(template)
                # Parse again
                ast2 = parse(formatted)
                # Check idempotence
                passed = str(ast) == str(ast2)
                all_passed = all_passed and passed
                check(passed, f"{description:30} {template[:40]}")
            except Exception as e:
                check(False, f"{description:30} {str(e)[:40]}")
                all_passed = False

        return all_passed
    except ImportError as e:
        warn(f"Could not import parser/formatter: {e}")
        return False

def suggest_improvements():
    """Suggest improvements for better verification."""
    print("\n" + "=" * 70)
    print("4. SUGGESTED IMPROVEMENTS")
    print("=" * 70 + "\n")

    suggestions = [
        "Add docstring to each parse method referencing grammar rule",
        "Create test_grammar.py with one test per production rule",
        "Use pytest --cov to measure parser coverage",
        "Add property-based tests with hypothesis library",
        "Generate parser from EBNF using lark-parser for comparison",
        "Add comments in parser.py showing EBNF production rules",
    ]

    for i, suggestion in enumerate(suggestions, 1):
        print(f"{i}. {suggestion}")

def main():
    """Run all verification checks."""
    print(f"\n{Colors.BLUE}{'=' * 70}{Colors.RESET}")
    print(f"{Colors.BLUE}RDTL GRAMMAR-PARSER VERIFICATION{Colors.RESET}")
    print(f"{Colors.BLUE}{'=' * 70}{Colors.RESET}")

    results = []
    results.append(("Grammar Coverage", verify_grammar_coverage()))
    results.append(("New Features", verify_new_features()))
    results.append(("Round-Trip Tests", verify_round_trip_tests()))

    suggest_improvements()

    # Summary
    print(f"\n{Colors.BLUE}{'=' * 70}{Colors.RESET}")
    print(f"{Colors.BLUE}SUMMARY{Colors.RESET}")
    print(f"{Colors.BLUE}{'=' * 70}{Colors.RESET}\n")

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        check(result, name)

    print(f"\nTotal: {passed}/{total} checks passed")

    return 0 if passed == total else 1

if __name__ == '__main__':
    sys.exit(main())
