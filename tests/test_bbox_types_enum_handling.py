"""Test that _get_supported_bbox_types handles enums correctly.

This test verifies the fix for the bug where _get_supported_bbox_types
didn't extract enum values or convert to lowercase, unlike _get_targets.
"""

from enum import Enum
from typing import ClassVar

import albumentations as A

from albu_spec.extractor import TransformMetadataExtractor


class TestBBoxTypeEnumHandling:
    """Test enum value extraction and lowercase conversion."""

    def test_enum_values_extracted_and_lowercased(self):
        """Verify enum values are extracted and converted to lowercase."""

        # Create enum with uppercase values
        class BBoxType(Enum):
            HBB = "HBB"
            OBB = "OBB"

        # Mock transform with enum-based _supported_bbox_types
        class MockTransform(A.DualTransform):
            _targets: ClassVar = ("image", "bboxes")
            _supported_bbox_types = frozenset([BBoxType.HBB, BBoxType.OBB])

        extractor = TransformMetadataExtractor()
        result = extractor._get_supported_bbox_types(MockTransform)

        # Should extract .value and convert to lowercase
        assert result == ["hbb", "obb"]
        assert all(isinstance(x, str) for x in result)
        assert all(x == x.lower() for x in result)

    def test_mixed_enum_and_string_values(self):
        """Verify mixed enum and string values are handled correctly."""

        class BBoxType(Enum):
            HBB = "HBB"

        class MockTransform(A.DualTransform):
            _targets: ClassVar = ("image", "bboxes")
            _supported_bbox_types = frozenset([BBoxType.HBB, "OBB"])

        extractor = TransformMetadataExtractor()
        result = extractor._get_supported_bbox_types(MockTransform)

        assert result == ["hbb", "obb"]
        assert all(isinstance(x, str) for x in result)

    def test_uppercase_strings_converted_to_lowercase(self):
        """Verify uppercase strings are converted to lowercase."""

        class MockTransform(A.DualTransform):
            _targets: ClassVar = ("image", "bboxes")
            _supported_bbox_types = frozenset(["HBB", "OBB"])

        extractor = TransformMetadataExtractor()
        result = extractor._get_supported_bbox_types(MockTransform)

        assert result == ["hbb", "obb"]
        assert all(x == x.lower() for x in result)

    def test_consistency_with_get_targets_pattern(self):
        """Verify _get_supported_bbox_types follows same pattern as _get_targets."""

        class TargetEnum(Enum):
            IMAGE = "IMAGE"
            MASK = "MASK"
            BBOXES = "BBOXES"

        class BBoxTypeEnum(Enum):
            HBB = "HBB"
            OBB = "OBB"

        class MockTransform(A.DualTransform):
            _targets: ClassVar = [TargetEnum.IMAGE, TargetEnum.MASK, TargetEnum.BBOXES]
            _supported_bbox_types: ClassVar = frozenset([BBoxTypeEnum.HBB, BBoxTypeEnum.OBB])

        extractor = TransformMetadataExtractor()

        targets = extractor._get_targets(MockTransform)
        bbox_types = extractor._get_supported_bbox_types(MockTransform)

        # Both should extract enum values and convert to lowercase
        assert targets == ["image", "mask", "bboxes"]
        assert bbox_types == ["hbb", "obb"]

        # Both should be lists of strings
        assert all(isinstance(x, str) for x in targets)
        assert all(isinstance(x, str) for x in bbox_types)

        # Both should be lowercase
        assert all(x == x.lower() for x in targets)
        assert all(x == x.lower() for x in bbox_types)

    def test_non_string_enum_values_filtered_out(self):
        """Verify non-string enum values are filtered out."""

        class BBoxType(Enum):
            HBB = "HBB"
            INVALID = 123  # Non-string value

        class MockTransform(A.DualTransform):
            _targets: ClassVar = ("image", "bboxes")
            _supported_bbox_types = frozenset([BBoxType.HBB, BBoxType.INVALID])

        extractor = TransformMetadataExtractor()
        result = extractor._get_supported_bbox_types(MockTransform)

        # Only string values should be included
        assert result == ["hbb"]

    def test_real_transforms_return_lowercase_strings(self):
        """Verify real AlbumentationsX transforms return lowercase strings."""
        extractor = TransformMetadataExtractor()

        # Test a few real transforms
        for transform_class in [A.Affine, A.Rotate, A.HorizontalFlip]:
            result = extractor._get_supported_bbox_types(transform_class)

            if result is not None:
                # Should be list of lowercase strings
                assert isinstance(result, list)
                assert all(isinstance(x, str) for x in result)
                assert all(x == x.lower() for x in result)
                # Should be sorted
                assert result == sorted(result)
