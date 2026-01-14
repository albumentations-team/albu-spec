"""Albumentations Transform Metadata Extractor.

Extract comprehensive metadata from Albumentations transforms including:
- Parameter names, types, and default values
- Pydantic Field constraints (ge, le, gt, lt, etc.)
- AfterValidator bounds and custom validators
- Parameter descriptions from docstrings
"""

from albu_spec.extractor import get_all_transforms_metadata, get_transform_metadata
from albu_spec.models import ConstraintInfo, ParameterMetadata, TransformMetadata

__version__ = "0.1.0"

__all__ = [
    "get_transform_metadata",
    "get_all_transforms_metadata",
    "TransformMetadata",
    "ParameterMetadata",
    "ConstraintInfo",
]
