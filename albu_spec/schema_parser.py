"""Parser for extracting constraints from Pydantic InitSchema classes."""

import inspect
import re
from collections.abc import Callable
from typing import Annotated, Any, ForwardRef, get_args, get_origin

from pydantic.fields import FieldInfo

from albu_spec.models import ConstraintInfo
from albu_spec.type_utils import evaluate_string_annotation

# Mapping of metadata type names to constraint attributes and value extractors
CONSTRAINT_MAPPING: dict[str, tuple[str, str]] = {
    "Ge": ("ge", "ge"),
    "Le": ("le", "le"),
    "Gt": ("gt", "gt"),
    "Lt": ("lt", "lt"),
    "MinLen": ("min_length", "min_length"),
    "MaxLen": ("max_length", "max_length"),
    "MultipleOf": ("multiple_of", "multiple_of"),
}


class SchemaParser:
    """Extract constraints from Pydantic InitSchema classes."""

    def extract_schema_constraints(self, transform_class: type) -> dict[str, ConstraintInfo]:
        """Extract constraints from InitSchema if it exists.

        Args:
            transform_class: The transform class to inspect

        Returns:
            Dictionary mapping parameter names to their constraints

        """
        if not hasattr(transform_class, "InitSchema"):
            return {}

        init_schema = transform_class.InitSchema
        constraints_map = self._extract_field_constraints_from_schema(init_schema)
        self._extract_validator_constraints(init_schema, constraints_map)

        return constraints_map

    def _extract_field_constraints_from_schema(self, init_schema: type) -> dict[str, ConstraintInfo]:
        """Extract field constraints from InitSchema model_fields.

        Args:
            init_schema: The InitSchema class

        Returns:
            Dictionary mapping field names to their constraints

        """
        constraints_map: dict[str, ConstraintInfo] = {}

        if hasattr(init_schema, "model_fields"):
            for field_name, field_info in init_schema.model_fields.items():
                constraints = self._extract_field_constraints(field_name, field_info)
                if constraints:
                    constraints_map[field_name] = constraints

        return constraints_map

    def _extract_validator_constraints(self, init_schema: type, constraints_map: dict[str, ConstraintInfo]) -> None:
        """Extract validator information from InitSchema decorators.

        Args:
            init_schema: The InitSchema class
            constraints_map: Dictionary to update with validator information

        """
        if not hasattr(init_schema, "__pydantic_decorators__"):
            return

        decorators = init_schema.__pydantic_decorators__
        if not hasattr(decorators, "field_validators"):
            return

        for decorator in decorators.field_validators.values():
            self._process_field_validator(decorator, constraints_map)

    def _process_field_validator(self, decorator: Any, constraints_map: dict[str, ConstraintInfo]) -> None:
        """Process a single field validator decorator.

        Args:
            decorator: The validator decorator
            constraints_map: Dictionary to update with validator information

        """
        if not (hasattr(decorator, "info") and hasattr(decorator.info, "fields")):
            return

        field_names = decorator.info.fields
        if not hasattr(decorator, "func"):
            return

        validator_name = decorator.func.__name__
        for field_name in field_names:
            if field_name not in constraints_map:
                constraints_map[field_name] = ConstraintInfo()
            constraints_map[field_name].validators.append(validator_name)

    def _extract_field_constraints(self, _field_name: str, field_info: FieldInfo) -> ConstraintInfo | None:
        """Extract constraints from a Pydantic FieldInfo object.

        Args:
            _field_name: Name of the field (unused, kept for API compatibility)
            field_info: Pydantic FieldInfo object

        Returns:
            ConstraintInfo object with extracted constraints, or None if no constraints

        """
        constraints = ConstraintInfo()
        has_constraints = False

        # In Pydantic v2, constraints are stored in metadata list
        if hasattr(field_info, "metadata") and field_info.metadata:
            for metadata_item in field_info.metadata:
                # Check for constraint objects using mapping
                metadata_type = type(metadata_item).__name__

                if metadata_type in CONSTRAINT_MAPPING:
                    constraint_attr, value_attr = CONSTRAINT_MAPPING[metadata_type]
                    if hasattr(metadata_item, value_attr):
                        value = getattr(metadata_item, value_attr)
                        # Convert to float for numeric constraints
                        if constraint_attr in ("ge", "le", "gt", "lt", "multiple_of"):
                            value = float(value)
                        setattr(constraints, constraint_attr, value)
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

    def _analyze_validator_function(self, func: Callable[..., Any]) -> dict[str, Any]:
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

                # Regex only handles literal numeric values
                # Variables/expressions need manual inspection
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

    def _handle_forward_ref(self, type_annotation: ForwardRef) -> Any:
        """Handle ForwardRef by attempting evaluation.

        Args:
            type_annotation: ForwardRef to evaluate

        Returns:
            Evaluated type object or None if evaluation fails

        """
        # Try to evaluate the ForwardRef to get the actual type
        if hasattr(type_annotation, "__forward_evaluated__") and type_annotation.__forward_evaluated__:
            return type_annotation.__forward_value__
        if hasattr(type_annotation, "__forward_arg__"):
            forward_str = type_annotation.__forward_arg__
            evaluated = evaluate_string_annotation(forward_str)
            if evaluated is not forward_str and not isinstance(evaluated, str):
                return evaluated
        return None

    def _merge_field_constraints(self, target: ConstraintInfo, source: ConstraintInfo) -> None:  # noqa: C901
        """Merge constraint fields from source to target.

        Args:
            target: Constraint object to merge into
            source: Constraint object to merge from

        """
        if source.ge is not None:
            target.ge = source.ge
        if source.le is not None:
            target.le = source.le
        if source.gt is not None:
            target.gt = source.gt
        if source.lt is not None:
            target.lt = source.lt
        if source.min_length is not None:
            target.min_length = source.min_length
        if source.max_length is not None:
            target.max_length = source.max_length
        if source.multiple_of is not None:
            target.multiple_of = source.multiple_of
        if source.pattern is not None:
            target.pattern = source.pattern
        if source.validator_info:
            target.validator_info.update(source.validator_info)
        if source.validators:
            target.validators.extend(source.validators)
        if source.min_value is not None:
            target.min_value = source.min_value
        if source.max_value is not None:
            target.max_value = source.max_value

    def _extract_validator_bounds(self, constraints: ConstraintInfo, validator_info: dict[str, Any]) -> None:
        """Extract min/max values from validator info.

        Args:
            constraints: Constraint object to update
            validator_info: Validator metadata dictionary

        """
        for validator_data in validator_info.values():
            if isinstance(validator_data, dict):
                if "min_value" in validator_data:
                    constraints.min_value = validator_data["min_value"]
                if "max_value" in validator_data:
                    constraints.max_value = validator_data["max_value"]

    def extract_annotated_constraints(self, type_annotation: object) -> ConstraintInfo | None:
        """Extract constraints from Annotated type hints.

        Args:
            type_annotation: Type annotation to analyze (may be ForwardRef or string)

        Returns:
            ConstraintInfo if constraints found, None otherwise

        """
        # Handle string annotations (from __future__ import annotations)
        # Caller should use get_type_hints to resolve them with proper context
        if isinstance(type_annotation, str):
            return None

        # Handle ForwardRef by attempting evaluation
        if isinstance(type_annotation, ForwardRef):
            evaluated = self._handle_forward_ref(type_annotation)
            if evaluated is None:
                return None
            type_annotation = evaluated

        origin = get_origin(type_annotation)

        if origin is Annotated:
            args = get_args(type_annotation)
            if len(args) > 1:
                # First arg is the actual type, rest are metadata
                metadata = args[1:]
                constraints = ConstraintInfo()
                has_constraints = False

                # Extract Field constraints from FieldInfo metadata
                for metadata_item in metadata:
                    if isinstance(metadata_item, FieldInfo):
                        field_constraints = self._extract_field_constraints("", metadata_item)
                        if field_constraints:
                            self._merge_field_constraints(constraints, field_constraints)
                            has_constraints = True

                # Extract validator info from AfterValidator and similar
                validator_info = self._extract_validator_metadata(list(metadata))
                if validator_info:
                    constraints.validator_info.update(validator_info)
                    has_constraints = True

                    # Try to extract min/max from validator info
                    self._extract_validator_bounds(constraints, validator_info)

                return constraints if has_constraints else None

        return None
