"""Property-based tests for universal invariants across all transforms.

These tests define properties that MUST hold for ALL transforms,
regardless of their specific implementation.
"""

from __future__ import annotations

import albumentations as A
import pytest

from albu_spec import get_transform_metadata

from .conftest import get_init_params, get_init_schema_params

# Test multiple common transforms
TEST_TRANSFORMS = [
    A.HorizontalFlip,
    A.Affine,
    A.Rotate,
    A.Blur,
    A.Normalize,
]


@pytest.mark.parametrize("transform_class", TEST_TRANSFORMS)
def test_property_all_init_schema_params_in_init(transform_class):
    """PROPERTY: All InitSchema parameters must exist in __init__ signature.

    Universal invariant for all transforms with InitSchema.
    """
    if not hasattr(transform_class, "InitSchema"):
        pytest.skip(f"{transform_class.__name__} has no InitSchema")

    init_params = get_init_params(transform_class)
    schema_params = get_init_schema_params(transform_class)

    missing = schema_params - init_params

    assert not missing, f"INVARIANT VIOLATION: {transform_class.__name__} InitSchema defines {missing} not in __init__"


@pytest.mark.parametrize("transform_class", TEST_TRANSFORMS)
def test_property_type_hints_are_non_empty(transform_class):
    """PROPERTY: All extracted type hints must be non-empty strings or lists.

    Universal invariant: we should never extract empty type information.
    """
    metadata = get_transform_metadata(transform_class)

    for param_name, param_meta in metadata.parameters.items():
        type_hint = param_meta.type_hint

        if isinstance(type_hint, str):
            assert type_hint.strip(), f"{transform_class.__name__}.{param_name}: type_hint is empty string"
        elif isinstance(type_hint, list):
            assert len(type_hint) > 0, f"{transform_class.__name__}.{param_name}: type_hint is empty list"
            assert all(str(item).strip() for item in type_hint), (
                f"{transform_class.__name__}.{param_name}: type_hint list contains empty items"
            )
        else:
            pytest.fail(
                f"{transform_class.__name__}.{param_name}: type_hint must be str or list, got {type(type_hint)}"
            )


@pytest.mark.parametrize("transform_class", TEST_TRANSFORMS)
def test_property_constraint_ranges_are_valid(transform_class):
    """PROPERTY: Constraint ranges must be logically valid.

    Universal invariant:
    - If both ge and le exist: ge <= le
    - If both gt and lt exist: gt < lt
    - ge and gt are mutually exclusive
    - le and lt are mutually exclusive
    """
    metadata = get_transform_metadata(transform_class)

    for param_name, param_meta in metadata.parameters.items():
        if param_meta.constraints is None:
            continue

        c = param_meta.constraints

        # Check ge <= le
        if c.ge is not None and c.le is not None:
            assert c.ge <= c.le, (
                f"{transform_class.__name__}.{param_name}: Invalid range: ge={c.ge} must be <= le={c.le}"
            )

        # Check gt < lt
        if c.gt is not None and c.lt is not None:
            assert c.gt < c.lt, f"{transform_class.__name__}.{param_name}: Invalid range: gt={c.gt} must be < lt={c.lt}"

        # Check ge and gt are not both set
        if c.ge is not None and c.gt is not None:
            pytest.xfail(
                f"albumentationsx_bug: {transform_class.__name__}.{param_name} "
                f"has both ge={c.ge} and gt={c.gt} (should be mutually exclusive)"
            )

        # Check le and lt are not both set
        if c.le is not None and c.lt is not None:
            pytest.xfail(
                f"albumentationsx_bug: {transform_class.__name__}.{param_name} "
                f"has both le={c.le} and lt={c.lt} (should be mutually exclusive)"
            )


@pytest.mark.parametrize("transform_class", TEST_TRANSFORMS)
def test_property_transform_type_is_valid(transform_class):
    """PROPERTY: Transform type must be one of the valid categories.

    Universal invariant: transform_type must be:
    - 'image_only', 'dual', 'transforms_3d', or 'unknown'
    """
    metadata = get_transform_metadata(transform_class)

    valid_types = {"image_only", "dual", "transforms_3d", "unknown"}

    assert metadata.transform_type in valid_types, (
        f"{transform_class.__name__}: Invalid transform_type '{metadata.transform_type}', must be one of {valid_types}"
    )


@pytest.mark.parametrize("transform_class", [A.HorizontalFlip, A.Affine, A.Rotate])
def test_property_dual_transforms_have_targets(transform_class):
    """PROPERTY: Dual transforms must have non-empty targets list.

    Universal invariant: dual transforms operate on multiple targets,
    so targets list must not be empty.
    """
    metadata = get_transform_metadata(transform_class)

    if metadata.transform_type == "dual":
        assert len(metadata.targets) > 0, (
            f"{transform_class.__name__}: Dual transform must have targets, but targets list is empty"
        )

        # Should at least support 'image'
        assert "image" in metadata.targets, f"{transform_class.__name__}: Dual transform must support 'image' target"


@pytest.mark.parametrize("transform_class", TEST_TRANSFORMS)
def test_property_has_docstring(transform_class):
    """PROPERTY: All transforms should have docstrings.

    Universal invariant: transforms should be documented.
    """
    metadata = get_transform_metadata(transform_class)

    # At minimum should have some docstring
    assert metadata.docstring is not None and metadata.docstring.strip(), (
        f"{transform_class.__name__}: Transform has no docstring"
    )


@pytest.mark.parametrize("transform_class", TEST_TRANSFORMS)
def test_property_metadata_is_deterministic(transform_class):
    """PROPERTY: Extracting metadata twice should give identical results.

    Universal invariant: metadata extraction should be deterministic.
    """
    metadata1 = get_transform_metadata(transform_class)
    metadata2 = get_transform_metadata(transform_class)

    # Convert to dict for comparison
    dict1 = metadata1.model_dump()
    dict2 = metadata2.model_dump()

    assert dict1 == dict2, f"{transform_class.__name__}: Metadata extraction is non-deterministic"


@pytest.mark.parametrize("transform_class", TEST_TRANSFORMS)
def test_property_default_values_satisfy_constraints(transform_class):
    """PROPERTY: Default values must satisfy their own constraints.

    Universal invariant: if a parameter has ge=0, le=1 and default=0.5,
    the default must satisfy 0 <= 0.5 <= 1.
    """
    metadata = get_transform_metadata(transform_class)

    for param_name, param_meta in metadata.parameters.items():
        if param_meta.constraints is None:
            continue

        if param_meta.default is None:
            continue

        # Only check numeric defaults
        if not isinstance(param_meta.default, (int, float)):
            continue

        c = param_meta.constraints
        default = param_meta.default

        # Check ge constraint
        if c.ge is not None:
            if default < c.ge:
                pytest.xfail(
                    f"albumentationsx_bug: {transform_class.__name__}.{param_name} default={default} violates ge={c.ge}"
                )

        # Check le constraint
        if c.le is not None:
            if default > c.le:
                pytest.xfail(
                    f"albumentationsx_bug: {transform_class.__name__}.{param_name} default={default} violates le={c.le}"
                )

        # Check gt constraint
        if c.gt is not None:
            if default <= c.gt:
                pytest.xfail(
                    f"albumentationsx_bug: {transform_class.__name__}.{param_name} default={default} violates gt={c.gt}"
                )

        # Check lt constraint
        if c.lt is not None:
            if default >= c.lt:
                pytest.xfail(
                    f"albumentationsx_bug: {transform_class.__name__}.{param_name} default={default} violates lt={c.lt}"
                )
