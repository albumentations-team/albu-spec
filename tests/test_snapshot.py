"""Snapshot tests for transform metadata extraction.

These tests verify that metadata extraction produces expected JSON output.
They serve as:
1. Regression tests - detect unintended changes to extraction logic
2. Documentation - show exact output format for each transform
3. Integration tests - verify the complete extraction pipeline works

Each test compares extracted metadata against known-good snapshots for:
- HorizontalFlip (simple dual transform with only 'p' parameter)
- ColorJitter (image-only transform with multiple numeric parameters)
- Affine (complex dual transform with mixed types including Literal[int] and Literal[str])
- AdditiveNoise (image-only transform with Literal types and dict parameters)
"""

import albumentations as A
import pytest

from albu_spec import get_transform_metadata


@pytest.fixture
def expected_horizontalflip_metadata() -> dict:
    """Expected metadata for HorizontalFlip transform."""
    return {
        "name": "HorizontalFlip",
        "module": "albumentations.augmentations.geometric.flip",
        "transform_type": "dual",
        "targets": ["image", "mask", "bboxes", "keypoints", "volume", "mask3d"],
        "parameters": {
            "p": {
                "name": "p",
                "type_hint": "float",
                "default": 0.5,
                "description": "probability of applying the transform. Default: 0.5.",
                "constraints": {
                    "ge": 0.0,
                    "le": 1.0,
                    "gt": None,
                    "lt": None,
                    "min_length": None,
                    "max_length": None,
                    "multiple_of": None,
                    "min_value": None,
                    "max_value": None,
                    "pattern": None,
                    "validators": [],
                    "validator_info": {},
                },
            },
        },
        "docstring_short": "Flip the input horizontally around the y-axis.",
        "has_init_schema": True,
    }


@pytest.fixture
def expected_colorjitter_metadata() -> dict:
    """Expected metadata for ColorJitter transform."""
    return {
        "name": "ColorJitter",
        "module": "albumentations.augmentations.pixel.transforms",
        "transform_type": "image_only",
        "targets": ["image", "volume"],
        "parameters": {
            "brightness": {
                "name": "brightness",
                "type_hint": "tuple[float, float] | float",
                "default": (0.8, 1.2),
                "description_prefix": "How much to jitter brightness.",
                "constraints": None,
            },
            "contrast": {
                "name": "contrast",
                "type_hint": "tuple[float, float] | float",
                "default": (0.8, 1.2),
                "description_prefix": "How much to jitter contrast.",
                "constraints": None,
            },
            "saturation": {
                "name": "saturation",
                "type_hint": "tuple[float, float] | float",
                "default": (0.8, 1.2),
                "description_prefix": "How much to jitter saturation.",
                "constraints": None,
            },
            "hue": {
                "name": "hue",
                "type_hint": "tuple[float, float] | float",
                "default": (-0.5, 0.5),
                "description_prefix": "How much to jitter hue.",
                "constraints": None,
            },
            "p": {
                "name": "p",
                "type_hint": "float",
                "default": 0.5,
                "description": None,
                "constraints": {
                    "ge": 0.0,
                    "le": 1.0,
                    "gt": None,
                    "lt": None,
                    "min_length": None,
                    "max_length": None,
                    "multiple_of": None,
                    "min_value": None,
                    "max_value": None,
                    "pattern": None,
                    "validators": [],
                    "validator_info": {},
                },
            },
        },
        "docstring_short": "Randomly changes the brightness, contrast, saturation, and hue of an image.",
        "has_init_schema": True,
    }


@pytest.fixture
def expected_additivenoise_metadata() -> dict:
    """Expected metadata for AdditiveNoise transform."""
    return {
        "name": "AdditiveNoise",
        "module": "albumentations.augmentations.pixel.transforms",
        "transform_type": "image_only",
        "targets": ["image", "volume"],
        "parameters": {
            "noise_type": {
                "name": "noise_type",
                "type_hint": ["uniform", "gaussian", "laplace", "beta"],
                "default": "uniform",
                "description_prefix": "Type of noise distribution to use.",
                "constraints": None,
            },
            "spatial_mode": {
                "name": "spatial_mode",
                "type_hint": ["constant", "per_pixel", "shared"],
                "default": "constant",
                "description_prefix": "How to generate and apply the noise.",
                "constraints": None,
            },
            "noise_params": {
                "name": "noise_params",
                "type_hint": "dict[str, Any] | None",
                "default": None,
                "description_prefix": "Parameters for the chosen noise distribution.",
                "constraints": None,
            },
            "approximation": {
                "name": "approximation",
                "type_hint": "float",
                "default": 1.0,
                "description_prefix": "float in [0, 1], default=1.0",
                "constraints": {
                    "ge": 0.0,
                    "le": 1.0,
                    "gt": None,
                    "lt": None,
                    "min_length": None,
                    "max_length": None,
                    "multiple_of": None,
                    "min_value": None,
                    "max_value": None,
                    "pattern": None,
                    "validators": [],
                    "validator_info": {},
                },
            },
            "p": {
                "name": "p",
                "type_hint": "float",
                "default": 0.5,
                "description": None,
                "constraints": {
                    "ge": 0.0,
                    "le": 1.0,
                    "gt": None,
                    "lt": None,
                    "min_length": None,
                    "max_length": None,
                    "multiple_of": None,
                    "min_value": None,
                    "max_value": None,
                    "pattern": None,
                    "validators": [],
                    "validator_info": {},
                },
            },
        },
        "docstring_short": "Apply random noise to image channels using various noise distributions.",
        "has_init_schema": True,
    }


@pytest.fixture
def expected_affine_metadata() -> dict:
    """Expected metadata for Affine transform."""
    return {
        "name": "Affine",
        "module": "albumentations.augmentations.geometric.transforms",
        "transform_type": "dual",
        "targets": ["image", "mask", "bboxes", "keypoints", "volume", "mask3d"],
        "parameters": {
            "scale": {
                "name": "scale",
                "type_hint": "tuple[float, float] | float | dict[str, float | tuple[float, float]]",
                "default": (1.0, 1.0),
                "description_prefix": 'Scaling factor to use, where `1.0` denotes "no change"',
                "constraints": None,
            },
            "translate_percent": {
                "name": "translate_percent",
                "type_hint": "tuple[float, float] | float | dict[str, float | tuple[float, float]] | None",
                "default": None,
                "description_prefix": "Translation as a fraction of the image height/width",
                "constraints": None,
            },
            "translate_px": {
                "name": "translate_px",
                "type_hint": "tuple[float, float] | float | dict[str, float | tuple[float, float]] | None",
                "default": None,
                "description_prefix": "Translation in pixels.",
                "constraints": None,
            },
            "rotate": {
                "name": "rotate",
                "type_hint": "tuple[float, float] | float",
                "default": 0.0,
                "description_prefix": "Rotation in degrees (**NOT** radians)",
                "constraints": None,
            },
            "shear": {
                "name": "shear",
                "type_hint": "tuple[float, float] | float | dict[str, float | tuple[float, float]]",
                "default": (0.0, 0.0),
                "description_prefix": "Shear in degrees (**NOT** radians)",
                "constraints": None,
            },
            "interpolation": {
                "name": "interpolation",
                "type_hint": [0, 1, 2, 3, 4],
                "default": 1,
                "description": "OpenCV interpolation flag.",
                "constraints": None,
            },
            "mask_interpolation": {
                "name": "mask_interpolation",
                "type_hint": [0, 1, 2, 3, 4],
                "default": 0,
                "description": "OpenCV interpolation flag.",
                "constraints": None,
            },
            "fit_output": {
                "name": "fit_output",
                "type_hint": "bool",
                "default": False,
                "description_prefix": "If True, the image plane size and position will be adjusted",
                "constraints": None,
            },
            "keep_ratio": {
                "name": "keep_ratio",
                "type_hint": "bool",
                "default": True,
                "description_prefix": "When True, the original aspect ratio will be kept",
                "constraints": None,
            },
            "rotate_method": {
                "name": "rotate_method",
                "type_hint": ["largest_box", "ellipse"],
                "default": "largest_box",
                "description_prefix": "rotation method used for the bounding boxes.",
                "constraints": None,
            },
            "balanced_scale": {
                "name": "balanced_scale",
                "type_hint": "bool",
                "default": False,
                "description_prefix": "When True, scaling factors are chosen to be either entirely below or above 1",
                "constraints": None,
            },
            "border_mode": {
                "name": "border_mode",
                "type_hint": [0, 1, 2, 3, 4],
                "default": 0,
                "description": "OpenCV border flag.",
                "constraints": None,
            },
            "fill": {
                "name": "fill",
                "type_hint": "tuple[float, ...] | float",
                "default": 0,
                "description_prefix": "The constant value to use when filling in newly created pixels.",
                "constraints": None,
            },
            "fill_mask": {
                "name": "fill_mask",
                "type_hint": "tuple[float, ...] | float",
                "default": 0,
                "description": "Same as fill but only for masks.",
                "constraints": None,
            },
            "p": {
                "name": "p",
                "type_hint": "float",
                "default": 0.5,
                "description": "probability of applying the transform. Default: 0.5.",
                "constraints": {
                    "ge": 0.0,
                    "le": 1.0,
                    "gt": None,
                    "lt": None,
                    "min_length": None,
                    "max_length": None,
                    "multiple_of": None,
                    "min_value": None,
                    "max_value": None,
                    "pattern": None,
                    "validators": [],
                    "validator_info": {},
                },
            },
        },
        "docstring_short": "Augmentation to apply affine transformations to images.",
        "has_init_schema": True,
    }


def test_horizontalflip_metadata_snapshot(expected_horizontalflip_metadata: dict) -> None:
    """Test that HorizontalFlip metadata extraction produces expected JSON."""
    metadata = get_transform_metadata(A.HorizontalFlip)
    actual = metadata.model_dump()

    # Compare everything except the full docstring (too long)
    assert actual["name"] == expected_horizontalflip_metadata["name"]
    assert actual["module"] == expected_horizontalflip_metadata["module"]
    assert actual["transform_type"] == expected_horizontalflip_metadata["transform_type"]
    assert actual["targets"] == expected_horizontalflip_metadata["targets"]
    assert actual["parameters"] == expected_horizontalflip_metadata["parameters"]
    assert actual["docstring_short"] == expected_horizontalflip_metadata["docstring_short"]
    assert actual["has_init_schema"] == expected_horizontalflip_metadata["has_init_schema"]
    assert actual["docstring"] is not None  # Just verify it exists


def test_colorjitter_metadata_snapshot(expected_colorjitter_metadata: dict) -> None:
    """Test that ColorJitter metadata extraction produces expected JSON."""
    metadata = get_transform_metadata(A.ColorJitter)
    actual = metadata.model_dump()

    # Compare everything except the full docstring
    assert actual["name"] == expected_colorjitter_metadata["name"]
    assert actual["module"] == expected_colorjitter_metadata["module"]
    assert actual["transform_type"] == expected_colorjitter_metadata["transform_type"]
    assert actual["targets"] == expected_colorjitter_metadata["targets"]

    # Compare parameters, checking description prefixes only
    for param_name, expected_param in expected_colorjitter_metadata["parameters"].items():
        actual_param = actual["parameters"][param_name]
        assert actual_param["name"] == expected_param["name"]
        assert actual_param["type_hint"] == expected_param["type_hint"]
        assert actual_param["default"] == expected_param["default"]
        assert actual_param["constraints"] == expected_param["constraints"]

        # Check description prefix if provided
        if "description_prefix" in expected_param:
            actual_desc = actual_param.get("description") or ""
            assert actual_desc.startswith(expected_param["description_prefix"]), (
                f"Description for {param_name} should start with {expected_param['description_prefix']!r}"
            )
        elif expected_param["description"] is not None:
            assert actual_param["description"] == expected_param["description"]

    assert actual["docstring_short"] == expected_colorjitter_metadata["docstring_short"]
    assert actual["has_init_schema"] == expected_colorjitter_metadata["has_init_schema"]
    assert actual["docstring"] is not None


def test_affine_metadata_snapshot(expected_affine_metadata: dict) -> None:
    """Test that Affine metadata extraction produces expected JSON."""
    metadata = get_transform_metadata(A.Affine)
    actual = metadata.model_dump()

    # Compare everything except the full docstring
    assert actual["name"] == expected_affine_metadata["name"]
    assert actual["module"] == expected_affine_metadata["module"]
    assert actual["transform_type"] == expected_affine_metadata["transform_type"]
    assert actual["targets"] == expected_affine_metadata["targets"]

    # Compare parameters, checking description prefixes only
    for param_name, expected_param in expected_affine_metadata["parameters"].items():
        actual_param = actual["parameters"][param_name]
        assert actual_param["name"] == expected_param["name"]
        assert actual_param["type_hint"] == expected_param["type_hint"]
        assert actual_param["default"] == expected_param["default"]
        assert actual_param["constraints"] == expected_param["constraints"]

        # Check description prefix if provided
        if "description_prefix" in expected_param:
            actual_desc = actual_param.get("description") or ""
            assert actual_desc.startswith(expected_param["description_prefix"]), (
                f"Description for {param_name} should start with {expected_param['description_prefix']!r}"
            )
        elif expected_param["description"] is not None:
            assert actual_param["description"] == expected_param["description"]

    assert actual["docstring_short"] == expected_affine_metadata["docstring_short"]
    assert actual["has_init_schema"] == expected_affine_metadata["has_init_schema"]
    assert actual["docstring"] is not None


def test_affine_interpolation_type_is_int_list() -> None:
    """Test that Affine interpolation parameter uses integer Literal values, not strings."""
    metadata = get_transform_metadata(A.Affine)
    interpolation_type = metadata.parameters["interpolation"].type_hint

    assert isinstance(interpolation_type, list), "interpolation type_hint should be a list"
    assert interpolation_type == [0, 1, 2, 3, 4], "interpolation should be list of ints, not strings"
    assert all(isinstance(x, int) for x in interpolation_type), "All values should be integers"


def test_affine_rotate_method_type_is_str_list() -> None:
    """Test that Affine rotate_method parameter uses string Literal values."""
    metadata = get_transform_metadata(A.Affine)
    rotate_method_type = metadata.parameters["rotate_method"].type_hint

    assert isinstance(rotate_method_type, list), "rotate_method type_hint should be a list"
    assert rotate_method_type == ["largest_box", "ellipse"], "rotate_method should be list of strings"
    assert all(isinstance(x, str) for x in rotate_method_type), "All values should be strings"


def test_additivenoise_metadata_snapshot(expected_additivenoise_metadata: dict) -> None:
    """Test that AdditiveNoise metadata extraction produces expected JSON."""
    metadata = get_transform_metadata(A.AdditiveNoise)
    actual = metadata.model_dump()

    # Compare everything except the full docstring
    assert actual["name"] == expected_additivenoise_metadata["name"]
    assert actual["module"] == expected_additivenoise_metadata["module"]
    assert actual["transform_type"] == expected_additivenoise_metadata["transform_type"]
    assert actual["targets"] == expected_additivenoise_metadata["targets"]

    # Compare parameters, checking description prefixes only
    for param_name, expected_param in expected_additivenoise_metadata["parameters"].items():
        actual_param = actual["parameters"][param_name]
        assert actual_param["name"] == expected_param["name"]
        assert actual_param["type_hint"] == expected_param["type_hint"]
        assert actual_param["default"] == expected_param["default"]
        assert actual_param["constraints"] == expected_param["constraints"]

        # Check description prefix if provided
        if "description_prefix" in expected_param:
            actual_desc = actual_param.get("description") or ""
            assert actual_desc.startswith(expected_param["description_prefix"]), (
                f"Description for {param_name} should start with {expected_param['description_prefix']!r}"
            )
        elif expected_param["description"] is not None:
            assert actual_param["description"] == expected_param["description"]

    assert actual["docstring_short"] == expected_additivenoise_metadata["docstring_short"]
    assert actual["has_init_schema"] == expected_additivenoise_metadata["has_init_schema"]
    assert actual["docstring"] is not None


def test_additivenoise_noise_type_is_str_list() -> None:
    """Test that AdditiveNoise noise_type parameter uses string Literal values."""
    metadata = get_transform_metadata(A.AdditiveNoise)
    noise_type = metadata.parameters["noise_type"].type_hint

    assert isinstance(noise_type, list), "noise_type type_hint should be a list"
    assert noise_type == ["uniform", "gaussian", "laplace", "beta"], "noise_type should be list of strings"
    assert all(isinstance(x, str) for x in noise_type), "All values should be strings"


def test_additivenoise_spatial_mode_is_str_list() -> None:
    """Test that AdditiveNoise spatial_mode parameter uses string Literal values."""
    metadata = get_transform_metadata(A.AdditiveNoise)
    spatial_mode = metadata.parameters["spatial_mode"].type_hint

    assert isinstance(spatial_mode, list), "spatial_mode type_hint should be a list"
    assert spatial_mode == ["constant", "per_pixel", "shared"], "spatial_mode should be list of strings"
    assert all(isinstance(x, str) for x in spatial_mode), "All values should be strings"
