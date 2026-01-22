"""Type annotation formatters using strategy pattern."""

from __future__ import annotations

from collections.abc import Callable
from typing import Annotated, Any, ForwardRef, Literal, Protocol, get_args, get_origin

from albu_spec.type_utils import evaluate_string_annotation


class TypeHandler(Protocol):
    """Protocol for type annotation handlers."""

    def can_handle(self, type_annotation: object) -> bool:
        """Check if this handler can format the given type annotation.

        Args:
            type_annotation: Type annotation to check

        Returns:
            True if this handler can format the type

        """
        ...

    def format(self, type_annotation: object, formatter: TypeFormatter) -> str | list[Any]:
        """Format the type annotation.

        Args:
            type_annotation: Type annotation to format
            formatter: TypeFormatter for recursive formatting

        Returns:
            Formatted type string or list for Literal types

        """
        ...


class NoneTypeHandler:
    """Handle None type annotations."""

    def can_handle(self, type_annotation: object) -> bool:
        """Check if annotation is None type."""
        return type_annotation is None or type_annotation is type(None)

    def format(self, type_annotation: object, formatter: TypeFormatter) -> str | list[Any]:  # noqa: ARG002
        """Format None type."""
        return "None"


class BasicTypeHandler:
    """Handle basic Python types (int, float, bool, str)."""

    def can_handle(self, type_annotation: object) -> bool:
        """Check if annotation is a basic type."""
        return isinstance(type_annotation, type) and type_annotation in (int, float, bool, str)

    def format(self, type_annotation: object, formatter: TypeFormatter) -> str | list[Any]:  # noqa: ARG002
        """Format basic type."""
        if isinstance(type_annotation, type):
            return type_annotation.__name__
        return "Any"


class StringAnnotationHandler:
    """Handle string type annotations that need evaluation."""

    def can_handle(self, type_annotation: object) -> bool:
        """Check if annotation is a string."""
        return isinstance(type_annotation, str)

    def format(self, type_annotation: object, formatter: TypeFormatter) -> str | list[Any]:
        """Format string annotation by evaluating it."""
        if not isinstance(type_annotation, str):
            return str(type_annotation)

        # Use shared evaluation function
        evaluated = evaluate_string_annotation(type_annotation)

        # If evaluation failed, it returns the string as-is
        # Don't recursively format in this case to avoid infinite loop
        if evaluated is type_annotation or isinstance(evaluated, str):
            return str(type_annotation)

        # Recursively format the evaluated type
        return formatter.format(evaluated)


class ForwardRefHandler:
    """Handle ForwardRef type annotations."""

    def can_handle(self, type_annotation: object) -> bool:
        """Check if annotation is ForwardRef."""
        return isinstance(type_annotation, ForwardRef)

    def _extract_annotated_base_type(self, forward_str: str) -> str | None:
        """Extract base type from Annotated[T, ...] handling nested brackets.

        Args:
            forward_str: String like "Annotated[dict[str, int], Field()]"

        Returns:
            Base type string like "dict[str, int]", or None if extraction fails

        Example:
            >>> self._extract_annotated_base_type("Annotated[dict[str, int], Field()]")
            "dict[str, int]"
            >>> self._extract_annotated_base_type("Annotated[int, Field()]")
            "int"

        """
        # Find the opening bracket after "Annotated"
        start = forward_str.find("Annotated[")
        if start == -1:
            return None

        # Start after "Annotated["
        start += len("Annotated[")

        # Track bracket depth to handle nested generics
        bracket_depth = 0
        i = start

        while i < len(forward_str):
            char = forward_str[i]

            if char == "[":
                bracket_depth += 1
            elif char == "]":
                if bracket_depth == 0:
                    # Found the closing bracket for this type argument
                    return forward_str[start:i].strip()
                bracket_depth -= 1
            elif char == "," and bracket_depth == 0:
                # Found comma at depth 0 - end of first type argument
                return forward_str[start:i].strip()

            i += 1

        return None

    def format(self, type_annotation: object, formatter: TypeFormatter) -> str | list[Any]:
        """Format ForwardRef by evaluating the forward string."""
        if not isinstance(type_annotation, ForwardRef):
            return str(type_annotation)

        # Get the forward reference string
        if hasattr(type_annotation, "__forward_arg__"):
            forward_str = type_annotation.__forward_arg__

            # Try to evaluate it
            evaluated = evaluate_string_annotation(forward_str)

            # If evaluation succeeded and it's not a string, format it
            if evaluated is not forward_str and not isinstance(evaluated, str):
                return formatter.format(evaluated)

            # If evaluation failed but it looks like Annotated[T, ...], extract T
            if "Annotated[" in forward_str:
                # Extract the first type argument from Annotated[T, ...]
                # Use proper bracket matching to handle nested generics like dict[str, int]
                base_type = self._extract_annotated_base_type(forward_str)
                if base_type:
                    # Try to evaluate just the base type
                    evaluated_base = evaluate_string_annotation(base_type)
                    if evaluated_base is not base_type and not isinstance(evaluated_base, str):
                        return formatter.format(evaluated_base)
                    return base_type

            # If evaluation failed, return the string as-is
            return forward_str

        # Fallback: return string representation
        return str(type_annotation)


class LiteralTypeHandler:
    """Handle Literal type annotations."""

    def can_handle(self, type_annotation: object) -> bool:
        """Check if annotation is Literal."""
        return get_origin(type_annotation) is Literal

    def format(self, type_annotation: object, formatter: TypeFormatter) -> str | list[Any]:  # noqa: ARG002
        """Format Literal type - preserve original types."""
        args = get_args(type_annotation)
        return list(args)


class UnionTypeHandler:
    """Handle Union type annotations (including | syntax)."""

    def can_handle(self, type_annotation: object) -> bool:
        """Check if annotation is Union."""
        origin = get_origin(type_annotation)
        if origin is type(int | str):
            return True
        return bool(origin and "Union" in str(origin))

    def format(self, type_annotation: object, formatter: TypeFormatter) -> str | list[Any]:
        """Format Union type."""
        args = get_args(type_annotation)
        formatted_types = [formatter.format(arg) for arg in args]
        # Flatten any nested lists
        flat_types: list[str] = []
        for t in formatted_types:
            if isinstance(t, list):
                flat_types.extend(str(item) for item in t)
            else:
                flat_types.append(str(t))
        return " | ".join(flat_types)


class TupleTypeHandler:
    """Handle tuple type annotations."""

    def can_handle(self, type_annotation: object) -> bool:
        """Check if annotation is tuple."""
        return get_origin(type_annotation) is tuple

    def format(self, type_annotation: object, formatter: TypeFormatter) -> str | list[Any]:
        """Format tuple type."""
        args = get_args(type_annotation)
        if not args:
            return "tuple"

        tuple_ellipsis_length = 2
        if len(args) == tuple_ellipsis_length and args[1] is ...:
            return f"tuple[{formatter.format(args[0])}, ...]"

        formatted_args = [str(formatter.format(arg)) for arg in args]
        return f"tuple[{', '.join(formatted_args)}]"


class ListTypeHandler:
    """Handle list type annotations."""

    def can_handle(self, type_annotation: object) -> bool:
        """Check if annotation is list."""
        return get_origin(type_annotation) is list

    def format(self, type_annotation: object, formatter: TypeFormatter) -> str | list[Any]:
        """Format list type."""
        args = get_args(type_annotation)
        if args:
            return f"list[{formatter.format(args[0])}]"
        return "list"


class DictTypeHandler:
    """Handle dict type annotations."""

    def can_handle(self, type_annotation: object) -> bool:
        """Check if annotation is dict."""
        return get_origin(type_annotation) is dict

    def format(self, type_annotation: object, formatter: TypeFormatter) -> str | list[Any]:
        """Format dict type."""
        args = get_args(type_annotation)
        min_dict_args = 2
        if len(args) >= min_dict_args:
            key_type = formatter.format(args[0])
            value_type = formatter.format(args[1])
            return f"dict[{key_type}, {value_type}]"
        return "dict"


class AnnotatedTypeHandler:
    """Handle Annotated type annotations."""

    def can_handle(self, type_annotation: object) -> bool:
        """Check if annotation is Annotated."""
        origin = get_origin(type_annotation)
        return origin is Annotated

    def format(self, type_annotation: object, formatter: TypeFormatter) -> str | list[Any]:
        """Format Annotated type - extract the actual type."""
        args = get_args(type_annotation)
        if args:
            return formatter.format(args[0])
        return "Annotated"


class CallableTypeHandler:
    """Handle Callable type annotations."""

    def can_handle(self, type_annotation: object) -> bool:
        """Check if annotation is Callable."""
        origin = get_origin(type_annotation)
        if origin is Callable:
            return True
        return bool(origin and "Callable" in str(origin))

    def format(self, type_annotation: object, formatter: TypeFormatter) -> str | list[Any]:
        """Format Callable type."""
        args = get_args(type_annotation)
        min_callable_args = 2
        if args and len(args) >= min_callable_args:
            return f"Callable[..., {formatter.format(args[-1])}]"
        return "Callable"


class DefaultTypeHandler:
    """Default handler for types that don't match other handlers."""

    def can_handle(self, type_annotation: object) -> bool:  # noqa: ARG002
        """Always returns True as the fallback handler."""
        return True

    def format(self, type_annotation: object, formatter: TypeFormatter) -> str | list[Any]:  # noqa: ARG002
        """Format type using __name__ or string representation."""
        if hasattr(type_annotation, "__name__"):
            return str(type_annotation.__name__)
        return str(type_annotation)


class TypeFormatter:
    """Coordinator that dispatches type formatting to appropriate handlers."""

    def __init__(self) -> None:
        """Initialize the type formatter with all handlers."""
        self.handlers: list[TypeHandler] = [
            NoneTypeHandler(),
            BasicTypeHandler(),
            StringAnnotationHandler(),
            ForwardRefHandler(),
            LiteralTypeHandler(),
            UnionTypeHandler(),
            TupleTypeHandler(),
            ListTypeHandler(),
            DictTypeHandler(),
            AnnotatedTypeHandler(),
            CallableTypeHandler(),
            DefaultTypeHandler(),  # Must be last as it always matches
        ]

    def format(self, type_annotation: object) -> str | list[Any]:
        """Format a type annotation using the appropriate handler.

        Args:
            type_annotation: Type annotation to format

        Returns:
            Formatted type string or list for Literal types

        """
        for handler in self.handlers:
            if handler.can_handle(type_annotation):
                return handler.format(type_annotation, self)

        # This should never be reached due to DefaultTypeHandler
        return "Any"
