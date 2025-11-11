# CLI Improvements with Click

We've migrated the RDTL formatter CLI from argparse to Click, a modern and user-friendly command-line interface framework.

## Benefits of Using Click

### 1. **Cleaner, More Readable Code**

**Before (argparse)**:
```python
parser = argparse.ArgumentParser(
    description="Format RDTL template files",
    formatter_class=argparse.RawDescriptionHelpFormatter,
    epilog="..."
)

parser.add_argument('files', nargs='+', type=Path, help='Template files to format')
action_group = parser.add_mutually_exclusive_group()
action_group.add_argument('--check', action='store_true', help='Check if files are formatted')
action_group.add_argument('--write', action='store_true', help='Format files in-place')
# ... many more lines
args = parser.parse_args()
```

**After (click)**:
```python
@click.command()
@click.argument('files', nargs=-1, required=True, type=click.Path(exists=True, path_type=Path))
@click.option('--check', is_flag=True, help='Check if files are formatted')
@click.option('--write', '-w', is_flag=True, help='Format files in-place')
@click.version_option(version='0.1.0', prog_name='rdtl-fmt')
def main(files, check, write, ...):
    """Format RDTL template files with consistent style."""
```

### 2. **Better Error Handling**

Click provides clearer error messages:

```bash
$ rdtl-fmt --check --write test.html
Error: --check and --write are mutually exclusive
```

### 3. **Colored Output**

Click makes it easy to add colors for better UX:

```python
click.echo(click.style(f"✓ {file_path}: Formatted", fg='green'))
click.echo(click.style(f"❌ {file_path}: Error", fg='red'), err=True)
```

Result:
- ✓ Success messages in **green**
- ❌ Error messages in **red** (sent to stderr)

### 4. **Built-in Version Flag**

Click automatically handles `--version`:

```python
@click.version_option(version='0.1.0', prog_name='rdtl-fmt')
```

```bash
$ rdtl-fmt --version
rdtl-fmt, version 0.1.0
```

### 5. **Short Option Aliases**

Easy to add short flags:

```python
@click.option('--write', '-w', is_flag=True, help='Format files in-place')
```

```bash
$ rdtl-fmt test.html -w  # Same as --write
```

### 6. **Better Help Formatting**

Click provides cleaner help output with proper alignment and grouping:

```bash
$ rdtl-fmt --help
Usage: rdtl-fmt [OPTIONS] FILES...

  Format RDTL template files with consistent style.

  Examples:
    rdtl-fmt template.html                  # Format to stdout
    rdtl-fmt template.html --write          # Format in-place
    rdtl-fmt template.html --check          # Check if formatted

Options:
  --check                   Check if files are formatted
  -w, --write               Format files in-place
  --compact                 Use compact formatting style
  --quotes [double|single]  Quote style for attributes
  --version                 Show the version and exit.
  --help                    Show this message and exit.
```

### 7. **Type Validation**

Click handles type validation automatically:

```python
@click.option('--indent', type=int, metavar='N', help='Indentation size')
@click.option('--quotes', type=click.Choice(['double', 'single']))
```

Invalid input is caught with helpful errors:

```bash
$ rdtl-fmt test.html --indent abc
Error: Invalid value for '--indent': 'abc' is not a valid integer.

$ rdtl-fmt test.html --quotes triple
Error: Invalid value for '--quotes': 'triple' is not one of 'double', 'single'.
```

### 8. **Path Validation**

Click validates file paths at the CLI level:

```python
@click.argument('files', type=click.Path(exists=True, path_type=Path))
```

```bash
$ rdtl-fmt nonexistent.html
Error: Invalid value for 'FILES...': Path 'nonexistent.html' does not exist.
```

## Feature Parity

All original argparse features are preserved:

✅ Format to stdout (default)
✅ `--check` mode (check if formatted, exit non-zero if not)
✅ `--write` mode (format in-place)
✅ `--compact` style (minimal whitespace)
✅ `--verbose-style` (extra blank lines)
✅ `--indent N` (custom indentation size)
✅ `--tabs` (use tabs instead of spaces)
✅ `--quotes [double|single]` (quote style)
✅ `--no-self-closing-slash` (omit trailing slash in void elements)
✅ `-v, --verbose` (verbose output)
✅ Multiple file support with glob patterns

## Usage Examples

### Basic Formatting

```bash
# Format to stdout
rdtl-fmt template.html

# Format in-place
rdtl-fmt template.html --write

# Check if formatted (CI/CD)
rdtl-fmt template.html --check
```

### Style Options

```bash
# Compact style (2-space indent, no spaces in tags)
rdtl-fmt template.html --compact

# Custom indentation
rdtl-fmt template.html --indent 2

# Use tabs
rdtl-fmt template.html --tabs

# Single quotes for attributes
rdtl-fmt template.html --quotes single
```

### Multiple Files

```bash
# Format all templates in directory
rdtl-fmt templates/*.html --write

# Check multiple files
rdtl-fmt src/**/*.html --check
```

### Verbose Output

```bash
# Show which files were formatted
rdtl-fmt templates/*.html --write --verbose

# Output:
# ✓ templates/base.html: Formatted
# ✓ templates/index.html: Already formatted
# ✓ templates/about.html: Formatted
```

## Installation

Click is now a runtime dependency:

```toml
# pyproject.toml
dependencies = [
    "click>=8.0",
]
```

Install with:

```bash
pip install rdtl
```

Or for development:

```bash
pip install -e ".[dev]"
```

## Testing

All CLI functionality tested:

```bash
# Test help
rdtl-fmt --help

# Test version
rdtl-fmt --version

# Test formatting
rdtl-fmt test.html

# Test check mode
rdtl-fmt test.html --check

# Test write mode
rdtl-fmt test.html --write --verbose

# Test styles
rdtl-fmt test.html --compact
rdtl-fmt test.html --quotes single

# Test error handling
rdtl-fmt test.html --check --write  # Error: mutually exclusive
```

## Migration Notes

For users upgrading from argparse version:

- **No breaking changes** - All flags and options work the same
- **New feature**: `-w` short flag for `--write`
- **Improved**: Better error messages and colored output
- **Improved**: Automatic file path validation

## Summary

Click provides:
- ✅ Cleaner, more maintainable code
- ✅ Better error messages
- ✅ Colored output for better UX
- ✅ Built-in version handling
- ✅ Type validation
- ✅ Path validation
- ✅ Better help formatting
- ✅ Short option aliases

All while maintaining 100% feature parity with the original argparse implementation!
