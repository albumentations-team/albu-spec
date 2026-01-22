"""Extract raw type annotations from transform constructors and InitSchema.

This module provides functions to extract type objects (not strings) from:
1. __init__ method signatures
2. Pydantic InitSchema model_fields

These raw types can be used for semantic comparison or formatted to strings.
"""

from __future__ import annotations

import inspect
from typing import Any

from albu_spec.type_utils import evaluate_string_annotation


def get_init_param_type(transform_class: type, param_name: str) -> Any:
    """Extract raw type annotation from __init__ signature.

    Args:
        transform_class: Transform class to inspect
        param_name: Parameter name to extract type for

    Returns:
        Raw type annotation object (e.g., int | float, tuple[int, int])
        Returns inspect.Parameter.empty if parameter has no annotation

    Raises:
        ValueError: If parameter doesn't exist in __init__ signature

    Example:
        >>> import albumentations as A
        >>> from albu_spec.type_extraction import get_init_param_type
        >>> param_type = get_init_param_type(A.Blur, 'blur_limit')
        >>> # Returns: tuple[int, int] | int (as type object, not string)

    """
    try:
        init_method = transform_class.__init__
        sig = inspect.signature(init_method)
    except (ValueError, TypeError, AttributeError) as e:
        msg = f"Cannot get signature for {transform_class.__name__}.__init__"
        raise ValueError(msg) from e

    if param_name not in sig.parameters:
        msg = (
            f"Parameter '{param_name}' not found in {transform_class.__name__}.__init__. "
            f"Available parameters: {list(sig.parameters.keys())}"
        )
        raise ValueError(msg)

    param = sig.parameters[param_name]
    annotation = param.annotation

    # If annotation is a string (forward reference), evaluate it
    if isinstance(annotation, str):
        annotation = evaluate_string_annotation(annotation)

    return annotation


def get_init_schema_param_type(transform_class: type, param_name: str) -> Any:
    """Extract raw type annotation from InitSchema model_fields.

    Args:
        transform_class: Transform class to inspect
        param_name: Parameter name to extract type for

    Returns:
        Raw type annotation from InitSchema field
        Returns None if InitSchema doesn't exist or field not found

    Raises:
        ValueError: If transform has no InitSchema or parameter doesn't exist

    Example:
        >>> import albumentations as A
        >>> from albu_spec.type_extraction import get_init_schema_param_type
        >>> param_type = get_init_schema_param_type(A.Blur, 'blur_limit')
        >>> # Returns: tuple[int, int] | int (as type object, not string)

    """
    if not hasattr(transform_class, "InitSchema"):
        msg = f"{transform_class.__name__} has no InitSchema"
        raise ValueError(msg)

    init_schema = transform_class.InitSchema

    if not hasattr(init_schema, "model_fields"):
        msg = f"{transform_class.__name__}.InitSchema has no model_fields"
        raise ValueError(msg)

    if param_name not in init_schema.model_fields:
        msg = (
            f"Parameter '{param_name}' not found in {transform_class.__name__}.InitSchema. "
            f"Available fields: {list(init_schema.model_fields.keys())}"
        )
        raise ValueError(msg)

    field_info = init_schema.model_fields[param_name]

    if not hasattr(field_info, "annotation"):
        return None

    return field_info.annotation


def get_common_param_names(transform_class: type) -> set[str]:
    """Get parameter names that exist in both __init__ and InitSchema.

    Args:
        transform_class: Transform class to inspect

    Returns:
        Set of parameter names present in both __init__ and InitSchema
        Excludes 'self' and 'strict'

    Example:
        >>> import albumentations as A
        >>> from albu_spec.type_extraction import get_common_param_names
        >>> params = get_common_param_names(A.HorizontalFlip)
        >>> # Returns: {'p'}

    """
    # Get __init__ params
    try:
        sig = inspect.signature(transform_class.__init__)
        init_params = {name for name in sig.parameters if name not in {"self", "strict"}}
    except (ValueError, TypeError, AttributeError):
        init_params = set()

    # Get InitSchema params
    if not hasattr(transform_class, "InitSchema"):
        return set()

    init_schema = transform_class.InitSchema
    if not hasattr(init_schema, "model_fields"):
        return set()

    schema_params = {name for name in init_schema.model_fields if name != "strict"}

    # Return intersection
    return init_params & schema_params
