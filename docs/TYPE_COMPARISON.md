"""Guide for using albu-spec to compare types between __init__ and InitSchema.

This document explains the type comparison functionality and how to use it
for validating type consistency in AlbumentationsX transforms.
"""

# Type Comparison Guide

## Overview

albu-spec provides semantic type comparison to validate that type annotations in `__init__` signatures match those in Pydantic `InitSchema` definitions.

## Why Semantic Comparison?

Simple string comparison of types doesn't work because:

```python
# These are semantically identical but look different:
int | float       # Modern Python union syntax
Union[int, float] # typing.Union syntax
float | int       # Different order, same meaning

# These are also equivalent:
int | None        # Modern optional
Optional[int]     # typing.Optional

# Literal values can be in any order:
Literal[1, 2, 3]
Literal[3, 2, 1]  # Same meaning
```

albu-spec handles all these cases correctly.

## Basic Usage

### Extract Raw Type Objects

```python
from albu_spec import get_init_param_type, get_init_schema_param_type
import albumentations as A

# Get type from __init__ signature
init_type = get_init_param_type(A.Blur, 'blur_limit')
print(init_type)  # tuple[int, int] | int (actual type object)

# Get type from InitSchema
schema_type = get_init_schema_param_type(A.Blur, 'blur_limit')
print(schema_type)  # tuple[int, int] | int (actual type object)
```

**Important**: These return **type objects**, not strings!

```python
# ❌ Don't do this:
if str(init_type) == str(schema_type):  # String comparison is fragile

# ✅ Do this:
from albu_spec import compare_types
if compare_types(init_type, schema_type):  # Semantic comparison
```

### Compare Types

```python
from albu_spec import compare_types

# Basic comparison
type1 = int | float
type2 = float | int
print(compare_types(type1, type2))  # True (order doesn't matter)

# With Optional
from typing import Optional
type1 = int | None
type2 = Optional[int]
print(compare_types(type1, type2))  # True (semantically equivalent)

# With Literal
from typing import Literal
type1 = Literal[1, 2, 3]
type2 = Literal[3, 2, 1]
print(compare_types(type1, type2))  # True (value order doesn't matter)
```

### Get Detailed Mismatch Info

```python
from albu_spec import get_type_mismatch

type1 = int
type2 = float

mismatch = get_type_mismatch(type1, type2)
if mismatch:
    print(f"Reason: {mismatch.reason}")
    print(f"Type 1: {mismatch.type1}")
    print(f"Type 2: {mismatch.type2}")
    print(f"Normalized 1: {mismatch.type1_normalized}")
    print(f"Normalized 2: {mismatch.type2_normalized}")
```

## Supported Type Comparisons

### 1. Union Types (Order Independent)

```python
from albu_spec import compare_types

# All of these are equivalent:
compare_types(int | float, float | int)  # True
compare_types(int | float | str, str | int | float)  # True

# Even with nested types:
compare_types(
    tuple[int, int] | int,
    int | tuple[int, int]
)  # True
```

### 2. Optional Variations

```python
from typing import Optional

# All equivalent:
compare_types(int | None, Optional[int])  # True
compare_types(None | int, Optional[int])  # True
compare_types(int | None, None | int)  # True
```

### 3. Literal Types (Value Order Independent)

```python
from typing import Literal

# Order doesn't matter:
compare_types(
    Literal[1, 2, 3],
    Literal[3, 2, 1]
)  # True

# Works with strings:
compare_types(
    Literal['a', 'b', 'c'],
    Literal['c', 'b', 'a']
)  # True

# Works with mixed types:
compare_types(
    Literal[1, 'a', 2.0],
    Literal[2.0, 1, 'a']
)  # True
```

### 4. Annotated Types (Metadata Ignored)

```python
from typing import Annotated

# Annotated metadata is ignored in comparison:
compare_types(
    Annotated[int, "some metadata"],
    int
)  # True

# Also works with complex types:
compare_types(
    Annotated[int | float, "constraint info"],
    float | int
)  # True
```

### 5. Generic Types (Nested Comparison)

```python
# Tuples:
compare_types(
    tuple[int, int],
    tuple[int, int]
)  # True

compare_types(
    tuple[int, float],
    tuple[int, int]
)  # False (element types differ)

# Lists:
compare_types(
    list[int],
    list[int]
)  # True

# Dicts:
compare_types(
    dict[str, int],
    dict[str, int]
)  # True

# Nested generics:
compare_types(
    dict[str, list[int]],
    dict[str, list[int]]
)  # True
```

### 6. Complex Combinations

```python
# Union of generics:
compare_types(
    tuple[int, int] | int | None,
    int | None | tuple[int, int]
)  # True

# Nested unions:
compare_types(
    dict[str, int | float],
    dict[str, float | int]
)  # True
```

## Common Patterns

### Check All Parameters in a Transform

```python
from albu_spec import (
    compare_types,
    get_common_param_names,
    get_init_param_type,
    get_init_schema_param_type,
)
import albumentations as A

def check_transform(transform_class):
    """Check all parameters in a transform."""
    mismatches = []

    # Get parameters present in both __init__ and InitSchema
    common_params = get_common_param_names(transform_class)

    for param_name in common_params:
        init_type = get_init_param_type(transform_class, param_name)
        schema_type = get_init_schema_param_type(transform_class, param_name)

        if not compare_types(init_type, schema_type):
            mismatches.append(param_name)

    return mismatches

# Example
mismatches = check_transform(A.Blur)
if mismatches:
    print(f"Parameters with type mismatches: {mismatches}")
```

### Generate Report for Multiple Transforms

```python
from albu_spec import get_type_mismatch

def generate_report(transforms):
    """Generate detailed report for multiple transforms."""
    report = []

    for transform_class in transforms:
        common_params = get_common_param_names(transform_class)

        for param_name in common_params:
            init_type = get_init_param_type(transform_class, param_name)
            schema_type = get_init_schema_param_type(transform_class, param_name)

            if not compare_types(init_type, schema_type):
                mismatch = get_type_mismatch(init_type, schema_type)
                report.append({
                    'transform': transform_class.__name__,
                    'parameter': param_name,
                    'init_type': init_type,
                    'schema_type': schema_type,
                    'reason': mismatch.reason if mismatch else 'Unknown',
                })

    return report

# Generate report
import albumentations as A
transforms = [A.Blur, A.Rotate, A.Affine]
report = generate_report(transforms)

# Print report
for item in report:
    print(f"{item['transform']}.{item['parameter']}: {item['reason']}")
```

## Edge Cases and Limitations

### 1. Forward References (Strings)

Forward references in `__init__` are automatically evaluated:

```python
# __init__ signature has:
def __init__(self, value: 'int | float'): ...  # String annotation

# albu-spec automatically evaluates it to:
int | float  # Actual type object
```

### 2. inspect.Parameter.empty

Parameters without type annotations:

```python
# If __init__ has no annotation:
def __init__(self, value): ...

# get_init_param_type returns:
inspect.Parameter.empty

# This only matches other empty annotations:
compare_types(inspect.Parameter.empty, inspect.Parameter.empty)  # True
compare_types(inspect.Parameter.empty, int)  # False
```

### 3. Type Aliases

Type aliases are resolved to their underlying types:

```python
# If InitSchema uses:
ScalarType = int | float

class InitSchema:
    value: ScalarType

# get_init_schema_param_type returns:
int | float  # Resolved alias
```

### 4. Custom Generic Types

Custom generic types are compared by origin and args:

```python
from typing import TypeVar, Generic

T = TypeVar('T')

class MyGeneric(Generic[T]):
    pass

# These match:
compare_types(MyGeneric[int], MyGeneric[int])  # True
compare_types(MyGeneric[int], MyGeneric[float])  # False
```

## Type Comparison Algorithm

The comparison algorithm:

1. **Unwrap Annotated types**: Extract inner type, ignore metadata
2. **Normalize None**: Handle `type(None)` and `None` as equivalent
3. **Check origins**: Compare type constructors (Union, tuple, list, etc.)
4. **For Union types**: Convert args to set, compare (order-independent)
5. **For Literal types**: Convert values to set, compare (order-independent)
6. **For generic types**: Recursively compare type arguments
7. **For basic types**: Direct equality comparison

## Performance Considerations

Type comparison is fast, but if you're checking thousands of parameters:

```python
import functools

@functools.lru_cache(maxsize=None)
def compare_types_cached(type1_str, type2_str):
    """Cache comparison results."""
    # Convert strings back to types and compare
    # (You'll need to implement string-to-type conversion)
    return compare_types(type1, type2)
```

## Debugging Type Comparisons

If types should match but don't:

```python
from albu_spec import get_type_mismatch
from typing import get_origin, get_args

def debug_types(type1, type2):
    """Debug why two types don't match."""
    print(f"Type 1: {type1}")
    print(f"Type 2: {type2}")
    print(f"Origin 1: {get_origin(type1)}")
    print(f"Origin 2: {get_origin(type2)}")
    print(f"Args 1: {get_args(type1)}")
    print(f"Args 2: {get_args(type2)}")

    mismatch = get_type_mismatch(type1, type2)
    if mismatch:
        print(f"\nMismatch reason: {mismatch.reason}")

# Example
debug_types(int | float, float | int)
```

## Testing Your Type Comparisons

When writing tests:

```python
import pytest
from albu_spec import compare_types

def test_union_order_independence():
    """Union order should not matter."""
    assert compare_types(int | float, float | int)

def test_optional_variations():
    """Optional variations should match."""
    from typing import Optional
    assert compare_types(int | None, Optional[int])

def test_literal_order_independence():
    """Literal value order should not matter."""
    from typing import Literal
    assert compare_types(Literal[1, 2, 3], Literal[3, 2, 1])
```

See `tests/test_type_comparison.py` for comprehensive examples.

## Related Documentation

- [Pre-Commit Guide](PRE_COMMIT_GUIDE.md) - Using type comparison in pre-commit hooks
- [Testing Guide](TESTING.md) - Testing strategies for type consistency
- [API Reference](../README.md) - Complete API documentation
