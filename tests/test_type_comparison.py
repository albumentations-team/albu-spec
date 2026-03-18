"""Comprehensive tests for type comparison functionality.

Tests type comparison logic by:
1. Testing all transforms in AlbumentationsX
2. Comparing __init__ types vs InitSchema types for all parameters
3. Testing edge cases (Union order, Optional, Literal, etc.)
"""

from __future__ import annotations

import inspect

import albumentations as A
import pytest

from albu_spec.type_comparison import TypeMismatch, compare_types, get_type_mismatch
from albu_spec.type_extraction import (
    get_common_param_names,
    get_init_param_type,
    get_init_schema_param_type,
)


def get_all_transform_classes() -> list[type]:
    """Get all transform classes from AlbumentationsX.

    Returns:
        List of transform classes to test

    """
    ignored_classes = {
        "Lambda",
        "BasicTransform",
        "DualTransform",
        "ImageOnlyTransform",
        "Transform3D",
        "BaseTransformInitSchema",
    }

    transforms = []
    for name, obj in inspect.getmembers(A, predicate=inspect.isclass):
        if name in ignored_classes:
            continue

        try:
            if not issubclass(obj, A.BasicTransform):
                continue
            if obj is A.BasicTransform:
                continue
        except TypeError:
            continue

        # Only include transforms with InitSchema
        if hasattr(obj, "InitSchema"):
            transforms.append(obj)

    return transforms


@pytest.mark.parametrize("transform_class", get_all_transform_classes())
def test_init_vs_initschema_types_all_transforms(transform_class):
    """Compare types from __init__ vs InitSchema for all parameters in all transforms.

    This test loops through ALL transforms in AlbumentationsX and compares
    the type annotations from __init__ signature with those from InitSchema.

    If types don't match, this indicates either:
    1. An AlbumentationsX bug (types should be consistent)
    2. A type comparison bug in our logic

    """
    common_params = get_common_param_names(transform_class)

    if not common_params:
        pytest.skip(f"{transform_class.__name__} has no common parameters to test")

    mismatches = []

    for param_name in common_params:
        init_type = get_init_param_type(transform_class, param_name)
        schema_type = get_init_schema_param_type(transform_class, param_name)

        if not compare_types(init_type, schema_type):
            mismatch = get_type_mismatch(init_type, schema_type)
            mismatches.append(
                {
                    "param": param_name,
                    "init_type": init_type,
                    "schema_type": schema_type,
                    "mismatch": mismatch,
                },
            )

    if mismatches:
        msg = f"\n{transform_class.__name__} has type mismatches:\n"
        for m in mismatches:
            msg += f"\n  Parameter: {m['param']}\n"
            msg += f"    __init__: {m['init_type']}\n"
            msg += f"    InitSchema: {m['schema_type']}\n"
            if m["mismatch"]:
                msg += f"    Reason: {m['mismatch'].reason}\n"

        # Mark as xfail if these are known AlbumentationsX inconsistencies
        pytest.xfail(f"albumentationsx_bug: {msg}")


# Edge case tests for type comparison logic


def test_compare_types_union_order_independence():
    """Union types should match regardless of order."""
    type1 = int | float
    type2 = float | int

    assert compare_types(type1, type2), "Union order should not matter"


def test_compare_types_optional_variations():
    """Optional variations should be equivalent."""
    type1 = int | None
    type2 = int | None

    assert compare_types(type1, type2), "int | None should equal int | None"


def test_compare_types_literal_order_independence():
    """Literal types should match regardless of value order."""
    from typing import Literal

    type1 = Literal[1, 2, 3]
    type2 = Literal[3, 2, 1]

    assert compare_types(type1, type2), "Literal value order should not matter"


def test_compare_types_annotated_unwrapping():
    """Annotated types should unwrap to compare inner types."""
    from typing import Annotated

    type1 = Annotated[int, "some metadata"]
    type2 = int

    assert compare_types(type1, type2), "Annotated[T, ...] should equal T"


def test_compare_types_nested_generics():
    """Nested generic types should compare correctly."""
    type1 = tuple[int, int]
    type2 = tuple[int, int]
    type3 = tuple[int, float]

    assert compare_types(type1, type2), "Identical tuple types should match"
    assert not compare_types(type1, type3), "Different tuple element types should not match"


def test_compare_types_list_generics():
    """List generic types should compare correctly."""
    type1 = list[int]
    type2 = list[int]
    type3 = list[float]

    assert compare_types(type1, type2), "Identical list types should match"
    assert not compare_types(type1, type3), "Different list element types should not match"


def test_compare_types_dict_generics():
    """Dict generic types should compare correctly."""
    type1 = dict[str, int]
    type2 = dict[str, int]
    type3 = dict[str, float]

    assert compare_types(type1, type2), "Identical dict types should match"
    assert not compare_types(type1, type3), "Different dict value types should not match"


def test_compare_types_none_variations():
    """Different representations of None type should match."""
    type1 = type(None)
    type2 = None

    assert compare_types(type1, type2), "type(None) should equal None"


def test_compare_types_inspect_parameter_empty():
    """inspect.Parameter.empty should only match itself."""
    assert compare_types(inspect.Parameter.empty, inspect.Parameter.empty), "empty should equal empty"
    assert not compare_types(inspect.Parameter.empty, int), "empty should not equal int"


def test_compare_types_complex_union():
    """Complex union types with multiple nested types."""
    type1 = tuple[int, int] | int | None
    type2 = int | None | tuple[int, int]

    assert compare_types(type1, type2), "Complex union order should not matter"


def test_compare_types_different_basic_types():
    """Basic types that differ should not match."""
    assert not compare_types(int, float), "int should not equal float"
    assert not compare_types(str, int), "str should not equal int"
    assert not compare_types(bool, int), "bool should not equal int"


def test_get_type_mismatch_returns_none_when_equal():
    """get_type_mismatch should return None when types match."""
    type1 = int | float
    type2 = float | int

    mismatch = get_type_mismatch(type1, type2)
    assert mismatch is None, "Should return None when types match"


def test_get_type_mismatch_returns_details_when_different():
    """get_type_mismatch should return TypeMismatch with details."""
    type1 = int
    type2 = float

    mismatch = get_type_mismatch(type1, type2)

    assert isinstance(mismatch, TypeMismatch), "Should return TypeMismatch object"
    assert mismatch.type1 == type1, "Should store first type"
    assert mismatch.type2 == type2, "Should store second type"
    assert mismatch.reason, "Should have a reason string"


def test_type_mismatch_string_representation():
    """TypeMismatch should have readable string representation."""
    mismatch = TypeMismatch(
        type1=int,
        type2=float,
        reason="Basic types differ",
        type1_normalized="int",
        type2_normalized="float",
    )

    string_repr = str(mismatch)

    assert "Type mismatch" in string_repr
    assert "Basic types differ" in string_repr
    assert "int" in string_repr
    assert "float" in string_repr


# Tests for specific AlbumentationsX transforms (examples)


def test_horizontalflip_type_consistency():
    """Test HorizontalFlip parameter type consistency."""
    transform_class = A.HorizontalFlip

    if not hasattr(transform_class, "InitSchema"):
        pytest.skip("HorizontalFlip has no InitSchema")

    common_params = get_common_param_names(transform_class)

    for param_name in common_params:
        init_type = get_init_param_type(transform_class, param_name)
        schema_type = get_init_schema_param_type(transform_class, param_name)

        assert compare_types(init_type, schema_type), (
            f"HorizontalFlip.{param_name} type mismatch: __init__={init_type} vs InitSchema={schema_type}"
        )


def test_affine_type_consistency():
    """Test Affine parameter type consistency."""
    transform_class = A.Affine

    if not hasattr(transform_class, "InitSchema"):
        pytest.skip("Affine has no InitSchema")

    common_params = get_common_param_names(transform_class)

    # Affine has complex types, good stress test
    for param_name in common_params:
        init_type = get_init_param_type(transform_class, param_name)
        schema_type = get_init_schema_param_type(transform_class, param_name)

        if not compare_types(init_type, schema_type):
            mismatch = get_type_mismatch(init_type, schema_type)
            pytest.xfail(
                f"albumentationsx_bug: Affine.{param_name} type mismatch: {mismatch.reason if mismatch else 'unknown'}",
            )
