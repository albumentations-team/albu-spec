"""Main extraction orchestrator for transform metadata."""

from __future__ import annotations

import inspect
import sys
from typing import TYPE_CHECKING, Any, cast, get_type_hints

if TYPE_CHECKING:
    from typing import Literal

import albumentations as A

from albu_spec.docstring_parser import DocstringParser
from albu_spec.models import ConstraintInfo, ParameterMetadata, TransformCollection, TransformMetadata
from albu_spec.schema_parser import SchemaParser
from albu_spec.type_formatters import TypeFormatter

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
        self.type_formatter = TypeFormatter()

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
        docstring_parsed = self.docstring_parser.parse_full_docstring(transform_class)
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
        if transform_type in ("image_only", "dual", "transforms_3d"):
            valid_transform_type = cast(
                "Literal['image_only', 'dual', 'transforms_3d', 'unknown']",
                transform_type,
            )
        else:
            valid_transform_type = "unknown"

        return TransformMetadata(
            name=name,
            module=module,
            transform_type=valid_transform_type,
            targets=targets,
            parameters=parameters,
            docstring=docstring,
            docstring_short=docstring_short,
            docstring_parsed=docstring_parsed,
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
            # Get signature from the class __init__ method
            # Access through the class, not instance, to avoid mypy warning
            init_method = transform_class.__init__
            init_signature = inspect.signature(init_method)
        except (ValueError, TypeError, AttributeError):
            return parameters

        # Use get_type_hints to resolve string annotations with module context
        try:
            # Get the module where the transform is defined to access its namespace
            transform_module = sys.modules.get(transform_class.__module__)
            module_globals = vars(transform_module) if transform_module else {}

            type_hints = get_type_hints(
                init_method,
                globalns=module_globals,
                localns={},
                include_extras=True,
            )
        except (ValueError, TypeError, AttributeError, NameError):
            # Fallback to using raw signature annotations
            type_hints = {}

        for param_name, param in init_signature.parameters.items():
            # Skip self and strict (strict is in InitSchema but not actually in __init__)
            if param_name in {"self", "strict"}:
                continue

            # Extract raw type annotation first (separation of concerns)
            raw_type = self._extract_type_annotation(param.annotation, param_name, transform_class)

            # Use resolved type hint if available (handles string annotations properly)
            resolved_type = type_hints.get(param_name, raw_type)

            # Format type for display/JSON
            type_hint = self._format_type(resolved_type)

            # Get default value
            default_value = param.default if param.default is not inspect.Parameter.empty else None

            # Format default value
            formatted_default = self._format_default_value(default_value)

            # Get description from docstring
            description = param_descriptions.get(param_name)

            # Get constraints from schema or from type annotation
            constraints = schema_constraints.get(param_name)
            if constraints is None:
                constraints = self.schema_parser.extract_annotated_constraints(resolved_type)

            parameters[param_name] = ParameterMetadata(
                name=param_name,
                type_hint=type_hint,
                default=formatted_default,
                description=description,
                constraints=constraints,
            )

        return parameters

    def _extract_type_annotation(self, annotation: object, param_name: str, transform_class: type) -> object:
        """Extract raw type annotation, preferring InitSchema if available.

        This method extracts the type annotation without formatting it to a string,
        enabling semantic type comparison and other operations on type objects.

        Args:
            annotation: Type annotation from __init__ parameter
            param_name: Parameter name (for context)
            transform_class: Transform class (for InitSchema lookup)

        Returns:
            Raw type annotation object (not formatted to string)

        """
        if annotation is inspect.Parameter.empty:
            # Try to get type from InitSchema if __init__ has no annotation
            if hasattr(transform_class, "InitSchema"):
                init_schema = transform_class.InitSchema
                if hasattr(init_schema, "model_fields") and param_name in init_schema.model_fields:
                    field_info = init_schema.model_fields[param_name]
                    if hasattr(field_info, "annotation"):
                        return field_info.annotation
            return annotation

        # Prefer InitSchema type if available (it's usually more precise)
        if hasattr(transform_class, "InitSchema"):
            init_schema = transform_class.InitSchema
            if hasattr(init_schema, "model_fields") and param_name in init_schema.model_fields:
                field_info = init_schema.model_fields[param_name]
                if hasattr(field_info, "annotation"):
                    return field_info.annotation

        return annotation

    def _format_type(self, type_annotation: object) -> str | list[Any]:
        """Format a type annotation into a readable string.

        Args:
            type_annotation: Type annotation to format

        Returns:
            Formatted type string or list for Literal types

        """
        # Handle inspect.Parameter.empty
        if type_annotation is inspect.Parameter.empty:
            return "Any"

        return self.type_formatter.format(type_annotation)

    def _format_default_value(self, value: object) -> Any:
        """Format default value for display.

        Args:
            value: Default value to format

        Returns:
            Formatted default value

        """
        if callable(value) and not isinstance(value, type) and hasattr(value, "__name__"):
            return f"<function {value.__name__}>"

        return value

    def _get_transform_type(self, transform_class: type) -> str:
        """Determine the type of transform.

        Args:
            transform_class: Transform class to analyze

        Returns:
            Transform type string

        """
        if issubclass(transform_class, A.Transform3D):
            return "transforms_3d"
        if issubclass(transform_class, A.ImageOnlyTransform):
            return "image_only"
        if issubclass(transform_class, A.DualTransform):
            return "dual"

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
            targets_attr = transform_class._targets

            # Handle various types of _targets
            if isinstance(targets_attr, (list, tuple)) or (
                hasattr(targets_attr, "__iter__") and not isinstance(targets_attr, str)
            ):
                for target in targets_attr:
                    target_str = getattr(target, "value", target)
                    if isinstance(target_str, str):
                        targets.append(target_str.lower())

        return targets

    def get_all_transforms_metadata(self) -> TransformCollection:
        """Extract metadata for all Albumentations transforms.

        Returns:
            TransformCollection with all transforms grouped by type

        """
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
