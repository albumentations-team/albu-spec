"""Tests for full parsed docstring extraction."""

import albumentations as A
import pytest

from albu_spec import get_transform_metadata
from albu_spec.models import ParsedDocstring


def test_parsed_docstring_present():
    """Test that parsed docstring is extracted."""
    metadata = get_transform_metadata(A.HorizontalFlip)

    assert metadata.docstring_parsed is not None
    assert isinstance(metadata.docstring_parsed, ParsedDocstring)


def test_parsed_docstring_short_description():
    """Test short description extraction."""
    metadata = get_transform_metadata(A.HorizontalFlip)

    assert metadata.docstring_parsed is not None
    assert metadata.docstring_parsed.short_description is not None
    assert len(metadata.docstring_parsed.short_description) > 0


def test_parsed_docstring_args():
    """Test args section extraction."""
    metadata = get_transform_metadata(A.Blur)

    assert metadata.docstring_parsed is not None
    assert len(metadata.docstring_parsed.args) > 0

    # Check that args have names and descriptions
    for arg in metadata.docstring_parsed.args:
        assert arg.name
        # Some args might not have descriptions in docstring


def test_parsed_docstring_examples():
    """Test examples section extraction if present."""
    # Many transforms have examples, let's try a few
    transforms_to_check = [A.Blur, A.RandomBrightnessContrast, A.Affine]

    for transform_class in transforms_to_check:
        metadata = get_transform_metadata(transform_class)
        if metadata.docstring_parsed and metadata.docstring_parsed.examples:
            # If examples exist, they should be non-empty strings
            for example in metadata.docstring_parsed.examples:
                assert isinstance(example, str)
                assert len(example) > 0


def test_parsed_docstring_json_serialization():
    """Test that parsed docstring can be serialized to JSON."""
    metadata = get_transform_metadata(A.Blur)

    # This should not raise
    json_str = metadata.model_dump_json()
    assert json_str
    assert "docstring_parsed" in json_str


def test_parsed_docstring_contains_all_sections():
    """Test that parsed docstring model has all expected sections."""
    metadata = get_transform_metadata(A.Blur)

    assert metadata.docstring_parsed is not None
    parsed = metadata.docstring_parsed

    # Check all fields exist (even if None/empty)
    assert hasattr(parsed, "short_description")
    assert hasattr(parsed, "long_description")
    assert hasattr(parsed, "args")
    assert hasattr(parsed, "returns")
    assert hasattr(parsed, "raises")
    assert hasattr(parsed, "yields")
    assert hasattr(parsed, "examples")
    assert hasattr(parsed, "notes")
    assert hasattr(parsed, "warnings")
    assert hasattr(parsed, "see_also")
    assert hasattr(parsed, "references")
    assert hasattr(parsed, "attributes")
    assert hasattr(parsed, "extra_sections")


def test_parsed_docstring_extra_sections():
    """Test that extra sections (Image types, Targets, etc.) are captured."""
    metadata = get_transform_metadata(A.Blur)

    assert metadata.docstring_parsed is not None
    assert isinstance(metadata.docstring_parsed.extra_sections, dict)

    # Blur should have "Image types" and "Targets" sections
    assert "Image types" in metadata.docstring_parsed.extra_sections
    assert "Targets" in metadata.docstring_parsed.extra_sections


def test_parsed_docstring_extra_sections_various_transforms():
    """Test that different transforms capture their unique sections."""
    # RandomBrightnessContrast has Mathematical Formulation
    metadata = get_transform_metadata(A.RandomBrightnessContrast)
    assert metadata.docstring_parsed is not None
    if metadata.docstring_parsed.extra_sections:
        # Should have custom math sections
        assert (
            any(
                "mathematical" in key.lower() or "formulation" in key.lower()
                for key in metadata.docstring_parsed.extra_sections.keys()
            )
            or "Number of channels" in metadata.docstring_parsed.extra_sections
        )


@pytest.mark.parametrize(
    "transform_class",
    [
        A.HorizontalFlip,
        A.Blur,
        A.RandomBrightnessContrast,
        A.Affine,
        A.Rotate,
    ],
)
def test_parsed_docstring_multiple_transforms(transform_class):
    """Test parsed docstring extraction for multiple transforms."""
    metadata = get_transform_metadata(transform_class)

    # All transforms should have parsed docstrings (or None if no docstring)
    if metadata.docstring:
        assert metadata.docstring_parsed is not None
        assert isinstance(metadata.docstring_parsed, ParsedDocstring)


def test_parsed_docstring_arg_structure():
    """Test that parsed args have correct structure."""
    metadata = get_transform_metadata(A.Blur)

    assert metadata.docstring_parsed is not None
    if metadata.docstring_parsed.args:
        for arg in metadata.docstring_parsed.args:
            # Each arg must have a name
            assert arg.name
            # Type and description are optional
            assert hasattr(arg, "type")
            assert hasattr(arg, "description")


def test_no_docstring_returns_none():
    """Test that transforms without docstrings return None for parsed."""

    # Create a dummy class without docstring
    class DummyTransform(A.BasicTransform):
        pass

    metadata = get_transform_metadata(DummyTransform)
    assert metadata.docstring_parsed is None
