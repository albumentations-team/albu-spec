"""Test ForwardRef handling in constraint extraction.

This test verifies that constraints are properly extracted from ForwardRef annotations
when using `from __future__ import annotations`.
"""

from __future__ import annotations

from typing import Annotated

from pydantic import AfterValidator, BaseModel, Field

from albu_spec import get_transform_metadata
from albu_spec.schema_parser import SchemaParser


def check_positive(v: float) -> float:
    """Validator for positive values."""
    if v <= 0:
        msg = "Must be positive"
        raise ValueError(msg)
    return v


def test_bug1_forwardref_constraints_extracted():
    """Bug 1: ForwardRef should not prevent constraint extraction.

    When using `from __future__ import annotations`, all type annotations
    become ForwardRef strings. The constraint extraction should handle this.

    NOTE: This test passes because the ForwardRef is from InitSchema, and
    _extract_field_constraints handles it via FieldInfo.metadata.
    The real bug is when extract_annotated_constraints receives a ForwardRef directly.
    """

    class MockTransform:
        """Mock transform with ForwardRef annotations."""

        class InitSchema(BaseModel):
            """Schema with constraints."""

            # With future annotations, this becomes a ForwardRef
            value: Annotated[float, Field(ge=0.0, le=1.0)]

        def __init__(self, value: Annotated[float, Field(ge=0.0, le=1.0)]):
            """Init with Annotated type."""
            self.value = value

    metadata = get_transform_metadata(MockTransform)

    assert "value" in metadata.parameters
    param = metadata.parameters["value"]

    # Type should be extracted
    assert param.type_hint == "float"

    # BUG 1: Constraints should be extracted even though annotation is ForwardRef
    assert param.constraints is not None, "Constraints should be extracted from ForwardRef"
    assert param.constraints.ge == 0.0
    assert param.constraints.le == 1.0


def test_bug1_forwardref_with_validator():
    """Bug 1: ForwardRef with AfterValidator should extract validator info."""

    class MockTransform:
        """Mock transform."""

        class InitSchema(BaseModel):
            """Schema."""

            # ForwardRef with AfterValidator
            scale: Annotated[float, AfterValidator(check_positive)]

        def __init__(self, scale: Annotated[float, AfterValidator(check_positive)]):
            """Init."""
            self.scale = scale

    metadata = get_transform_metadata(MockTransform)

    param = metadata.parameters["scale"]

    # Type extracted
    assert param.type_hint == "float"

    # BUG 1: Validator info should be extracted from ForwardRef
    assert param.constraints is not None
    assert param.constraints.validator_info is not None
    assert "check_positive" in param.constraints.validator_info


def test_bug2_field_constraints_in_annotated():
    """Bug 2: Field constraints should be extracted from Annotated in __init__.

    When a parameter has `Annotated[int, Field(ge=0)]` directly in __init__,
    the Field constraints should be extracted, not just validator info.
    """

    class MockTransform:
        """Mock transform."""

        class InitSchema(BaseModel):
            """Schema without constraints."""

            value: float  # No constraints in InitSchema

        def __init__(self, value: Annotated[float, Field(ge=0.0, le=1.0)]):
            """Init has Field constraints in Annotated."""
            self.value = value

    metadata = get_transform_metadata(MockTransform)

    param = metadata.parameters["value"]

    # Type extracted
    assert param.type_hint == "float"

    # BUG 2: Field constraints from Annotated should be extracted
    assert param.constraints is not None, "Field constraints from Annotated should be extracted"
    assert param.constraints.ge == 0.0, f"Expected ge=0.0, got {param.constraints.ge}"
    assert param.constraints.le == 1.0, f"Expected le=1.0, got {param.constraints.le}"


def test_bug2_combined_field_and_validator_in_annotated():
    """Bug 2: Both Field and validator should be extracted from Annotated."""

    class MockTransform:
        """Mock transform."""

        class InitSchema(BaseModel):
            """Schema."""

            scale: float  # No constraints

        def __init__(self, scale: Annotated[float, Field(gt=0), AfterValidator(check_positive)]):
            """Init with both Field and validator."""
            self.scale = scale

    metadata = get_transform_metadata(MockTransform)

    param = metadata.parameters["scale"]

    # Type extracted
    assert param.type_hint == "float"

    # BUG 2: Both Field constraints and validator should be extracted
    assert param.constraints is not None
    assert param.constraints.gt == 0, "Field constraint (gt) should be extracted"
    assert param.constraints.validator_info is not None, "Validator info should be extracted"
    assert "check_positive" in param.constraints.validator_info


def test_bug1_direct_forwardref_to_extract_annotated_constraints():
    """Bug 1: Direct test of extract_annotated_constraints with ForwardRef.

    This directly tests the bug where extract_annotated_constraints returns None
    when receiving an unevaluated ForwardRef, even if the forward string contains
    Annotated with Field constraints.
    """
    from typing import ForwardRef

    parser = SchemaParser()

    # Create a ForwardRef that represents: Annotated[float, Field(ge=0.0, le=1.0)]
    # This simulates what happens with `from __future__ import annotations`
    forward_ref = ForwardRef("Annotated[float, Field(ge=0.0, le=1.0)]")

    # BUG 1: This currently returns None because ForwardRef is not evaluated
    constraints = parser.extract_annotated_constraints(forward_ref)

    assert constraints is not None, "Should extract constraints from ForwardRef string"
    # Note: Extracting constraints from the string is complex, but at minimum
    # it shouldn't silently return None
