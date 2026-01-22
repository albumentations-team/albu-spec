"""Shared utilities for type annotation handling.

This module provides common functionality used across type extraction,
formatting, and comparison modules to avoid code duplication.
"""

from __future__ import annotations

from typing import Annotated, Any, Literal

import cv2
from pydantic import AfterValidator, Field


def create_type_namespace() -> dict[str, Any]:
    """Create namespace for evaluating type annotations.

    This namespace contains all the common types and typing constructs
    needed to safely evaluate string type annotations using eval().

    Returns:
        Dictionary mapping type names to their corresponding type objects

    """
    return {
        "Annotated": Annotated,
        "Literal": Literal,
        "tuple": tuple,
        "dict": dict,
        "list": list,
        "int": int,
        "float": float,
        "str": str,
        "bool": bool,
        "Any": Any,
        "cv2": cv2,
        "Field": Field,
        "AfterValidator": AfterValidator,
    }


def evaluate_string_annotation(annotation_str: str) -> Any:
    """Evaluate a string type annotation to a type object.

    This function safely evaluates string type annotations (forward references)
    using a restricted namespace containing only safe type constructs.

    Args:
        annotation_str: String representation of type (e.g., 'float', 'int | float')

    Returns:
        Evaluated type object, or the original string if evaluation fails

    Example:
        >>> evaluate_string_annotation('int | float')
        int | float  # Returns actual type object
        >>> evaluate_string_annotation('invalid syntax')
        'invalid syntax'  # Returns string if evaluation fails

    """
    namespace = create_type_namespace()

    try:
        # eval is used here for forward references in type annotations
        # The namespace is restricted to safe type constructs only
        return eval(annotation_str, namespace)
    except (ValueError, NameError, SyntaxError, AttributeError):
        # If evaluation fails, return the string as-is
        # This will be caught by comparison or formatting logic
        return annotation_str
