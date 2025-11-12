# Quick Start: Pre-commit Hooks

Set up RDTL's formatter and i18n linter to run automatically on every commit.

## Installation (3 steps)

1. **Install pre-commit**:
   ```bash
   pip install pre-commit
   ```

2. **Create `.pre-commit-config.yaml`** in your project root:
   ```yaml
   repos:
     - repo: https://github.com/fgregg/rdtl
       rev: v0.1.0
       hooks:
         - id: rdtl-fmt      # Check template formatting
         - id: rdtl-i18n     # Check for untranslated text
   ```

3. **Install the hooks**:
   ```bash
   pre-commit install
   ```

Done! The hooks will now run automatically on `git commit`.

## What the Hooks Do

### `rdtl-fmt`
- Validates Django template syntax
- Checks HTML structure
- Ensures consistent formatting
- **Does not modify files** (checks only)

### `rdtl-i18n`
- Finds untranslated user-visible text
- Checks buttons, labels, paragraphs, etc.
- Verifies translatable attributes
- Excludes symbols, numbers, and emoji

## Common Commands

```bash
# Run on all files
pre-commit run --all-files

# Run specific hook
pre-commit run rdtl-fmt --all-files

# Skip hooks for one commit
git commit --no-verify

# Update hooks to latest version
pre-commit autoupdate
```

## See Full Documentation

For advanced configuration, CI/CD integration, and troubleshooting, see [PRE_COMMIT.md](PRE_COMMIT.md).
