"""Shared constants for albu-spec."""

from __future__ import annotations

# Transforms to ignore when enumerating Albumentations classes.
IGNORED_CLASSES = {
    "Lambda",
    "BasicTransform",
    "DualTransform",
    "ImageOnlyTransform",
    "Transform3D",
    "BaseTransformInitSchema",
}
