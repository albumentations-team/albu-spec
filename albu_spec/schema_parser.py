"""Parser for extracting constraints from Pydantic InitSchema classes."""

import inspect
from typing import Annotated, Any, get_args, get_origin

from pydantic.fields import FieldInfo

from albu_spec.models import ConstraintInfo


class SchemaParser:
    """Extract constraints from Pydantic InitSchema classes."""

    def extract_schema_constraints(self, transform_class: type) -> dict[str, ConstraintInfo]:
        """Extract constraints from InitSchema if it exists.

        Args:
            transform_class: The transform class to inspect

        Returns:
            Dictionary mapping parameter names to their constraints
        """
        constraints_map: dict[str, ConstraintInfo] = {}

        # Check if the transform has an InitSchema
        if not hasattr(transform_class, "InitSchema"):
            return constraints_map

        init_schema = transform_class.InitSchema

        # Get the model fields from the schema
        if hasattr(init_schema, "model_fields"):
            for field_name, field_info in init_schema.model_fields.items():
                constraints = self._extract_field_constraints(field_name, field_info)
                if constraints:
                    constraints_map[field_name] = constraints

        # Also check for validators
        if hasattr(init_schema, "__pydantic_decorators__"):
            decorators = init_schema.__pydantic_decorators__
            if hasattr(decorators, "field_validators"):
                for field_name, decorator in decorators.field_validators.items():
                    if field_name not in constraints_map:
                        constraints_map[field_name] = ConstraintInfo()
                    # Decorator object has a 'func' attribute
                    if hasattr(decorator, "func"):
                        constraints_map[field_name].validators.append(decorator.func.__name__)

        return constraints_map

    def _extract_field_constraints(self, field_name: str, field_info: FieldInfo) -> ConstraintInfo | None:
        """Extract constraints from a Pydantic FieldInfo object.

        Args:
            field_name: Name of the field
            field_info: Pydantic FieldInfo object

        Returns:
            ConstraintInfo object with extracted constraints, or None if no constraints
        """
        constraints = ConstraintInfo()
        has_constraints = False

        # In Pydantic v2, constraints are stored in metadata list
        if hasattr(field_info, "metadata") and field_info.metadata:
            for metadata_item in field_info.metadata:
                # Check for constraint objects (Ge, Le, Gt, Lt, etc.)
                metadata_type = type(metadata_item).__name__

                if metadata_type == "Ge" and hasattr(metadata_item, "ge"):
                    constraints.ge = float(metadata_item.ge)
                    has_constraints = True
                elif metadata_type == "Le" and hasattr(metadata_item, "le"):
                    constraints.le = float(metadata_item.le)
                    has_constraints = True
                elif metadata_type == "Gt" and hasattr(metadata_item, "gt"):
                    constraints.gt = float(metadata_item.gt)
                    has_constraints = True
                elif metadata_type == "Lt" and hasattr(metadata_item, "lt"):
                    constraints.lt = float(metadata_item.lt)
                    has_constraints = True
                elif metadata_type == "MinLen" and hasattr(metadata_item, "min_length"):
                    constraints.min_length = metadata_item.min_length
                    has_constraints = True
                elif metadata_type == "MaxLen" and hasattr(metadata_item, "max_length"):
                    constraints.max_length = metadata_item.max_length
                    has_constraints = True
                elif metadata_type == "MultipleOf" and hasattr(metadata_item, "multiple_of"):
                    constraints.multiple_of = float(metadata_item.multiple_of)
                    has_constraints = True
                elif metadata_type == "_PydanticGeneralMetadata" and hasattr(metadata_item, "pattern"):
                    constraints.pattern = metadata_item.pattern
                    has_constraints = True

            # Also extract validator info from metadata
            validator_info = self._extract_validator_metadata(field_info.metadata)
            if validator_info:
                constraints.validator_info.update(validator_info)
                has_constraints = True

        return constraints if has_constraints else None

    def _extract_validator_metadata(self, metadata: list[Any]) -> dict[str, Any]:
        """Extract information from Annotated type validators.

        Args:
            metadata: List of metadata from Annotated type

        Returns:
            Dictionary of validator information
        """
        validator_info: dict[str, Any] = {}

        for item in metadata:
            # Check for AfterValidator
            if hasattr(item, "__class__") and "AfterValidator" in item.__class__.__name__:
                if hasattr(item, "func"):
                    func = item.func
                    func_name = func.__name__ if hasattr(func, "__name__") else str(func)
                    validator_info[func_name] = self._analyze_validator_function(func)

            # Check for other validator types
            elif hasattr(item, "__class__") and "Validator" in item.__class__.__name__:
                class_name = item.__class__.__name__
                if hasattr(item, "func"):
                    func = item.func
                    func_name = func.__name__ if hasattr(func, "__name__") else str(func)
                    validator_info[f"{class_name}_{func_name}"] = self._analyze_validator_function(func)

        return validator_info

    def _analyze_validator_function(self, func: Any) -> dict[str, Any]:
        """Analyze a validator function to extract constraint information.

        Args:
            func: Validator function

        Returns:
            Dictionary with validator analysis
        """
        info: dict[str, Any] = {}

        # Try to get the function source to extract bounds
        try:
            source = inspect.getsource(func)
            info["source_available"] = True

            # Look for common patterns like check_range_bounds(min, max)
            if "check_range_bounds" in source:
                # Try to extract the bounds from the source
                info["type"] = "range_bounds"
                # This is a heuristic - you might need to make it more robust
                import re

                bounds_match = re.search(r"check_range_bounds\s*\(\s*([-\d.]+)\s*,\s*([-\d.]+)\s*\)", source)
                if bounds_match:
                    info["min_value"] = float(bounds_match.group(1))
                    info["max_value"] = float(bounds_match.group(2))

            elif "nondecreasing" in source:
                info["type"] = "nondecreasing"
                info["description"] = "Values must be in non-decreasing order"

        except (OSError, TypeError):
            info["source_available"] = False

        # Get function name and docstring
        if hasattr(func, "__name__"):
            info["function_name"] = func.__name__

        if hasattr(func, "__doc__") and func.__doc__:
            info["docstring"] = func.__doc__.strip()

        return info

    def extract_annotated_constraints(self, type_annotation: Any) -> ConstraintInfo | None:
        """Extract constraints from Annotated type hints.

        Args:
            type_annotation: Type annotation to analyze

        Returns:
            ConstraintInfo if constraints found, None otherwise
        """
        origin = get_origin(type_annotation)

        if origin is Annotated:
            args = get_args(type_annotation)
            if len(args) > 1:
                # First arg is the actual type, rest are metadata
                metadata = args[1:]
                constraints = ConstraintInfo()
                has_constraints = False

                validator_info = self._extract_validator_metadata(list(metadata))
                if validator_info:
                    constraints.validator_info.update(validator_info)
                    has_constraints = True

                    # Try to extract min/max from validator info
                    for validator_name, validator_data in validator_info.items():
                        if isinstance(validator_data, dict):
                            if "min_value" in validator_data:
                                constraints.min_value = validator_data["min_value"]
                            if "max_value" in validator_data:
                                constraints.max_value = validator_data["max_value"]

                return constraints if has_constraints else None

        return None
