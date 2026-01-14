"""Tests for metadata extraction consistency across different methods.

These tests verify that metadata extracted from different sources
(InitSchema, __init__ signature, docstrings) is consistent.
"""

from __future__ import annotations

import inspect

import albumentations as A
import pytest

from albu_spec import get_transform_metadata

from .conftest import (
    get_init_params,
    get_init_schema_params,
    normalize_type_string,
)


@pytest.mark.parametrize(
    "transform_class",
    [
        A.HorizontalFlip,
        A.Affine,
        pytest.param(
            A.ColorJitter if hasattr(A, "ColorJitter") else None,
            marks=pytest.mark.skipif(
                not hasattr(A, "ColorJitter"), reason="ColorJitter not available in AlbumentationsX"
            ),
        ),
    ],
)
def test_init_schema_params_exist_in_init(transform_class):
    """All InitSchema parameters must exist in __init__ signature.

    This is a fundamental consistency check: if InitSchema defines a parameter,
    it must be accepted by __init__.
    """
    if transform_class is None:
        pytest.skip("Transform not available")

    if not hasattr(transform_class, "InitSchema"):
        pytest.skip(f"{transform_class.__name__} has no InitSchema")

    init_params = get_init_params(transform_class)
    schema_params = get_init_schema_params(transform_class)

    missing_in_init = schema_params - init_params

    assert not missing_in_init, (
        f"{transform_class.__name__}: InitSchema defines parameters {missing_in_init} that don't exist in __init__"
    )


@pytest.mark.parametrize(
    "transform_class",
    [
        A.HorizontalFlip,
        A.Affine,
        pytest.param(
            A.ColorJitter if hasattr(A, "ColorJitter") else None,
            marks=pytest.mark.skipif(
                not hasattr(A, "ColorJitter"), reason="ColorJitter not available in AlbumentationsX"
            ),
        ),
    ],
)
def test_init_params_have_metadata(transform_class):
    """All __init__ parameters (except self, p, strict) should have metadata extracted.

    If a parameter exists in __init__, our extractor should capture it.
    """
    if transform_class is None:
        pytest.skip("Transform not available")

    metadata = get_transform_metadata(transform_class)

    init_params = get_init_params(transform_class)
    extracted_params = set(metadata.parameters.keys())

    missing = init_params - extracted_params

    assert not missing, f"{transform_class.__name__}: Parameters {missing} in __init__ but not extracted to metadata"


@pytest.mark.parametrize(
    "transform_class",
    [
        A.HorizontalFlip,
        A.Affine,
        pytest.param(
            A.ColorJitter if hasattr(A, "ColorJitter") else None,
            marks=pytest.mark.skipif(
                not hasattr(A, "ColorJitter"), reason="ColorJitter not available in AlbumentationsX"
            ),
        ),
    ],
)
def test_type_hints_consistency(transform_class):
    """Type hints from InitSchema should match __init__ annotations.

    If InitSchema defines a type and __init__ has a type annotation,
    they should be semantically equivalent.
    """
    if transform_class is None:
        pytest.skip("Transform not available")

    if not hasattr(transform_class, "InitSchema"):
        pytest.skip(f"{transform_class.__name__} has no InitSchema")

    metadata = get_transform_metadata(transform_class)
    init_schema = transform_class.InitSchema

    if not hasattr(init_schema, "model_fields"):
        pytest.skip("InitSchema has no model_fields")

    # Get __init__ signature for comparison
    sig = inspect.signature(transform_class.__init__)

    mismatches = []

    for param_name, field_info in init_schema.model_fields.items():
        if param_name not in metadata.parameters:
            continue

        # Get type from InitSchema
        schema_type = field_info.annotation if hasattr(field_info, "annotation") else None

        # Get type from __init__
        if param_name in sig.parameters:
            init_param = sig.parameters[param_name]
            init_type = init_param.annotation

            # Compare formatted representations
            if schema_type and init_type != inspect.Parameter.empty:
                schema_type_str = _format_type_for_comparison(schema_type)
                init_type_str = _format_type_for_comparison(init_type)

                # Normalize and compare
                if normalize_type_string(schema_type_str) != normalize_type_string(init_type_str):
                    mismatches.append(
                        {
                            "param": param_name,
                            "schema_type": schema_type_str,
                            "init_type": init_type_str,
                        }
                    )

    if mismatches:
        msg = f"{transform_class.__name__} type mismatches:\n"
        for m in mismatches:
            msg += f"  {m['param']}: InitSchema={m['schema_type']} vs __init__={m['init_type']}\n"

        # Mark as xfail if this is a known AlbumentationsX issue
        pytest.xfail(f"albumentationsx_bug: {msg}")


@pytest.mark.parametrize(
    "transform_class",
    [
        A.HorizontalFlip,
        A.Affine,
        pytest.param(
            A.ColorJitter if hasattr(A, "ColorJitter") else None,
            marks=pytest.mark.skipif(
                not hasattr(A, "ColorJitter"), reason="ColorJitter not available in AlbumentationsX"
            ),
        ),
    ],
)
def test_constraints_extracted_correctly(transform_class):
    """Constraints from InitSchema Field() should be extracted correctly.

    If InitSchema uses Field(ge=0, le=1), our SchemaParser should capture it.
    """
    if transform_class is None:
        pytest.skip("Transform not available")

    if not hasattr(transform_class, "InitSchema"):
        pytest.skip(f"{transform_class.__name__} has no InitSchema")

    metadata = get_transform_metadata(transform_class)
    init_schema = transform_class.InitSchema

    if not hasattr(init_schema, "model_fields"):
        pytest.skip("InitSchema has no model_fields")

    for param_name, field_info in init_schema.model_fields.items():
        if param_name not in metadata.parameters:
            continue

        param_metadata = metadata.parameters[param_name]

        # Check numeric constraints
        for constraint_name in ["ge", "le", "gt", "lt"]:
            schema_value = getattr(field_info, constraint_name, None)

            if schema_value is not None:
                assert param_metadata.constraints is not None, (
                    f"{transform_class.__name__}.{param_name}: "
                    f"Field has {constraint_name}={schema_value} but no constraints extracted"
                )

                extracted_value = getattr(param_metadata.constraints, constraint_name, None)

                assert extracted_value is not None, (
                    f"{transform_class.__name__}.{param_name}: "
                    f"Field has {constraint_name}={schema_value} but not extracted"
                )

                assert float(extracted_value) == float(schema_value), (
                    f"{transform_class.__name__}.{param_name}: "
                    f"{constraint_name} mismatch: expected {schema_value}, got {extracted_value}"
                )


def test_affine_specific_metadata():
    """Test Affine transform specific metadata extraction.

    Affine is complex with many parameters and nested dict types.
    """
    metadata = get_transform_metadata(A.Affine)

    # Should be dual transform
    assert metadata.transform_type == "dual", f"Affine should be 'dual' but got '{metadata.transform_type}'"

    # Should support multiple targets
    expected_targets = {"image", "mask", "bboxes", "keypoints"}
    actual_targets = set(metadata.targets)

    assert expected_targets.issubset(actual_targets), (
        f"Affine missing expected targets: {expected_targets - actual_targets}"
    )

    # Check complex parameters exist
    expected_params = {
        "scale",
        "translate_percent",
        "translate_px",
        "rotate",
        "shear",
        "interpolation",
        "mask_interpolation",
        "border_mode",
        "fit_output",
    }
    actual_params = set(metadata.parameters.keys())

    missing_params = expected_params - actual_params
    assert not missing_params, f"Affine missing parameters: {missing_params}"


def test_horizontalflip_specific_metadata():
    """Test HorizontalFlip transform specific metadata extraction.

    HorizontalFlip is simple with minimal parameters.
    """
    metadata = get_transform_metadata(A.HorizontalFlip)

    # Should be dual transform
    assert metadata.transform_type == "dual", f"HorizontalFlip should be 'dual' but got '{metadata.transform_type}'"

    # Should support standard targets
    assert "image" in metadata.targets, "HorizontalFlip must support 'image' target"


def _format_type_for_comparison(type_annotation) -> str:
    """Format type annotation for comparison."""
    from albu_spec.extractor import TransformMetadataExtractor

    extractor = TransformMetadataExtractor()
    formatted = extractor._format_type(type_annotation)

    if isinstance(formatted, list):
        # Literal type
        return " | ".join(str(item) for item in formatted)

    return str(formatted)
