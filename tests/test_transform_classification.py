"""Regression coverage for volume-only and tensor transform metadata."""

import albumentations as A
import pytest

from albu_spec import get_all_transforms_metadata, get_transform_metadata


@pytest.mark.parametrize(
    ("transform_class", "expected_group", "expected_targets"),
    [
        (A.Anisotropy3D, "transforms_3d", {"volume"}),
        (A.ToTensor3D, "transforms_3d", {"volume", "mask3d"}),
        (A.ToTensorV2, "dual", {"image", "mask"}),
    ],
)
def test_concrete_transform_classification(transform_class, expected_group, expected_targets):
    """Concrete transforms retain their supported targets in a usable catalog group."""
    metadata = get_transform_metadata(transform_class)
    assert metadata.transform_type == expected_group, f"Unexpected group for {metadata.name}"
    assert set(metadata.targets) == expected_targets, f"Unexpected targets for {metadata.name}"
    assert metadata.supported_bbox_types is None, f"{metadata.name} does not accept bounding boxes"

    collection = get_all_transforms_metadata()
    matches = [item.name for item in getattr(collection, expected_group)]
    assert matches.count(metadata.name) == 1, f"{metadata.name} must occur once in {expected_group}"
    assert metadata.name not in {item.name for item in collection.unknown}, f"{metadata.name} remained unknown"


def test_collection_excludes_volume_base_class():
    """The public collection contains concrete transforms, not the volume base."""
    names = {item.name for item in get_all_transforms_metadata().get_all()}
    assert "VolumeOnlyTransform" not in names, "VolumeOnlyTransform is an abstract base, not an augmentation"
