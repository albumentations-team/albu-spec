"""Semantic comparison of Python type annotations.

This module provides functions to compare type annotations for semantic equivalence,
handling cases like:
- Union order independence: int | float == float | int
- Optional variations: int | None == Optional[int]
- Annotated unwrapping: Annotated[int, ...] == int
- Literal value sets: Literal[1, 2, 3] == Literal[3, 2, 1]
- Nested generics: tuple[int, int] == tuple[int, int]
"""

from __future__ import annotations

import inspect
from dataclasses import dataclass
from typing import Annotated, Any, Literal, Protocol, get_args, get_origin


@dataclass
class TypeMismatch:
    """Detailed information about a type mismatch.

    Attributes:
        type1: First type annotation
        type2: Second type annotation
        reason: Human-readable explanation of why types don't match
        type1_normalized: Normalized representation of type1
        type2_normalized: Normalized representation of type2

    """

    type1: Any
    type2: Any
    reason: str
    type1_normalized: str | None = None
    type2_normalized: str | None = None

    def __str__(self) -> str:
        """Format mismatch as readable string."""
        msg = f"Type mismatch: {self.reason}\n"
        msg += f"  Type 1: {self.type1}\n"
        msg += f"  Type 2: {self.type2}"
        if self.type1_normalized and self.type2_normalized:
            msg += f"\n  Normalized 1: {self.type1_normalized}\n"
            msg += f"  Normalized 2: {self.type2_normalized}"
        return msg


# Strategy Pattern for Type Comparison


class TypeComparisonHandler(Protocol):
    """Protocol for type comparison handlers."""

    def can_handle(self, origin1: Any, origin2: Any) -> bool:
        """Check if this handler can compare these type origins."""
        ...

    def compare(self, type1: Any, type2: Any) -> bool:
        """Compare two types for equivalence."""
        ...

    def get_mismatch(self, type1: Any, type2: Any) -> TypeMismatch | None:
        """Get detailed mismatch information."""
        ...


class LiteralComparisonHandler:
    """Handle comparison of Literal types."""

    def can_handle(self, origin1: Any, origin2: Any) -> bool:
        """Check if both types are Literal."""
        return origin1 is Literal and origin2 is Literal

    def compare(self, type1: Any, type2: Any) -> bool:
        """Compare Literal types by value sets."""
        values1 = set(get_args(type1))
        values2 = set(get_args(type2))
        return values1 == values2

    def get_mismatch(self, type1: Any, type2: Any) -> TypeMismatch | None:
        """Get mismatch details for Literal types."""
        values1 = set(get_args(type1))
        values2 = set(get_args(type2))
        if values1 != values2:
            return TypeMismatch(
                type1=type1,
                type2=type2,
                reason=f"Literal types have different values: {values1} vs {values2}",
                type1_normalized=str(sorted(values1)),
                type2_normalized=str(sorted(values2)),
            )
        return None


class UnionComparisonHandler:
    """Handle comparison of Union types."""

    def can_handle(self, origin1: Any, origin2: Any) -> bool:
        """Check if both types are Union."""
        return _is_union_type(origin1) and _is_union_type(origin2)

    def compare(self, type1: Any, type2: Any) -> bool:
        """Compare Union types by member sets."""
        args1 = get_args(type1)
        args2 = get_args(type2)
        normalized1 = {_normalize_type_arg(arg) for arg in args1}
        normalized2 = {_normalize_type_arg(arg) for arg in args2}
        return normalized1 == normalized2

    def get_mismatch(self, type1: Any, type2: Any) -> TypeMismatch | None:
        """Get mismatch details for Union types."""
        args1 = {_normalize_type_arg(arg) for arg in get_args(type1)}
        args2 = {_normalize_type_arg(arg) for arg in get_args(type2)}
        if args1 != args2:
            return TypeMismatch(
                type1=type1,
                type2=type2,
                reason=f"Union types have different members: {args1} vs {args2}",
                type1_normalized=str(sorted(args1)),
                type2_normalized=str(sorted(args2)),
            )
        return None


class TupleComparisonHandler:
    """Handle comparison of tuple types."""

    def can_handle(self, origin1: Any, origin2: Any) -> bool:
        """Check if both types are tuple."""
        return origin1 is tuple and origin2 is tuple

    def compare(self, type1: Any, type2: Any) -> bool:
        """Compare tuple types element by element."""
        args1 = get_args(type1)
        args2 = get_args(type2)
        if len(args1) != len(args2):
            return False
        return all(compare_types(a1, a2) for a1, a2 in zip(args1, args2, strict=True))

    def get_mismatch(self, type1: Any, type2: Any) -> TypeMismatch | None:
        """Get mismatch details for tuple types."""
        args1 = get_args(type1)
        args2 = get_args(type2)
        if len(args1) != len(args2):
            return TypeMismatch(
                type1=type1,
                type2=type2,
                reason=f"Tuple types have different lengths: {len(args1)} vs {len(args2)}",
            )
        for i, (a1, a2) in enumerate(zip(args1, args2, strict=True)):
            if not compare_types(a1, a2):
                return TypeMismatch(
                    type1=type1,
                    type2=type2,
                    reason=f"Tuple element {i} differs: {a1} vs {a2}",
                )
        return None


class ListComparisonHandler:
    """Handle comparison of list types."""

    def can_handle(self, origin1: Any, origin2: Any) -> bool:
        """Check if both types are list."""
        return origin1 is list and origin2 is list

    def compare(self, type1: Any, type2: Any) -> bool:
        """Compare list types by element type."""
        args1 = get_args(type1)
        args2 = get_args(type2)
        if not args1 and not args2:
            return True
        if bool(args1) != bool(args2):
            return False
        return compare_types(args1[0], args2[0])

    def get_mismatch(self, type1: Any, type2: Any) -> TypeMismatch | None:
        """Get mismatch details for list types."""
        args1 = get_args(type1)
        args2 = get_args(type2)
        if bool(args1) != bool(args2):
            return TypeMismatch(
                type1=type1,
                type2=type2,
                reason="One list type has element type, other doesn't",
            )
        if args1 and not compare_types(args1[0], args2[0]):
            return TypeMismatch(
                type1=type1,
                type2=type2,
                reason=f"List element types differ: {args1[0]} vs {args2[0]}",
            )
        return None


class DictComparisonHandler:
    """Handle comparison of dict types."""

    def can_handle(self, origin1: Any, origin2: Any) -> bool:
        """Check if both types are dict."""
        return origin1 is dict and origin2 is dict

    def compare(self, type1: Any, type2: Any) -> bool:
        """Compare dict types by key and value types."""
        args1 = get_args(type1)
        args2 = get_args(type2)
        if not args1 and not args2:
            return True
        if bool(args1) != bool(args2):
            return False
        min_dict_args = 2
        if len(args1) < min_dict_args or len(args2) < min_dict_args:
            return False
        return compare_types(args1[0], args2[0]) and compare_types(args1[1], args2[1])

    def get_mismatch(self, type1: Any, type2: Any) -> TypeMismatch | None:
        """Get mismatch details for dict types."""
        args1 = get_args(type1)
        args2 = get_args(type2)
        min_dict_args = 2
        if len(args1) < min_dict_args or len(args2) < min_dict_args:
            return TypeMismatch(
                type1=type1,
                type2=type2,
                reason="Dict types don't have both key and value types",
            )
        if not compare_types(args1[0], args2[0]):
            return TypeMismatch(
                type1=type1,
                type2=type2,
                reason=f"Dict key types differ: {args1[0]} vs {args2[0]}",
            )
        if not compare_types(args1[1], args2[1]):
            return TypeMismatch(
                type1=type1,
                type2=type2,
                reason=f"Dict value types differ: {args1[1]} vs {args2[1]}",
            )
        return None


class GenericComparisonHandler:
    """Handle comparison of other generic types."""

    def can_handle(self, origin1: Any, origin2: Any) -> bool:
        """Check if both have same non-None origin."""
        return origin1 is not None and origin1 == origin2

    def compare(self, type1: Any, type2: Any) -> bool:
        """Compare generic types by args."""
        args1 = get_args(type1)
        args2 = get_args(type2)
        if len(args1) != len(args2):
            return False
        return all(compare_types(a1, a2) for a1, a2 in zip(args1, args2, strict=True))

    def get_mismatch(self, type1: Any, type2: Any) -> TypeMismatch | None:
        """Get mismatch details for generic types."""
        args1 = get_args(type1)
        args2 = get_args(type2)
        if len(args1) != len(args2):
            return TypeMismatch(
                type1=type1,
                type2=type2,
                reason=f"Generic types have different arg counts: {len(args1)} vs {len(args2)}",
            )
        for i, (a1, a2) in enumerate(zip(args1, args2, strict=True)):
            if not compare_types(a1, a2):
                return TypeMismatch(
                    type1=type1,
                    type2=type2,
                    reason=f"Generic type arg {i} differs: {a1} vs {a2}",
                )
        return None


class BasicTypeComparisonHandler:
    """Handle comparison of basic types (fallback)."""

    def can_handle(self, origin1: Any, origin2: Any) -> bool:  # noqa: ARG002
        """Always returns True as the fallback handler."""
        return True

    def compare(self, type1: Any, type2: Any) -> bool:
        """Compare basic types by equality."""
        # Handle None types specially
        if _is_none_type(type1) and _is_none_type(type2):
            return True
        return bool(type1 == type2)

    def get_mismatch(self, type1: Any, type2: Any) -> TypeMismatch | None:
        """Get mismatch details for basic types."""
        if _is_none_type(type1) and _is_none_type(type2):
            return None
        if type1 == type2:
            return None
        return TypeMismatch(
            type1=type1,
            type2=type2,
            reason=f"Basic types differ: {type1} != {type2}",
            type1_normalized=str(type1),
            type2_normalized=str(type2),
        )


# Initialize handlers list (order matters - most specific first)
_comparison_handlers: list[TypeComparisonHandler] = [
    LiteralComparisonHandler(),
    UnionComparisonHandler(),
    TupleComparisonHandler(),
    ListComparisonHandler(),
    DictComparisonHandler(),
    GenericComparisonHandler(),
    BasicTypeComparisonHandler(),  # Must be last as fallback (handles None types and basic types)
]


def compare_types(type1: Any, type2: Any) -> bool:
    """Compare two type annotations for semantic equivalence.

    This function performs deep semantic comparison of type annotations,
    handling various edge cases:

    - Union/Optional order: int | float == float | int
    - Annotated unwrapping: Annotated[int, ...] == int
    - Literal value sets: Literal[1, 2] == Literal[2, 1]
    - None variations: type(None) == None
    - Nested generics: tuple[int, int] == tuple[int, int]
    - inspect.Parameter.empty handling

    Args:
        type1: First type annotation
        type2: Second type annotation

    Returns:
        True if types are semantically equivalent, False otherwise

    Example:
        >>> from albu_spec.type_comparison import compare_types
        >>> compare_types(int | float, float | int)
        True
        >>> compare_types(tuple[int, int], tuple[int, int])
        True
        >>> compare_types(int, float)
        False

    """
    # Handle inspect.Parameter.empty
    if type1 is inspect.Parameter.empty or type2 is inspect.Parameter.empty:
        return type1 is type2

    # Unwrap Annotated types
    type1 = _unwrap_annotated(type1)
    type2 = _unwrap_annotated(type2)

    # Get origins for handler dispatch
    origin1 = get_origin(type1)
    origin2 = get_origin(type2)

    # Special case: different origins mean types don't match
    if (
        origin1 != origin2
        and not (_is_union_type(origin1) and _is_union_type(origin2))
        and not (_is_none_type(type1) and _is_none_type(type2))
    ):
        return False

    # Dispatch to appropriate handler
    for handler in _comparison_handlers:
        if handler.can_handle(origin1, origin2):
            return handler.compare(type1, type2)

    # This should never be reached due to BasicTypeComparisonHandler fallback
    return False


def get_type_mismatch(type1: Any, type2: Any) -> TypeMismatch | None:
    """Get detailed information about why two types don't match.

    Args:
        type1: First type annotation
        type2: Second type annotation

    Returns:
        TypeMismatch object if types don't match, None if they do

    Example:
        >>> from albu_spec.type_comparison import get_type_mismatch
        >>> mismatch = get_type_mismatch(int, float)
        >>> if mismatch:
        ...     print(mismatch.reason)
        Basic types differ: int != float

    """
    if compare_types(type1, type2):
        return None

    # Unwrap for analysis
    unwrapped1 = _unwrap_annotated(type1)
    unwrapped2 = _unwrap_annotated(type2)

    origin1 = get_origin(unwrapped1)
    origin2 = get_origin(unwrapped2)

    # Check if origins differ
    if _normalize_origin(origin1) != _normalize_origin(origin2):
        return TypeMismatch(
            type1=type1,
            type2=type2,
            reason=f"Type constructors differ: {_origin_name(origin1)} vs {_origin_name(origin2)}",
            type1_normalized=_origin_name(origin1),
            type2_normalized=_origin_name(origin2),
        )

    # Dispatch to appropriate handler for detailed mismatch info
    for handler in _comparison_handlers:
        if handler.can_handle(origin1, origin2):
            return handler.get_mismatch(unwrapped1, unwrapped2)

    # Fallback - should not be reached
    return TypeMismatch(
        type1=type1,
        type2=type2,
        reason=f"Types differ: {unwrapped1} != {unwrapped2}",
        type1_normalized=str(unwrapped1),
        type2_normalized=str(unwrapped2),
    )


# Private helper functions


def _unwrap_annotated(type_annotation: Any) -> Any:
    """Unwrap Annotated types to get the actual type.

    Args:
        type_annotation: Type to unwrap

    Returns:
        Inner type if Annotated, otherwise original type

    """
    origin = get_origin(type_annotation)
    if origin is Annotated:
        args = get_args(type_annotation)
        if args:
            return args[0]
    return type_annotation


def _is_none_type(type_annotation: Any) -> bool:
    """Check if type annotation represents None type.

    Args:
        type_annotation: Type to check

    Returns:
        True if represents None type

    """
    return type_annotation is None or type_annotation is type(None)


def _is_union_type(origin: Any) -> bool:
    """Check if origin represents a Union type.

    Args:
        origin: Type origin from get_origin()

    Returns:
        True if represents Union (including | syntax)

    """
    if origin is None:
        return False

    # Handle UnionType (from | syntax)
    origin_name = getattr(origin, "__name__", str(origin))
    return "Union" in str(origin) or origin_name == "UnionType"


def _normalize_type_arg(type_arg: Any) -> str:
    """Normalize a type argument to a hashable string for comparison.

    Args:
        type_arg: Type argument to normalize

    Returns:
        String representation for comparison

    """
    # Unwrap Annotated
    unwrapped = _unwrap_annotated(type_arg)

    # Handle None
    if _is_none_type(unwrapped):
        return "None"

    # Get basic representation
    if hasattr(unwrapped, "__name__"):
        name: str = unwrapped.__name__
        return name

    return str(unwrapped)


def _normalize_origin(origin: Any) -> str:
    """Normalize type origin for comparison.

    Args:
        origin: Type origin from get_origin()

    Returns:
        Normalized string representation

    """
    if origin is None:
        return "None"

    # Handle Union variations
    if _is_union_type(origin):
        return "Union"

    if hasattr(origin, "__name__"):
        name: str = origin.__name__
        return name

    return str(origin)


def _origin_name(origin: Any) -> str:
    """Get human-readable name for type origin.

    Args:
        origin: Type origin from get_origin()

    Returns:
        Human-readable name

    """
    if origin is None:
        return "basic type"

    if _is_union_type(origin):
        return "Union"

    if hasattr(origin, "__name__"):
        name: str = origin.__name__
        return name

    return str(origin)
