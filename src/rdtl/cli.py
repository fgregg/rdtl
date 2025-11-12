#!/usr/bin/env python3
"""
RDTL Formatter CLI Tool

Format RDTL template files with consistent style.

Usage:
    rdtl-fmt template.html                 # Format and print to stdout
    rdtl-fmt template.html --check          # Check if formatted
    rdtl-fmt template.html --write          # Format in-place
    rdtl-fmt templates/*.html --write       # Format multiple files
    cat template.html | rdtl-fmt            # Read from stdin
"""

import re
import sys
from pathlib import Path

import click

from rdtl.formatter import FormatOptions, format_template
from rdtl.validator import validate_template


def format_file(
    file_path: Path,
    options: FormatOptions,
    check: bool = False,
    write: bool = False,
    verbose: bool = False,
) -> bool:
    """
    Format a single file.

    Returns:
        True if file is properly formatted (or was successfully formatted)
        False if file needs formatting (in check mode) or had errors
    """
    try:
        # Read file
        content = file_path.read_text()

        # Validate first
        is_valid, errors = validate_template(content, strict_html=True)
        if not is_valid:
            # Format validation errors like linter output: filename:line: message
            # Use relative path for cleaner output
            try:
                relative_path = file_path.relative_to(Path.cwd())
            except ValueError:
                relative_path = file_path

            for error in errors:
                # Extract line number from error message if present
                # Format: "Line X, col Y: message" -> "filename:X: message"
                line_match = re.match(r"Line (\d+), col \d+: (.+)", error)
                if line_match:
                    line_num, message = line_match.groups()
                    click.echo(
                        click.style(f"{relative_path}:{line_num}: ", fg="red")
                        + click.style("error: ", fg="red", bold=True)
                        + message,
                        err=True,
                    )
                else:
                    # No line number, just show filename and error
                    click.echo(
                        click.style(f"{relative_path}: ", fg="red")
                        + click.style("error: ", fg="red", bold=True)
                        + error,
                        err=True,
                    )
            return False

        # Format
        try:
            formatted = format_template(content, options)
        except Exception as e:
            click.echo(
                click.style(f"❌ {file_path}: Formatting error: {e}", fg="red"),
                err=True,
            )
            return False

        # Check mode: compare with original
        if check:
            if formatted == content:
                if verbose:
                    click.echo(
                        click.style(f"✓ {file_path}: Already formatted", fg="green")
                    )
                return True
            else:
                click.echo(click.style(f"❌ {file_path}: Needs formatting", fg="red"))
                return False

        # Write mode: update file
        if write:
            if formatted == content:
                if verbose:
                    click.echo(
                        click.style(f"✓ {file_path}: Already formatted", fg="green")
                    )
            else:
                file_path.write_text(formatted)
                click.echo(click.style(f"✓ {file_path}: Formatted", fg="green"))
            return True

        # Default: print to stdout
        click.echo(formatted, nl=False)
        return True

    except FileNotFoundError:
        click.echo(click.style(f"❌ {file_path}: File not found", fg="red"), err=True)
        return False
    except Exception as e:
        click.echo(click.style(f"❌ {file_path}: Error: {e}", fg="red"), err=True)
        return False


@click.command()
@click.argument(
    "files", nargs=-1, required=False, type=click.Path(exists=True, path_type=Path)
)
@click.option(
    "--check", is_flag=True, help="Check if files are formatted (exit non-zero if not)"
)
@click.option("--write", "-w", is_flag=True, help="Format files in-place")
@click.option(
    "--compact",
    is_flag=True,
    help="Use compact formatting style (2-space indent, minimal whitespace)",
)
@click.option(
    "--verbose-style",
    is_flag=True,
    help="Use verbose formatting style with blank lines",
)
@click.option(
    "--indent",
    type=int,
    metavar="N",
    help="Indentation size (default: 4 for normal, 2 for compact)",
)
@click.option("--tabs", is_flag=True, help="Use tabs for indentation instead of spaces")
@click.option(
    "--quotes",
    type=click.Choice(["double", "single"], case_sensitive=False),
    default="double",
    help="Quote style for attributes (default: double)",
)
@click.option(
    "--no-self-closing-slash",
    is_flag=True,
    help="Omit slash in self-closing tags (<br> instead of <br />)",
)
@click.option("-v", "--verbose", is_flag=True, help="Verbose output")
@click.version_option(version="0.1.0", prog_name="rdtl-fmt")
def main(
    files,
    check,
    write,
    compact,
    verbose_style,
    indent,
    tabs,
    quotes,
    no_self_closing_slash,
    verbose,
):
    """Format RDTL template files with consistent style.

    \b
    Examples:
      rdtl-fmt template.html                  # Format to stdout
      rdtl-fmt template.html --write          # Format in-place
      rdtl-fmt template.html --check          # Check if formatted
      rdtl-fmt templates/*.html --write       # Format multiple files
      rdtl-fmt template.html --compact        # Use compact style
      cat template.html | rdtl-fmt            # Read from stdin

    \b
    Formatting Options:
      Default style uses 4-space indentation with spaces in template tags.
      Use --compact for minimal whitespace (2-space indent, no spaces in tags).
      Use --tabs for tab indentation instead of spaces.
    """
    # Handle stdin when no files provided
    if not files:
        if check or write:
            raise click.UsageError(
                "--check and --write are not supported with stdin input"
            )
        content = sys.stdin.read()

        # Validate
        is_valid, errors = validate_template(content, strict_html=True)
        if not is_valid:
            # Format validation errors with standard linter format (stdin has no filename)
            for error in errors:
                line_match = re.match(r"Line (\d+), col \d+: (.+)", error)
                if line_match:
                    line_num, message = line_match.groups()
                    click.echo(
                        click.style(f"stdin:{line_num}: ", fg="red")
                        + click.style("error: ", fg="red", bold=True)
                        + message,
                        err=True,
                    )
                else:
                    click.echo(
                        click.style("stdin: ", fg="red")
                        + click.style("error: ", fg="red", bold=True)
                        + error,
                        err=True,
                    )
            sys.exit(1)

        # Format
        try:
            # Build formatting options (copied from below)
            if compact:
                options = FormatOptions(
                    indent_size=indent or 2,
                    use_tabs=tabs,
                    space_in_template_tags=False,
                    space_in_variables=False,
                    quotes=quotes,
                    self_closing_slash=not no_self_closing_slash,
                )
            elif verbose_style:
                options = FormatOptions(
                    indent_size=indent or 4,
                    use_tabs=tabs,
                    space_in_template_tags=True,
                    space_in_variables=True,
                    blank_line_before_block=True,
                    blank_line_after_block=True,
                    quotes=quotes,
                    self_closing_slash=not no_self_closing_slash,
                )
            else:
                options = FormatOptions(
                    indent_size=indent or 4,
                    use_tabs=tabs,
                    quotes=quotes,
                    self_closing_slash=not no_self_closing_slash,
                )

            formatted = format_template(content, options)
            click.echo(formatted, nl=False)
            sys.exit(0)
        except Exception as e:
            click.echo(click.style(f"❌ Formatting error: {e}", fg="red"), err=True)
            sys.exit(1)

    # Validate mutually exclusive options
    if check and write:
        raise click.UsageError("--check and --write are mutually exclusive")

    if compact and verbose_style:
        raise click.UsageError("--compact and --verbose-style are mutually exclusive")

    # Build formatting options
    if compact:
        options = FormatOptions(
            indent_size=indent or 2,
            use_tabs=tabs,
            space_in_template_tags=False,
            space_in_variables=False,
            quotes=quotes,
            self_closing_slash=not no_self_closing_slash,
        )
    elif verbose_style:
        options = FormatOptions(
            indent_size=indent or 4,
            use_tabs=tabs,
            space_in_template_tags=True,
            space_in_variables=True,
            blank_line_before_block=True,
            blank_line_after_block=True,
            quotes=quotes,
            self_closing_slash=not no_self_closing_slash,
        )
    else:
        options = FormatOptions(
            indent_size=indent or 4,
            use_tabs=tabs,
            quotes=quotes,
            self_closing_slash=not no_self_closing_slash,
        )

    # Process files
    all_ok = True
    for file_path in files:
        ok = format_file(file_path, options, check, write, verbose)
        if not ok:
            all_ok = False

    # Show development notice if there were errors
    if not all_ok:
        click.echo(
            "\n"
            + click.style("Note: ", fg="yellow", bold=True)
            + "This formatter is under active development. "
            "If you believe an error is incorrect, please report it at:\n"
            "https://github.com/fgregg/rdtl/issues",
            err=True,
        )

    # Exit code
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
