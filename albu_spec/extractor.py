"""Main extraction orchestrator for transform metadata."""

from __future__ import annotations

import inspect
import typing
from collections.abc import Callable
from typing import Annotated, Any, Literal, get_args, get_origin

from albu_spec.docstring_parser import DocstringParser
from albu_spec.models import ConstraintInfo, ParameterMetadata, TransformCollection, TransformMetadata
from albu_spec.schema_parser import SchemaParser

# Transforms to ignore
IGNORED_CLASSES = {
    "Lambda",
    "BasicTransform",
    "DualTransform",
    "ImageOnlyTransform",
    "Transform3D",
    "TextImage",
    "PiecewiseAffine",
    "OverlayElements",
    "BaseTransformInitSchema",
}


class TransformMetadataExtractor:
    """Extract comprehensive metadata from Albumentations transforms."""

    def __init__(self) -> None:
        """Initialize the metadata extractor."""
        self.schema_parser = SchemaParser()
        self.docstring_parser = DocstringParser()

    def get_transform_metadata(self, transform_class: type) -> TransformMetadata:
        """Extract complete metadata for a single transform.

        Args:
            transform_class: The transform class to analyze

        Returns:
            TransformMetadata object containing all extracted information

        """
        # Get basic information
        name = transform_class.__name__
        module = transform_class.__module__
        transform_type = self._get_transform_type(transform_class)
        targets = self._get_targets(transform_class)
        has_init_schema = hasattr(transform_class, "InitSchema")

        # Get docstring information
        docstring = transform_class.__doc__
        docstring_short = self.docstring_parser.get_short_description(transform_class)
        param_descriptions = self.docstring_parser.parse_docstring(transform_class)

        # Get schema constraints
        schema_constraints = self.schema_parser.extract_schema_constraints(transform_class)

        # Extract parameters from __init__
        parameters = self._extract_parameters(
            transform_class,
            param_descriptions,
            schema_constraints,
        )

        # Cast transform_type to Literal type expected by TransformMetadata
        valid_transform_type: Literal["image_only", "dual", "transforms_3d", "unknown"] = (
            transform_type if transform_type in ("image_only", "dual", "transforms_3d", "unknown") else "unknown"  # type: ignore[assignment]
        )

        return TransformMetadata(
            name=name,
            module=module,
            transform_type=valid_transform_type,
            targets=targets,
            parameters=parameters,
            docstring=docstring,
            docstring_short=docstring_short,
            has_init_schema=has_init_schema,
        )

    def _extract_parameters(
        self,
        transform_class: type,
        param_descriptions: dict[str, str],
        schema_constraints: dict[str, ConstraintInfo],
    ) -> dict[str, ParameterMetadata]:
        """Extract parameter metadata from __init__ signature.

        Args:
            transform_class: The transform class
            param_descriptions: Parameter descriptions from docstring
            schema_constraints: Constraints from InitSchema

        Returns:
            Dictionary mapping parameter names to their metadata

        """
        parameters: dict[str, ParameterMetadata] = {}

        try:
            # Get __init__ from class, not instance
            init_method = transform_class.__init__  # type: ignore[misc]
            init_signature = inspect.signature(init_method)
        except (ValueError, TypeError):
            return parameters

        for param_name, param in init_signature.parameters.items():
            # Skip self and strict (strict is in InitSchema but not actually in __init__)
            if param_name in {"self", "strict"}:
                continue

            # Get type hint
            type_hint = self._format_type_hint(param.annotation, param_name, transform_class)

            # Get default value
            default_value = param.default if param.default is not inspect.Parameter.empty else None

            # Format default value
            formatted_default = self._format_default_value(default_value)

            # Get description from docstring
            description = param_descriptions.get(param_name)

            # Get constraints from schema or from type annotation
            constraints = schema_constraints.get(param_name)
            if constraints is None and param.annotation is not inspect.Parameter.empty:
                # Try to extract from Annotated types
                constraints = self.schema_parser.extract_annotated_constraints(param.annotation)

            parameters[param_name] = ParameterMetadata(
                name=param_name,
                type_hint=type_hint,
                default=formatted_default,
                description=description,
                constraints=constraints,
            )

        return parameters

    def _format_type_hint(self, annotation: object, param_name: str, transform_class: type) -> str | list[Any]:
        """Format type annotation as human-readable string.

        Args:
            annotation: Type annotation
            param_name: Parameter name (for context)
            transform_class: Transform class (for InitSchema lookup)

        Returns:
            Formatted type string or list of strings for Literal types

        """
        if annotation is inspect.Parameter.empty:
            return "Any"

        # Try to get more precise type from InitSchema if available
        if hasattr(transform_class, "InitSchema"):
            init_schema = transform_class.InitSchema
            if hasattr(init_schema, "model_fields") and param_name in init_schema.model_fields:
                field_info = init_schema.model_fields[param_name]
                if hasattr(field_info, "annotation"):
                    annotation = field_info.annotation

        return self._format_type(annotation)

    def _format_type(self, type_annotation: object) -> str | list[Any]:  # noqa: C901, PLR0911, PLR0912
        """Format a type annotation into a readable string.

        Args:
            type_annotation: Type annotation to format

        Returns:
            Formatted type string or list for Literal types

        """
        # Handle None
        if type_annotation is None or type_annotation is type(None):
            return "None"

        # Handle basic types
        if type_annotation in (int, float, bool, str):
            return str(type_annotation.__name__)

        # Handle string annotations - evaluate them first
        if isinstance(type_annotation, str):
            try:
                # Try to evaluate the string annotation
                import cv2  # noqa: PLC0415

                # Create namespace with common imports
                namespace = {
                    "Literal": typing.Literal,
                    "Union": typing.Union,
                    "Optional": typing.Optional,
                    "tuple": tuple,
                    "dict": dict,
                    "list": list,
                    "int": int,
                    "float": float,
                    "str": str,
                    "bool": bool,
                    "cv2": cv2,
                }
                evaluated = eval(type_annotation, namespace)  # noqa: S307
                # Recursively format the evaluated type
                return self._format_type(evaluated)
            except (ValueError, NameError, SyntaxError, AttributeError):
                # If evaluation fails, return string as-is
                return str(type_annotation)

        # Get origin and args
        origin = get_origin(type_annotation)
        args = get_args(type_annotation)

        # Handle Literal - preserve original types (ints, strings, etc.)
        if origin is Literal:
            return list(args)

        # Handle Union (including | syntax)
        if origin is type(int | str) or (origin and "Union" in str(origin)):
            formatted_types = [self._format_type(arg) for arg in args]
            # Flatten any nested lists
            flat_types: list[str] = []
            for t in formatted_types:
                if isinstance(t, list):
                    flat_types.extend(str(item) for item in t)
                else:
                    flat_types.append(str(t))
            return " | ".join(flat_types)

        # Handle tuple
        tuple_ellipsis_length = 2
        if origin is tuple:
            if args:
                if len(args) == tuple_ellipsis_length and args[1] is ...:
                    return f"tuple[{self._format_type(args[0])}, ...]"
                formatted_args = [str(self._format_type(arg)) for arg in args]
                return f"tuple[{', '.join(formatted_args)}]"
            return "tuple"

        # Handle list
        if origin is list:
            if args:
                return f"list[{self._format_type(args[0])}]"
            return "list"

        # Handle dict
        min_dict_args = 2
        if origin is dict:
            if len(args) >= min_dict_args:
                key_type = self._format_type(args[0])
                value_type = self._format_type(args[1])
                return f"dict[{key_type}, {value_type}]"
            return "dict"

        # Handle Annotated
        if origin is Annotated:
            if args:
                return self._format_type(args[0])
            return "Annotated"

        # Handle Callable
        min_callable_args = 2
        if origin is Callable or (origin and "Callable" in str(origin)):
            if args and len(args) >= min_callable_args:
                return f"Callable[..., {self._format_type(args[-1])}]"
            return "Callable"

        # Fallback: use __name__ or string representation
        if hasattr(type_annotation, "__name__"):
            return str(type_annotation.__name__)

        return str(type_annotation)

    def _format_default_value(self, value: object) -> Any:  # noqa: ANN401
        """Format default value for display.

        Args:
            value: Default value to format

        Returns:
            Formatted default value

        """
        if callable(value) and not isinstance(value, type):
            return f"<function {value.__name__}>"

        return value

    def _get_transform_type(self, transform_class: type) -> str:
        """Determine the type of transform.

        Args:
            transform_class: Transform class to analyze

        Returns:
            Transform type string

        """
        try:
            # Try to import albumentations classes
            import albumentations as A  # noqa: PLC0415

            if issubclass(transform_class, A.Transform3D):
                return "transforms_3d"
            if issubclass(transform_class, A.ImageOnlyTransform):
                return "image_only"
            if issubclass(transform_class, A.DualTransform):
                return "dual"
        except (ImportError, TypeError):
            pass

        return "unknown"

    def _get_targets(self, transform_class: type) -> list[str]:
        """Get supported targets for the transform.

        Args:
            transform_class: Transform class to analyze

        Returns:
            List of target names

        """
        targets: list[str] = []

        if hasattr(transform_class, "_targets"):
            targets_attr = transform_class._targets  # noqa: SLF001

            # Handle various types of _targets
            if isinstance(targets_attr, (list, tuple)) or (
                hasattr(targets_attr, "__iter__") and not isinstance(targets_attr, str)
            ):
                for target in targets_attr:
                    target_str = getattr(target, "value", target)
                    if isinstance(target_str, str):
                        targets.append(target_str.lower())

        return targets

    def get_all_transforms_metadata(self) -> TransformCollection:  # noqa: C901
        """Extract metadata for all Albumentations transforms.

        Returns:
            TransformCollection with all transforms grouped by type

        """
        try:
            import albumentations as A  # noqa: PLC0415
        except ImportError as err:
            msg = "albumentations package is not installed. Please install it to extract transform metadata."
            raise ImportError(msg) from err

        collection = TransformCollection()

        # Find all transform classes
        for name, obj in inspect.getmembers(A, predicate=inspect.isclass):
            # Skip ignored classes
            if name in IGNORED_CLASSES:
                continue

            # Check if it's a transform
            try:
                if not issubclass(obj, A.BasicTransform):
                    continue
                if obj is A.BasicTransform:
                    continue
            except TypeError:
                continue

            # Extract metadata
            try:
                metadata = self.get_transform_metadata(obj)

                # Add to appropriate category
                if metadata.transform_type == "image_only":
                    collection.image_only.append(metadata)
                elif metadata.transform_type == "dual":
                    collection.dual.append(metadata)
                elif metadata.transform_type == "transforms_3d":
                    collection.transforms_3d.append(metadata)
                else:
                    collection.unknown.append(metadata)
            except (ValueError, TypeError, AttributeError):
                # Skip transforms that fail to extract
                continue

        return collection


# Public API functions
def get_transform_metadata(transform_class: type) -> TransformMetadata:
    """Extract metadata for a single transform.

    Args:
        transform_class: The transform class to analyze

    Returns:
        TransformMetadata object with all extracted information

    Example:
        >>> import albumentations as A
        >>> from albu_spec import get_transform_metadata
        >>> metadata = get_transform_metadata(A.Blur)
        >>> print(metadata.name)
        'Blur'
        >>> print(metadata.parameters['blur_limit'].type_hint)
        'tuple[int, int] | int'

    """
    extractor = TransformMetadataExtractor()
    return extractor.get_transform_metadata(transform_class)


def get_all_transforms_metadata() -> TransformCollection:
    """Extract metadata for all Albumentations transforms.

    Returns:
        TransformCollection with all transforms grouped by type

    Example:
        >>> from albu_spec import get_all_transforms_metadata
        >>> collection = get_all_transforms_metadata()
        >>> print(f"Found {collection.total_count} transforms")
        >>> print(f"Image-only: {len(collection.image_only)}")
        >>> print(f"Dual: {len(collection.dual)}")

    """
    extractor = TransformMetadataExtractor()
    return extractor.get_all_transforms_metadata()
