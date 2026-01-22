"""Test for bug: constraints not extracted when __init__ lacks annotation but InitSchema has Annotated type.

Bug Description:
When a parameter has no type annotation in __init__ but InitSchema has an Annotated type
with constraints, the constraint extraction logic checks param.annotation (which is empty)
instead of raw_type (which has the InitSchema annotation), causing constraints to be missed.

NOTE: This module does NOT use `from __future__ import annotations` because that would
prevent Pydantic from properly parsing Annotated metadata when local functions are used.
"""

from typing import Annotated

from pydantic import AfterValidator, BaseModel, Field

from albu_spec import get_transform_metadata


def test_constraints_extracted_when_init_has_no_annotation():
    """Test that constraints are extracted from InitSchema even when __init__ has no annotation.

    This is a regression test for the bug where:
    1. __init__ has no type annotation (param.annotation is inspect.Parameter.empty)
    2. InitSchema has Annotated type with constraints
    3. The condition `param.annotation is not inspect.Parameter.empty` on line 142 fails
    4. So constraints from InitSchema annotation are never extracted
    """

    # Create a mock transform that reproduces the bug scenario
    class MockTransform:
        """Mock transform to test constraint extraction."""

        class InitSchema(BaseModel):
            """InitSchema with Annotated type and constraints."""

            # Parameter has Annotated with validators in InitSchema
            value: Annotated[float, Field(ge=0.0, le=1.0)]

        def __init__(self, value):  # No type annotation in __init__
            """Initialize without type annotation."""
            self.value = value

    # Extract metadata
    metadata = get_transform_metadata(MockTransform)

    # Verify parameter exists
    assert "value" in metadata.parameters, "Parameter 'value' should be extracted"

    param = metadata.parameters["value"]

    # Type should be extracted from InitSchema (this already works)
    assert param.type_hint == "float", f"Expected type 'float', got '{param.type_hint}'"

    # Constraints should also be extracted from InitSchema (BUG: this fails)
    assert param.constraints is not None, "Constraints should be extracted from InitSchema"
    assert param.constraints.ge == 0.0, f"Expected ge=0.0, got {param.constraints.ge}"
    assert param.constraints.le == 1.0, f"Expected le=1.0, got {param.constraints.le}"


def test_constraints_extracted_with_annotated_in_initschema():
    """Test extraction when InitSchema has Annotated with custom validators."""

    def check_positive(v: float) -> float:
        if v <= 0:
            msg = "Must be positive"
            raise ValueError(msg)
        return v

    class MockTransformWithValidator:
        """Mock transform with validator in InitSchema."""

        class InitSchema(BaseModel):
            """InitSchema with Annotated validator."""

            # AfterValidator in Annotated
            scale: Annotated[float, Field(gt=0), AfterValidator(check_positive)]

        def __init__(self, scale):  # No annotation
            """Initialize."""
            self.scale = scale

    metadata = get_transform_metadata(MockTransformWithValidator)

    assert "scale" in metadata.parameters
    param = metadata.parameters["scale"]

    # Type extracted from InitSchema
    assert param.type_hint == "float"

    # Constraints should be extracted (BUG: validator_info might be missing)
    assert param.constraints is not None
    assert param.constraints.gt == 0, f"Expected gt=0, got {param.constraints.gt}"


def test_constraints_extracted_when_init_has_annotation_still_works():
    """Verify that the fix doesn't break the case when __init__ HAS annotation.

    This is a sanity check to ensure we don't regress existing functionality.
    """

    class MockTransformWithInitAnnotation:
        """Mock transform with annotation in both places."""

        class InitSchema(BaseModel):
            """InitSchema with constraints."""

            value: Annotated[float, Field(ge=0.0, le=1.0)]

        def __init__(self, value: float):  # Has annotation
            """Initialize with type annotation."""
            self.value = value

    metadata = get_transform_metadata(MockTransformWithInitAnnotation)

    assert "value" in metadata.parameters
    param = metadata.parameters["value"]

    # Should still work
    assert param.type_hint == "float"
    assert param.constraints is not None
    assert param.constraints.ge == 0.0
    assert param.constraints.le == 1.0
