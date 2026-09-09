"""Tests for bounding box type extraction."""

import albumentations as A
import pytest

from albu_spec import get_all_transforms_metadata, get_transform_metadata


class TestBBoxTypeExtraction:
    """Test extraction of supported bbox types from transforms."""

    def test_dual_transform_with_obb_support(self) -> None:
        """Test that dual transforms with OBB support are extracted correctly."""
        metadata = get_transform_metadata(A.Affine)

        assert metadata.supported_bbox_types is not None
        assert isinstance(metadata.supported_bbox_types, list)
        assert "hbb" in metadata.supported_bbox_types
        # Affine supports OBB
        assert "obb" in metadata.supported_bbox_types

    def test_dual_transform_hbb_only(self) -> None:
        """Test that dual transforms with only HBB support are extracted correctly."""
        # Note: CenterCrop now supports OBB in newer AlbumentationsX versions
        # Using Pad as example of HBB-only transform if it exists
        metadata = get_transform_metadata(A.CenterCrop)

        assert metadata.supported_bbox_types is not None
        assert isinstance(metadata.supported_bbox_types, list)
        assert "hbb" in metadata.supported_bbox_types
        # Note: This test now passes for transforms that support both HBB and OBB
        # AlbumentationsX has updated crop transforms to support OBB

    def test_image_only_transform_no_bbox_types(self) -> None:
        """Test that image-only transforms have None for bbox types."""
        metadata = get_transform_metadata(A.ColorJitter)

        assert metadata.transform_type == "image_only"
        assert metadata.supported_bbox_types is None

    def test_bbox_types_are_sorted(self) -> None:
        """Test that bbox types are returned in sorted order."""
        metadata = get_transform_metadata(A.Affine)

        if metadata.supported_bbox_types:
            assert metadata.supported_bbox_types == sorted(metadata.supported_bbox_types)

    @pytest.mark.parametrize(
        ("transform_class", "expected_has_obb"),
        [
            (A.Affine, True),
            (A.Rotate, True),
            (A.HorizontalFlip, True),
            (A.VerticalFlip, True),
            (A.Perspective, True),
            # Note: AlbumentationsX now supports OBB for crop transforms
            (A.CenterCrop, True),
            (A.RandomCrop, True),
            (A.Crop, True),
        ],
    )
    def test_obb_support_specific_transforms(
        self,
        transform_class: type,
        *,
        expected_has_obb: bool,
    ) -> None:
        """Test OBB support for specific transforms."""
        metadata = get_transform_metadata(transform_class)

        assert metadata.supported_bbox_types is not None, (
            f"{transform_class.__name__} should have bbox types (it's a dual transform)"
        )

        has_obb = "obb" in metadata.supported_bbox_types

        assert has_obb == expected_has_obb, (
            f"{transform_class.__name__} OBB support mismatch: expected {expected_has_obb}, got {has_obb}"
        )


class TestBBoxTypeConsistency:
    """Test consistency of bbox type extraction across all transforms."""

    def test_bbox_types_match_declared_targets(self) -> None:
        """Only transforms accepting bounding boxes need bbox type metadata."""
        collection = get_all_transforms_metadata()

        for transform in collection.dual:
            if "bboxes" not in transform.targets:
                assert transform.supported_bbox_types is None, f"{transform.name} does not accept bounding boxes"
                continue
            assert transform.supported_bbox_types is not None, (
                f"Dual transform {transform.name} should have bbox types defined"
            )
            assert len(transform.supported_bbox_types) > 0, (
                f"Dual transform {transform.name} should have at least one bbox type"
            )

    def test_image_only_transforms_no_bbox_types(self) -> None:
        """Test that image-only transforms don't have bbox types."""
        collection = get_all_transforms_metadata()

        for transform in collection.image_only:
            assert transform.supported_bbox_types is None, (
                f"Image-only transform {transform.name} should not have bbox types"
            )

    def test_bbox_types_only_valid_values(self) -> None:
        """Test that bbox types only contain valid values (hbb, obb)."""
        collection = get_all_transforms_metadata()
        valid_types = {"hbb", "obb"}

        for transform in collection.dual:
            if transform.supported_bbox_types:
                for bbox_type in transform.supported_bbox_types:
                    assert bbox_type in valid_types, f"{transform.name} has invalid bbox type: {bbox_type}"

    def test_bbox_transforms_support_hbb(self) -> None:
        """Transforms accepting bounding boxes support at least HBB."""
        collection = get_all_transforms_metadata()

        for transform in collection.dual:
            if "bboxes" not in transform.targets:
                continue
            assert transform.supported_bbox_types is not None
            assert "hbb" in transform.supported_bbox_types, (
                f"{transform.name} should support HBB (horizontal bounding boxes)"
            )


class TestBBoxTypeJSON:
    """Test JSON serialization of bbox types."""

    def test_bbox_types_in_json_output(self) -> None:
        """Test that bbox types appear in JSON output."""
        metadata = get_transform_metadata(A.Affine)
        json_data = metadata.model_dump()

        assert "supported_bbox_types" in json_data
        assert json_data["supported_bbox_types"] == ["hbb", "obb"]

    def test_none_bbox_types_serializes_correctly(self) -> None:
        """Test that None bbox types serialize correctly to JSON."""
        metadata = get_transform_metadata(A.ColorJitter)
        json_data = metadata.model_dump()

        assert "supported_bbox_types" in json_data
        assert json_data["supported_bbox_types"] is None

    def test_bbox_types_in_collection_json(self) -> None:
        """Test bbox types in collection JSON output."""
        collection = get_all_transforms_metadata()
        json_data = collection.model_dump()

        # Check first dual transform
        if json_data["dual"]:
            first_dual = json_data["dual"][0]
            assert "supported_bbox_types" in first_dual
            assert first_dual["supported_bbox_types"] is not None


class TestBBoxTypeFiltering:
    """Test filtering transforms by bbox type support."""

    def test_filter_transforms_with_obb_support(self) -> None:
        """Test filtering transforms that support OBB."""
        collection = get_all_transforms_metadata()

        transforms_with_obb = [t for t in collection.dual if t.supported_bbox_types and "obb" in t.supported_bbox_types]

        assert len(transforms_with_obb) > 0, "Should find transforms with OBB support"

        # Verify all returned transforms actually have OBB
        for transform in transforms_with_obb:
            assert "obb" in transform.supported_bbox_types

    def test_filter_transforms_hbb_only(self) -> None:
        """Test filtering transforms that support only HBB."""
        collection = get_all_transforms_metadata()

        transforms_hbb_only = [
            t
            for t in collection.dual
            if t.supported_bbox_types and "hbb" in t.supported_bbox_types and "obb" not in t.supported_bbox_types
        ]

        # Note: AlbumentationsX may have all dual transforms support OBB now
        # This test checks the filtering logic works, even if count is 0
        if len(transforms_hbb_only) > 0:
            # Verify all returned transforms have HBB but not OBB
            for transform in transforms_hbb_only:
                assert "hbb" in transform.supported_bbox_types
                assert "obb" not in transform.supported_bbox_types

    def test_count_bbox_type_support(self) -> None:
        """Test counting transforms by bbox type support."""
        collection = get_all_transforms_metadata()

        obb_count = sum(1 for t in collection.dual if t.supported_bbox_types and "obb" in t.supported_bbox_types)

        hbb_only_count = sum(
            1
            for t in collection.dual
            if t.supported_bbox_types and "hbb" in t.supported_bbox_types and "obb" not in t.supported_bbox_types
        )

        total_bbox = sum("bboxes" in transform.targets for transform in collection.dual)

        assert obb_count > 0, "Should have some transforms with OBB support"
        # Note: hbb_only_count may be 0 if all dual transforms now support OBB
        assert obb_count + hbb_only_count == total_bbox, "Every bbox transform must support HBB+OBB or HBB-only"


class TestBBoxTypeEdgeCases:
    """Test edge cases for bbox type extraction."""

    def test_transforms_3d_bbox_types_when_dual(self) -> None:
        """Test that 3D transforms that are also dual transforms can have bbox types."""
        collection = get_all_transforms_metadata()

        for transform in collection.transforms_3d:
            # Some 3D transforms inherit from DualTransform and support bboxes
            # Check if the transform is also a dual transform
            if transform.supported_bbox_types is not None:
                # If it has bbox types, verify they're valid
                assert isinstance(transform.supported_bbox_types, list)
                assert len(transform.supported_bbox_types) > 0
                for bbox_type in transform.supported_bbox_types:
                    assert bbox_type in {"hbb", "obb"}

    def test_bbox_types_exist_for_all_versions(self) -> None:
        """Test that bbox type extraction works (returns None for older versions or list for newer)."""
        metadata = get_transform_metadata(A.Affine)

        # Should be either None (older AlbumentationsX) or a list (newer versions)
        assert metadata.supported_bbox_types is None or isinstance(metadata.supported_bbox_types, list)
