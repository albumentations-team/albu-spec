"""Guide for creating pre-commit hooks for AlbumentationsX using albu-spec.

This guide shows how to use albu-spec to validate type consistency between
__init__ signatures and InitSchema in AlbumentationsX transforms.
"""

# Pre-Commit Hook Guide for AlbumentationsX

## Overview

albu-spec provides utilities to validate type consistency between transform `__init__` signatures and their Pydantic `InitSchema` definitions. This is essential for maintaining consistency in AlbumentationsX.

## Why Type Consistency Matters

AlbumentationsX transforms have **two sources of truth** for parameter types:

1. **`__init__` signature** - What developers see when instantiating transforms
2. **`InitSchema` (Pydantic)** - What validates parameters at runtime

These **must match** or you get:
- ❌ Runtime errors when valid types are rejected
- ❌ Silent acceptance of invalid types
- ❌ Confusing error messages
- ❌ IDE autocomplete showing wrong types

## Installation

In your AlbumentationsX development environment:

```bash
pip install albu-spec
```

## Basic Usage

### Check a Single Transform

```python
from albu_spec import (
    get_init_param_type,
    get_init_schema_param_type,
    compare_types,
    get_common_param_names,
)
import albumentations as A

def check_transform(transform_class):
    """Check type consistency for a single transform."""
    mismatches = []

    # Get parameters present in both __init__ and InitSchema
    common_params = get_common_param_names(transform_class)

    for param_name in common_params:
        # Extract raw type objects (not strings)
        init_type = get_init_param_type(transform_class, param_name)
        schema_type = get_init_schema_param_type(transform_class, param_name)

        # Semantic comparison (handles Union order, Optional, etc.)
        if not compare_types(init_type, schema_type):
            mismatches.append({
                'param': param_name,
                'init_type': init_type,
                'schema_type': schema_type,
            })

    return mismatches

# Example
mismatches = check_transform(A.Blur)
if mismatches:
    print(f"❌ Blur has type mismatches: {mismatches}")
else:
    print("✅ Blur types are consistent")
```

### Get Detailed Mismatch Information

```python
from albu_spec import get_type_mismatch

def check_with_details(transform_class, param_name):
    """Get detailed information about type mismatches."""
    init_type = get_init_param_type(transform_class, param_name)
    schema_type = get_init_schema_param_type(transform_class, param_name)

    mismatch = get_type_mismatch(init_type, schema_type)
    if mismatch:
        print(f"Type Mismatch in {transform_class.__name__}.{param_name}")
        print(f"  __init__:    {mismatch.type1}")
        print(f"  InitSchema:  {mismatch.type2}")
        print(f"  Reason:      {mismatch.reason}")
```

## Pre-Commit Hook Implementation

### Option 1: Python Script

Create `.pre-commit-hooks/check_types.py`:

```python
#!/usr/bin/env python
"""Pre-commit hook to check type consistency in AlbumentationsX transforms."""

import sys
import inspect
from pathlib import Path

import albumentations as A
from albu_spec import (
    compare_types,
    get_common_param_names,
    get_init_param_type,
    get_init_schema_param_type,
    get_type_mismatch,
)


def get_all_transforms():
    """Get all transform classes with InitSchema."""
    transforms = []
    for name, obj in inspect.getmembers(A, predicate=inspect.isclass):
        try:
            if issubclass(obj, A.BasicTransform) and obj is not A.BasicTransform:
                if hasattr(obj, 'InitSchema'):
                    transforms.append(obj)
        except TypeError:
            continue
    return transforms


def check_transform_types(transform_class):
    """Check type consistency for a transform."""
    mismatches = []
    common_params = get_common_param_names(transform_class)

    for param_name in common_params:
        try:
            init_type = get_init_param_type(transform_class, param_name)
            schema_type = get_init_schema_param_type(transform_class, param_name)

            if not compare_types(init_type, schema_type):
                mismatch = get_type_mismatch(init_type, schema_type)
                mismatches.append({
                    'param': param_name,
                    'init_type': init_type,
                    'schema_type': schema_type,
                    'reason': mismatch.reason if mismatch else 'Unknown',
                })
        except (ValueError, AttributeError) as e:
            # Skip parameters that can't be extracted
            continue

    return mismatches


def main():
    """Run type consistency checks."""
    print("Checking type consistency in AlbumentationsX transforms...")

    all_transforms = get_all_transforms()
    failing_transforms = {}

    for transform_class in all_transforms:
        mismatches = check_transform_types(transform_class)
        if mismatches:
            failing_transforms[transform_class.__name__] = mismatches

    if failing_transforms:
        print(f"\n❌ Found type inconsistencies in {len(failing_transforms)} transforms:\n")

        for transform_name, mismatches in failing_transforms.items():
            print(f"  {transform_name}:")
            for m in mismatches:
                print(f"    • {m['param']}: {m['reason']}")
                print(f"      __init__:    {m['init_type']}")
                print(f"      InitSchema:  {m['schema_type']}")

        print("\n⚠️  Please fix type inconsistencies before committing.")
        return 1

    print(f"\n✅ All {len(all_transforms)} transforms have consistent types!")
    return 0


if __name__ == '__main__':
    sys.exit(main())
```

Make it executable:
```bash
chmod +x .pre-commit-hooks/check_types.py
```

### Option 2: Using pre-commit Framework

Add to `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: local
    hooks:
      - id: check-transform-types
        name: Check Transform Type Consistency
        entry: python .pre-commit-hooks/check_types.py
        language: system
        pass_filenames: false
        always_run: true
```

### Option 3: Git Hook (Simple)

Create `.git/hooks/pre-commit`:

```bash
#!/bin/bash

echo "Checking AlbumentationsX transform type consistency..."

python -c "
import sys
from check_types import main  # Your check script
sys.exit(main())
"

if [ $? -ne 0 ]; then
    echo "❌ Pre-commit check failed. Fix type inconsistencies and try again."
    exit 1
fi

echo "✅ Pre-commit checks passed!"
```

## Selective Checking (Modified Files Only)

If you want to check only modified transforms:

```python
import subprocess
from pathlib import Path

def get_modified_transforms():
    """Get transform classes from modified files."""
    # Get modified Python files
    result = subprocess.run(
        ['git', 'diff', '--cached', '--name-only', '--diff-filter=ACM'],
        capture_output=True,
        text=True,
    )

    modified_files = result.stdout.strip().split('\n')
    python_files = [f for f in modified_files if f.endswith('.py')]

    # Extract transform names from file paths
    # Example: albumentations/transforms/blur.py -> check Blur transform
    # You'll need to implement this based on your project structure

    return transform_classes


def main():
    """Check only modified transforms."""
    modified = get_modified_transforms()

    if not modified:
        print("✅ No transforms modified, skipping check")
        return 0

    print(f"Checking {len(modified)} modified transforms...")
    # ... rest of checking logic
```

## Common Type Mismatches

### int vs float

**Problem**: `__init__` says `int` but InitSchema says `float`

```python
# __init__
def __init__(self, value: int): ...

# InitSchema
class InitSchema:
    value: float  # ❌ Mismatch!
```

**Fix**: Decide which is correct and update both to match.

### Union Order

**Good News**: albu-spec handles this automatically!

```python
# These are considered equal:
int | float  ==  float | int  # ✅ No error
```

### Optional Variations

**Good News**: albu-spec handles this automatically!

```python
# These are considered equal:
int | None  ==  Optional[int]  # ✅ No error
```

### list vs tuple

**Problem**: Collection types must match exactly

```python
# __init__
values: list[int]  # ❌ Mismatch with tuple[int, int, int, int]

# InitSchema
values: tuple[int, int, int, int]
```

**Fix**: Decide on the correct collection type.

## Handling Known Issues

If you have known type inconsistencies that you plan to fix later, you can add them to an allowlist:

```python
KNOWN_ISSUES = {
    'Affine': {'translate_px'},  # int vs float mismatch
    'AdvancedBlur': {'rotate_limit'},
}

def should_skip(transform_name, param_name):
    """Check if this is a known issue."""
    return (
        transform_name in KNOWN_ISSUES and
        param_name in KNOWN_ISSUES[transform_name]
    )

# In your check function:
if should_skip(transform_class.__name__, param_name):
    continue  # Skip this known issue
```

## Testing Your Hook

Before committing, test your hook:

```bash
# Run manually
python .pre-commit-hooks/check_types.py

# Test with pre-commit framework
pre-commit run check-transform-types --all-files

# Test git hook
git commit --no-verify  # Skip hooks (for testing)
git commit              # Run with hooks
```

## Integration with CI/CD

Add to your CI workflow (GitHub Actions example):

```yaml
name: Type Consistency Check

on: [push, pull_request]

jobs:
  check-types:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.9'

      - name: Install dependencies
        run: |
          pip install albumentationsx albu-spec

      - name: Check type consistency
        run: python .pre-commit-hooks/check_types.py
```

## Performance Optimization

For large codebases, cache results:

```python
import functools

@functools.lru_cache(maxsize=None)
def check_transform_cached(transform_class_name):
    """Cache check results to avoid redundant checks."""
    transform_class = getattr(A, transform_class_name)
    return check_transform_types(transform_class)
```

## Troubleshooting

### "Cannot get signature for __init__"

Some transforms use decorators that hide signatures. This is usually fine - the check will skip those parameters.

### "Parameter not found in InitSchema"

Parameter exists in `__init__` but not in `InitSchema`. This might be:
- Inherited parameter (like `p`)
- Parameter that shouldn't be validated

Check if this is intentional.

### False Positives

If you get false positives (types that should match but don't), please:
1. Check if it's a known edge case
2. File an issue with albu-spec
3. Add to your allowlist temporarily

## Best Practices

1. **Run locally before pushing**: Catch issues early
2. **Keep allowlist small**: Fix issues, don't just skip them
3. **Document known issues**: Explain why each allowlist entry exists
4. **Update regularly**: Remove fixed issues from allowlist
5. **Check in CI**: Don't rely only on local hooks

## Example: Complete Pre-Commit Script

See `example_type_comparison.py` in the albu-spec repository for a complete working example.

## Support

- **albu-spec issues**: https://github.com/albumentations-team/albu-spec/issues
- **AlbumentationsX issues**: https://github.com/albumentations-team/AlbumentationsX/issues
