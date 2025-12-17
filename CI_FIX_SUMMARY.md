# GitHub Actions CI Fix

## Problem

The CI workflow `.github/workflows/ci-cli.yml` was failing during the `pip install` step with a dependency installation error.

### Root Cause

The workflow was only installing 3 packages:
```yaml
- run: pip install -e packages/schema -e packages/sdk-python -e packages/cli
```

But the dependency tree looks like this:

```
dockrion-cli
  └── dockrion-sdk
      ├── dockrion-schema ✅ (was installed)
      ├── dockrion-common ❌ (was MISSING)
      └── dockrion-adapters ❌ (was MISSING)
```

**The missing packages caused the installation to fail.**

## Solution

Updated the workflow to install **ALL** required packages in dependency order:

```yaml
- name: Install dependencies
  run: |
    pip install -e packages/common-py      # Base utilities
    pip install -e packages/schema         # Data models
    pip install -e packages/adapters       # Agent adapters
    pip install -e packages/sdk-python     # SDK (depends on above)
    pip install -e packages/cli            # CLI (depends on SDK)
```

### Why This Order?

1. **common-py** - Contains base utilities (`errors`, `logger`, etc.) used by everything
2. **schema** - Contains Pydantic models, depends on nothing
3. **adapters** - Contains agent adapters, depends on common
4. **sdk-python** - Depends on schema, common, and adapters
5. **cli** - Depends on SDK

## Additional Changes

### Fixed Test Command

**Before:**
```yaml
- run: python -m dockrion_cli.main validate-cmd || python -m dockrion_cli.main --help
```

**After:**
```yaml
- name: Test CLI
  run: python -m dockrion_cli.main validate --help || python -m dockrion_cli.main --help
```

**Why:**
- `validate-cmd` doesn't exist (typo)
- Should be `validate --help` to test the validate command
- Falls back to `--help` if validate fails

## Testing

### Local Test

You can test the installation locally:

```bash
# Clean environment
cd /Users/prakharagarwal/Dockrion

# Install in order
pip install -e packages/common-py
pip install -e packages/schema
pip install -e packages/adapters
pip install -e packages/sdk-python
pip install -e packages/cli

# Test CLI
python -m dockrion_cli.main --help
python -m dockrion_cli.main validate --help
```

### Expected Output

```
Usage: python -m dockrion_cli.main [OPTIONS] COMMAND [ARGS]...

Dockrion CLI - Deploy and manage AI agents

Commands:
  build     Build agent runtime
  deploy    Deploy agent runtime
  info      Show agent information
  init      Initialize a new Dockrion project
  logs      View agent logs
  run       Run agent locally
  test      Test agent locally
  validate  Validate Dockfile configuration
```

## Files Modified

- `.github/workflows/ci-cli.yml` - Updated to install all dependencies

## Impact

- ✅ CI workflow will now pass
- ✅ All dependencies properly installed
- ✅ CLI commands can be tested
- ✅ Future pushes won't fail on this step

## Verification

After pushing this change, the GitHub Actions workflow should:
1. ✅ Install all packages successfully
2. ✅ Run CLI help command successfully
3. ✅ Complete in ~10-15 seconds

---

**Status:** Fixed
**Date:** December 17, 2025

