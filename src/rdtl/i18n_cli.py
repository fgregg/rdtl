#!/usr/bin/env python3
"""
CLI for i18n linting of RDTL templates.

Usage:
    rdtl-i18n template.html
    rdtl-i18n templates/**/*.html
    cat template.html | rdtl-i18n
"""

import sys
from pathlib import Path

import click

from rdtl.i18n_linter import lint_template


def get_relative_path(file_path: Path) -> Path:
    """Get path relative to current directory, or absolute if not relative."""
    try:
        return file_path.relative_to(Path.cwd())
    except ValueError:
        # File is not relative to cwd, return as-is
        return file_path


@click.command()
@click.argument(
    "files",
    nargs=-1,
    required=False,
    type=click.Path(exists=True, path_type=Path),
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Show detailed output",
)
def main(files: tuple[Path, ...], verbose: bool):
    """
    Check RDTL templates for untranslated user-visible text.

    Scans templates and reports any user-visible text that is not wrapped
    in {% trans %} or {% blocktranslate %} tags.

    Examples:
        rdtl-i18n template.html
        rdtl-i18n templates/**/*.html
        cat template.html | rdtl-i18n
    """
    if not files:
        # Read from stdin
        content = sys.stdin.read()
        issues = lint_template(content)

        if issues:
            for issue in issues:
                # Use different colors for validation errors vs i18n issues
                if issue.context in ("Validator", "Parser"):
                    # Validation/parser errors in red
                    if issue.line is not None:
                        location = f"stdin:{issue.line}: "
                    else:
                        location = "stdin: "
                    click.echo(
                        click.style(location, fg="red")
                        + click.style("error: ", fg="red", bold=True)
                        + issue.message,
                        err=True,
                    )
                else:
                    # i18n issues in cyan
                    click.echo(f"  • {issue}", err=True)
            click.echo(
                "\n"
                + click.style("Note: ", fg="yellow", bold=True)
                + "RDTL is under active development. Please report issues at:\n"
                + "https://github.com/fgregg/rdtl/issues",
                err=True,
            )
            sys.exit(1)
        else:
            if verbose:
                click.echo(click.style("✓ No i18n issues found", fg="green"))
            sys.exit(0)

    # Process files
    total_i18n_issues = 0
    total_validation_errors = 0
    files_with_issues = 0

    for file_path in files:
        if not file_path.is_file():
            click.echo(
                click.style(f"⚠ Skipping non-file: {file_path}", fg="yellow"),
                err=True,
            )
            continue

        try:
            content = file_path.read_text()
            issues = lint_template(content)

            if issues:
                files_with_issues += 1

                for issue in issues:
                    # Format as filename:line: message (standard linter format)
                    # Use relative path for cleaner output
                    relative_path = get_relative_path(file_path)

                    if issue.line is not None:
                        location = f"{relative_path}:{issue.line}: "
                    else:
                        location = f"{relative_path}: "

                    # Use different colors for validation errors vs i18n issues
                    if issue.context in ("Validator", "Parser"):
                        # Validation/parser errors in red
                        total_validation_errors += 1
                        click.echo(
                            click.style(location, fg="red")
                            + click.style("error: ", fg="red", bold=True)
                            + issue.message,
                            err=True,
                        )
                    else:
                        # i18n issues in cyan
                        total_i18n_issues += 1
                        click.echo(
                            click.style(location, fg="cyan")
                            + f"{issue.message}: {issue.text!r}",
                            err=True,
                        )
            else:
                if verbose:
                    click.echo(click.style(f"✓ {file_path}: No issues", fg="green"))

        except Exception as e:
            click.echo(
                click.style(f"❌ Error processing {file_path}: {e}", fg="red"),
                err=True,
            )
            sys.exit(1)

    # Summary
    if total_validation_errors > 0 or total_i18n_issues > 0:
        summary_parts = []
        if total_validation_errors > 0:
            summary_parts.append(f"{total_validation_errors} validation error(s)")
        if total_i18n_issues > 0:
            summary_parts.append(f"{total_i18n_issues} i18n issue(s)")

        click.echo(
            f"\n❌ Found {', '.join(summary_parts)} in {files_with_issues} file(s)",
            err=True,
        )

        # Show development notice only once at the end
        click.echo(
            "\n"
            + click.style("Note: ", fg="yellow", bold=True)
            + "RDTL is under active development. Please report issues at:\n"
            + "https://github.com/fgregg/rdtl/issues",
            err=True,
        )
        sys.exit(1)
    else:
        click.echo(f"✓ All {len(files)} file(s) passed i18n checks")
        sys.exit(0)


if __name__ == "__main__":
    main()
