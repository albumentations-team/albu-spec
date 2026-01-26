"""Albumentations Transform Metadata Extractor.

Extract comprehensive metadata from Albumentations transforms including:
- Parameter names, types, and default values
- Pydantic Field constraints (ge, le, gt, lt, etc.)
- AfterValidator bounds and custom validators
- Parameter descriptions from docstrings
- Structured parsed docstrings with args, examples, notes, etc.
- Type extraction and comparison utilities
"""

from albu_spec.extractor import get_all_transforms_metadata, get_transform_metadata
from albu_spec.models import (
    ConstraintInfo,
    DocstringArg,
    DocstringRaises,
    DocstringReturn,
    ParameterMetadata,
    ParsedDocstring,
    TransformMetadata,
)
from albu_spec.type_comparison import TypeMismatch, compare_types, get_type_mismatch
from albu_spec.type_extraction import (
    get_common_param_names,
    get_init_param_type,
    get_init_schema_param_type,
)

__all__ = [
    "ConstraintInfo",
    "DocstringArg",
    "DocstringRaises",
    "DocstringReturn",
    "ParameterMetadata",
    "ParsedDocstring",
    "TransformMetadata",
    "TypeMismatch",
    "compare_types",
    "get_all_transforms_metadata",
    "get_common_param_names",
    "get_init_param_type",
    "get_init_schema_param_type",
    "get_transform_metadata",
    "get_type_mismatch",
]
