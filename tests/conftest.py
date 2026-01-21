"""Shared pytest fixtures for albu-spec tests."""

from __future__ import annotations

import inspect
from pathlib import Path
from typing import Any

import albumentations as A
import pytest

from albu_spec.docstring_parser import DocstringParser
from albu_spec.extractor import TransformMetadataExtractor
from albu_spec.schema_parser import SchemaParser


@pytest.fixture
def extractor() -> TransformMetadataExtractor:
    """Create a TransformMetadataExtractor instance."""
    return TransformMetadataExtractor()


@pytest.fixture
def schema_parser() -> SchemaParser:
    """Create a SchemaParser instance."""
    return SchemaParser()


@pytest.fixture
def docstring_parser() -> DocstringParser:
    """Create a DocstringParser instance."""
    return DocstringParser()


@pytest.fixture
def transform_classes() -> list[type]:
    """Return list of transform classes to test.

    Focus on three representative transforms:
    - HorizontalFlip: Simple dual transform with minimal parameters
    - Affine: Complex dual transform with many parameters and nested types
    - ColorJitter: Image-only transform with range constraints
    """
    classes = []

    # HorizontalFlip - simple transform
    if hasattr(A, "HorizontalFlip"):
        classes.append(A.HorizontalFlip)

    # Affine - complex transform
    if hasattr(A, "Affine"):
        classes.append(A.Affine)

    # ColorJitter - color transform with constraints
    if hasattr(A, "ColorJitter"):
        classes.append(A.ColorJitter)

    return classes


@pytest.fixture
def all_transform_classes() -> list[type]:
    """Return all available AlbumentationsX transform classes.

    Used for property-based tests that should apply to ALL transforms.
    """
    transforms = []

    # Get all classes from A that are transforms
    for name, obj in inspect.getmembers(A, predicate=inspect.isclass):
        # Skip base classes and ignored transforms
        if name in {"BasicTransform", "DualTransform", "ImageOnlyTransform", "Transform3D", "Lambda"}:
            continue

        # Check if it's a transform
        try:
            if hasattr(A, "BasicTransform") and issubclass(obj, A.BasicTransform):
                if obj is not A.BasicTransform:
                    transforms.append(obj)
        except TypeError:
            continue

    return transforms


@pytest.fixture
def snapshot_dir(tmp_path: Path) -> Path:
    """Create temporary directory for test snapshots."""
    snapshots = tmp_path / "snapshots"
    snapshots.mkdir(exist_ok=True)
    return snapshots


@pytest.fixture
def xfail_tracker() -> dict[str, list[dict[str, Any]]]:
    """Track xfail tests for report generation.

    Returns:
        Dictionary to store xfail information

    """
    return {
        "albumentationsx_bugs": [],
        "parser_bugs": [],
    }
