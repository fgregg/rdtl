# Pre-commit Setup Guide

This guide shows you how to set up RDTL's formatter and i18n linter as pre-commit hooks.

## Quick Start

1. **Install pre-commit** (if you haven't already):
   ```bash
   pip install pre-commit
   ```

2. **Create `.pre-commit-config.yaml`** in your project root:
   ```yaml
   repos:
     - repo: https://github.com/fgregg/rdtl
       rev: main  # Use 'main' for latest, or specific commit SHA/tag
       hooks:
         - id: rdtl-fmt
         - id: rdtl-i18n
   ```

   **Note on `rev` values:**
   - During active development: `rev: main` (tracks latest changes)
   - For stability: `rev: COMMIT_SHA` (specific commit)
   - After first release: `rev: v0.1.0` (stable version)

3. **Install the hooks**:
   ```bash
   pre-commit install
   ```

That's it! Now the hooks will run automatically on `git commit`.

## Configuration Options

### Format Specific Files

Only check templates in specific directories:

```yaml
repos:
  - repo: https://github.com/fgregg/rdtl
    rev: v0.1.0
    hooks:
      - id: rdtl-fmt
        files: ^templates/.*\.html$  # Only templates/ directory

      - id: rdtl-i18n
        files: ^myapp/templates/.*\.html$  # Specific app templates
```

### Exclude Files

Exclude certain files or directories:

```yaml
repos:
  - repo: https://github.com/fgregg/rdtl
    rev: v0.1.0
    hooks:
      - id: rdtl-fmt
        exclude: ^vendor/|^third_party/

      - id: rdtl-i18n
        exclude: ^templates/email/  # Skip email templates
```

### Formatter Options

Pass additional arguments to the formatter:

```yaml
repos:
  - repo: https://github.com/fgregg/rdtl
    rev: v0.1.0
    hooks:
      - id: rdtl-fmt
        args: [--compact]  # Use compact formatting style
```

Available formatter args:
- `--compact` - Use 2-space indent with minimal whitespace
- `--verbose-style` - Add blank lines around blocks
- `--indent=N` - Set custom indentation (default: 4)
- `--tabs` - Use tabs instead of spaces
- `--quotes=single` - Use single quotes (default: double)
- `--no-self-closing-slash` - Omit slash in void elements

### Running Hooks Manually

Run hooks on all files (pre-commit automatically finds all HTML files in your repo):
```bash
pre-commit run --all-files
```

Run specific hook:
```bash
pre-commit run rdtl-fmt --all-files
pre-commit run rdtl-i18n --all-files
```

Run on specific files:
```bash
pre-commit run --files templates/myfile.html
```

### Skip Hooks Temporarily

Skip hooks for a single commit:
```bash
git commit --no-verify
```

Skip specific hook:
```bash
SKIP=rdtl-i18n git commit
```

## Available Hooks

### `rdtl-fmt` - Template Formatter

Validates and checks formatting of RDTL templates:
- Ensures proper HTML structure
- Validates Django template syntax
- Checks for formatting inconsistencies

**Default behavior**: Checks formatting only (does not modify files)

To auto-format files, run manually:
```bash
rdtl-fmt templates/*.html --write
```

### `rdtl-i18n` - Internationalization Linter

Checks for user-visible text that isn't wrapped in translation tags:
- Detects untranslated text in HTML content
- Checks translatable attributes (placeholder, title, alt, aria-label)
- Excludes dynamic content, numbers, symbols, and emoji

**Excluded from checks**:
- Text inside `{% trans %}` or `{% blocktranslate %}` tags
- Script, style, pre, and code tags
- Variables and template comments
- Numeric values and currency
- UI symbols (arrows, bullets, checkmarks)
- Emoji

## Using During Active Development

RDTL is under active development. Here are options for early adopters:

### Option 1: Track Main Branch (Latest Features)

```yaml
repos:
  - repo: https://github.com/fgregg/rdtl
    rev: main
    hooks:
      - id: rdtl-i18n
```

**Pros**: Always get latest features and fixes
**Cons**: May have breaking changes

Update to latest: `pre-commit autoupdate`

### Option 2: Pin to Specific Commit (Stable)

```yaml
repos:
  - repo: https://github.com/fgregg/rdtl
    rev: abc123def456  # Use actual commit SHA
    hooks:
      - id: rdtl-i18n
```

**Pros**: Stable, reproducible builds
**Cons**: Need to manually update

Find latest commit: Visit https://github.com/fgregg/rdtl/commits/main

### Option 3: Local Development (For Contributors)

If you're contributing to RDTL or testing local changes:

```yaml
repos:
  - repo: local
    hooks:
      - id: rdtl-i18n
        name: RDTL i18n Linter
        entry: rdtl-i18n
        language: system
        types: [html]
```

Requires: `pip install -e /path/to/rdtl` in your environment

## FAQ

### How does pre-commit find my template files?

Pre-commit automatically searches your git repository for files matching the hook's `types` specification. The RDTL hooks use `types: [html]`, so pre-commit will:
1. Find all `.html` files tracked by git (or staged for commit)
2. Pass their paths to the `rdtl-fmt` or `rdtl-i18n` command
3. The command processes each file

**You don't need to specify template locations** - pre-commit handles file discovery automatically!

### Can I limit hooks to specific directories?

Yes! Use the `files` pattern to target specific directories:

```yaml
hooks:
  - id: rdtl-i18n
    files: ^myapp/templates/.*\.html$  # Only myapp/templates/
```

### Will it check files outside my templates directory?

Only if they're HTML files tracked by git. You can exclude paths:

```yaml
hooks:
  - id: rdtl-i18n
    exclude: ^vendor/|^node_modules/  # Skip these directories
```

## Troubleshooting

### Hook not running

Make sure hooks are installed:
```bash
pre-commit install
```

### False positives in i18n linter

If the linter incorrectly flags content:
1. Check if the text is truly user-visible
2. Report the issue: https://github.com/fgregg/rdtl/issues
3. Temporarily skip: `SKIP=rdtl-i18n git commit`

### Formatter errors on valid templates

The formatter is under active development. If you encounter errors:
1. Verify the template works with Django
2. Report the issue: https://github.com/fgregg/rdtl/issues
3. Temporarily skip: `SKIP=rdtl-fmt git commit`

## Complete Example

Here's a complete `.pre-commit-config.yaml` with multiple tools:

```yaml
repos:
  # RDTL tools
  - repo: https://github.com/fgregg/rdtl
    rev: v0.1.0
    hooks:
      - id: rdtl-fmt
        files: ^templates/.*\.html$

      - id: rdtl-i18n
        files: ^templates/.*\.html$
        exclude: ^templates/admin/

  # Python formatting
  - repo: https://github.com/psf/black
    rev: 23.12.1
    hooks:
      - id: black

  # Python imports
  - repo: https://github.com/pycqa/isort
    rev: 5.13.2
    hooks:
      - id: isort

  # General checks
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
      - id: check-merge-conflict
```

## CI/CD Integration

Run pre-commit in your CI pipeline:

```yaml
# .github/workflows/pre-commit.yml
name: Pre-commit

on: [push, pull_request]

jobs:
  pre-commit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - uses: pre-commit/action@v3.0.0
```

## Learn More

- [Pre-commit documentation](https://pre-commit.com/)
- [RDTL repository](https://github.com/fgregg/rdtl)
- [Report issues](https://github.com/fgregg/rdtl/issues)
