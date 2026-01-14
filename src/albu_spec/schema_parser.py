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
                for field_name, validators in decorators.field_validators.items():
                    if field_name not in constraints_map:
                        constraints_map[field_name] = ConstraintInfo()
                    for validator in validators:
                        if hasattr(validator, "func"):
                            constraints_map[field_name].validators.append(validator.func.__name__)

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

        # Extract standard Field constraints
        if hasattr(field_info, "ge") and field_info.ge is not None:
            constraints.ge = float(field_info.ge)
            has_constraints = True

        if hasattr(field_info, "le") and field_info.le is not None:
            constraints.le = float(field_info.le)
            has_constraints = True

        if hasattr(field_info, "gt") and field_info.gt is not None:
            constraints.gt = float(field_info.gt)
            has_constraints = True

        if hasattr(field_info, "lt") and field_info.lt is not None:
            constraints.lt = float(field_info.lt)
            has_constraints = True

        if hasattr(field_info, "min_length") and field_info.min_length is not None:
            constraints.min_length = field_info.min_length
            has_constraints = True

        if hasattr(field_info, "max_length") and field_info.max_length is not None:
            constraints.max_length = field_info.max_length
            has_constraints = True

        if hasattr(field_info, "multiple_of") and field_info.multiple_of is not None:
            constraints.multiple_of = float(field_info.multiple_of)
            has_constraints = True

        if hasattr(field_info, "pattern") and field_info.pattern is not None:
            constraints.pattern = field_info.pattern
            has_constraints = True

        # Extract metadata from field_info.metadata (for Annotated types with validators)
        if hasattr(field_info, "metadata") and field_info.metadata:
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
