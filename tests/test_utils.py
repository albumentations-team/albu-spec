"""Shared test utilities for albu-spec tests."""

from __future__ import annotations

import inspect


def normalize_type_string(type_str: str | list[str]) -> set[str]:
    """Normalize type string for comparison.

    Type hints may differ in formatting but be semantically identical:
    - "int | float" vs "float | int" (order doesn't matter)
    - Whitespace variations

    Args:
        type_str: Type string or list of strings (for Literal types)

    Returns:
        Set of normalized type parts for comparison

    """
    if isinstance(type_str, list):
        # Literal types as list
        return {str(item).strip() for item in type_str}

    # Union types as string
    return {part.strip() for part in str(type_str).split(" | ")}


def assert_types_match(actual: str | list[str], expected: str | list[str], context: str = "") -> None:
    """Assert that two type representations match after normalization.

    Args:
        actual: Actual type from extraction
        expected: Expected type
        context: Context for error message

    """
    actual_norm = normalize_type_string(actual)
    expected_norm = normalize_type_string(expected)

    assert actual_norm == expected_norm, (
        f"Type mismatch{' in ' + context if context else ''}: expected {expected} but got {actual}"
    )


def get_init_params(transform_class: type) -> set[str]:
    """Get parameter names from __init__ signature (excluding self).

    Args:
        transform_class: Transform class to inspect

    Returns:
        Set of parameter names (including p and strict if present)

    """
    try:
        sig = inspect.signature(transform_class.__init__)
        return {
            name
            for name, param in sig.parameters.items()
            if name != "self" and param.kind not in {inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD}
        }
    except (ValueError, TypeError):
        return set()


def get_init_schema_params(transform_class: type) -> set[str]:
    """Get parameter names from InitSchema model_fields.

    Note: Filters out 'strict' which is defined in BaseTransformInitSchema
    but not actually accepted by transform __init__ methods (AlbumentationsX bug).

    Args:
        transform_class: Transform class to inspect

    Returns:
        Set of parameter names, empty if no InitSchema

    """
    if not hasattr(transform_class, "InitSchema"):
        return set()

    init_schema = transform_class.InitSchema

    if hasattr(init_schema, "model_fields"):
        # Filter out 'strict' - it's in BaseTransformInitSchema but not in __init__
        return {name for name in init_schema.model_fields.keys() if name != "strict"}

    return set()
