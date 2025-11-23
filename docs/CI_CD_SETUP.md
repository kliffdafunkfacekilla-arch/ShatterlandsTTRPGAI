# CI/CD Setup Guide

## Overview

This document explains how to set up and use the project's CI/CD quality gates:
1. **Pre-commit hooks** - Local code quality enforcement
2. **GitHub Actions** - Automated drift detection on PRs

---

## 1. Pre-Commit Hooks Setup

Pre-commit hooks run automatically before each commit to enforce code quality standards.

### Installation

```bash
# Install pre-commit
pip install pre-commit

# Install the git hooks
pre-commit install
```

### What Gets Checked

- **Black**: Code formatting (line length: 100)
- **isort**: Import statement ordering
- **flake8**: Linting and style guide enforcement
- **trailing-whitespace**: Removes trailing whitespace
- **mypy**: Static type checking (optional)
- **Model-Migration Drift**: Verifies ORM changes have migrations

### Running Manually

```bash
# Run on all files
pre-commit run --all-files

# Run on staged files only
pre-commit run

# Run specific hook
pre-commit run black --all-files
```

### Bypassing Hooks (Emergency Only)

```bash
# Skip pre-commit hooks (NOT RECOMMENDED)
git commit --no-verify -m "emergency fix"
```

### Configuration

Edit `.pre-commit-config.yaml` to customize:
- Hook versions
- Black/isort line length
- flake8 ignore rules
- File exclusions

---

## 2. GitHub Actions - Drift Detection

### What It Does

Automatically runs on:
- Pull requests touching `models.py` or Alembic migrations
- Pushes to `main` or `develop` branches

### Exit Codes

| Code | Meaning | Action |
|------|---------|--------|
| 0 | No drift detected | ✅ Pass |
| 1 | Warnings (non-blocking) | ⚠️ Pass with warnings |
| 2 | Drift detected | ❌ **FAIL BUILD** |

### When a PR Fails

If your PR triggers drift detection:

1. **Check the workflow logs** to see which models changed
2. **Generate a migration**:
   ```bash
   cd AI-TTRPG/monolith/modules/<module_name>
   alembic revision --autogenerate -m "add_field_to_model"
   ```
3. **Review the migration** for accuracy
4. **Commit the migration** to your PR:
   ```bash
   git add AI-TTRPG/monolith/modules/<module_name>/alembic/versions/*.py
   git commit -m "Add migration for model changes"
   git push
   ```

The workflow will re-run automatically and should pass.

---

## 3. Troubleshooting

### Pre-commit fails on existing code

If pre-commit fails on files you didn't change:

```bash
# Auto-fix formatting issues
pre-commit run --all-files

# Commit the auto-fixes
git add -u
git commit -m "Apply pre-commit auto-fixes"
```

### Drift detection false positive

If you believe the drift check is wrong:

1. Check `tools/model_migration_diff.py` output locally:
   ```bash
   python tools/model_migration_diff.py
   ```
2. Verify all migrations are committed
3. If needed, create an issue with workflow logs

### Skipping checks in special cases

Some scenarios where you might need to bypass:
- **Emergency hotfixes**: Use `--no-verify` (document in commit message)
- **Alembic migrations**: Already excluded from Black/isort
- **Generated code**: Add to exclusion patterns in configs

---

## 4. Best Practices

✅ **DO**:
- Run `pre-commit run --all-files` before creating a PR
- Generate migrations immediately after model changes
- Review auto-generated migrations for accuracy
- Keep migration messages descriptive

❌ **DON'T**:
- Bypass hooks without documenting why
- Modify migrations after they've been deployed
- Change models without creating migrations
- Commit large formatting changes mixed with logic changes

---

## 5. Quick Reference

```bash
# Setup (one-time)
pip install pre-commit
pre-commit install

# Before committing
pre-commit run --all-files

# After changing models
cd AI-TTRPG/monolith/modules/<module>
alembic revision --autogenerate -m "description"

# Check for drift manually
python tools/model_migration_diff.py
```

---

## Support

Questions or issues with CI/CD setup?
- Check workflow logs in GitHub Actions tab
- Run checks locally first for faster debugging
- Open an issue if automation is blocking valid changes
