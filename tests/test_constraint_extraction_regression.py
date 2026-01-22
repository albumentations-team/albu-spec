"""Regression tests for constraint extraction from InitSchema.

This module tests various scenarios where constraints should be extracted
from InitSchema when __init__ has no type annotations.
"""

from __future__ import annotations

from typing import Annotated

from pydantic import AfterValidator, BaseModel, Field

from albu_spec import get_transform_metadata


def check_positive(v: float) -> float:
    """Validator function for positive values."""
    if v <= 0:
        msg = "Must be positive"
        raise ValueError(msg)
    return v


def test_field_constraints_extracted_without_init_annotation():
    """Field constraints (ge, le) should be extracted when __init__ has no annotation."""

    class MockTransform:
        """Mock transform."""

        class InitSchema(BaseModel):
            """Schema with Field constraints."""

            value: Annotated[float, Field(ge=0.0, le=1.0)]

        def __init__(self, value):  # No annotation
            """Init."""
            self.value = value

    metadata = get_transform_metadata(MockTransform)

    assert "value" in metadata.parameters
    param = metadata.parameters["value"]

    # Type extracted from InitSchema
    assert param.type_hint == "float"

    # Constraints extracted from InitSchema
    assert param.constraints is not None
    assert param.constraints.ge == 0.0
    assert param.constraints.le == 1.0


def test_after_validator_extracted_without_init_annotation():
    """AfterValidator should be extracted when __init__ has no annotation."""

    class MockTransform:
        """Mock transform."""

        class InitSchema(BaseModel):
            """Schema with AfterValidator."""

            scale: Annotated[float, AfterValidator(check_positive)]

        def __init__(self, scale):  # No annotation
            """Init."""
            self.scale = scale

    metadata = get_transform_metadata(MockTransform)

    assert "scale" in metadata.parameters
    param = metadata.parameters["scale"]

    # Type extracted
    assert param.type_hint == "float"

    # Validator info extracted
    assert param.constraints is not None
    assert param.constraints.validator_info is not None
    assert "check_positive" in param.constraints.validator_info


def test_combined_field_and_validator_without_init_annotation():
    """Both Field constraints and AfterValidator should be extracted."""

    class MockTransform:
        """Mock transform."""

        class InitSchema(BaseModel):
            """Schema with both."""

            scale: Annotated[float, Field(gt=0), AfterValidator(check_positive)]

        def __init__(self, scale):  # No annotation
            """Init."""
            self.scale = scale

    metadata = get_transform_metadata(MockTransform)

    param = metadata.parameters["scale"]

    # Type extracted
    assert param.type_hint == "float"

    # Both Field constraints and validator info extracted
    assert param.constraints is not None
    assert param.constraints.gt == 0
    assert param.constraints.validator_info is not None


def test_multiple_params_with_mixed_annotations():
    """Test multiple parameters with some having __init__ annotations, some not."""

    class MockTransform:
        """Mock transform."""

        class InitSchema(BaseModel):
            """Schema."""

            scale: Annotated[float, Field(gt=0)]
            value: Annotated[float, Field(ge=0.0, le=1.0)]

        def __init__(self, scale: float, value):  # scale has annotation, value doesn't
            """Init."""
            self.scale = scale
            self.value = value

    metadata = get_transform_metadata(MockTransform)

    # Both parameters should have constraints extracted
    assert metadata.parameters["scale"].constraints is not None
    assert metadata.parameters["scale"].constraints.gt == 0

    assert metadata.parameters["value"].constraints is not None
    assert metadata.parameters["value"].constraints.ge == 0.0
    assert metadata.parameters["value"].constraints.le == 1.0


def test_all_constraint_types_extracted():
    """Test that ge, le, gt, lt constraints are all extracted."""

    class MockTransform:
        """Mock transform."""

        class InitSchema(BaseModel):
            """Schema."""

            param_ge: Annotated[float, Field(ge=0.0)]
            param_le: Annotated[float, Field(le=1.0)]
            param_gt: Annotated[float, Field(gt=0.0)]
            param_lt: Annotated[float, Field(lt=1.0)]

        def __init__(self, param_ge, param_le, param_gt, param_lt):  # No annotations
            """Init."""
            self.param_ge = param_ge
            self.param_le = param_le
            self.param_gt = param_gt
            self.param_lt = param_lt

    metadata = get_transform_metadata(MockTransform)

    # Check ge
    assert metadata.parameters["param_ge"].constraints is not None
    assert metadata.parameters["param_ge"].constraints.ge == 0.0

    # Check le
    assert metadata.parameters["param_le"].constraints is not None
    assert metadata.parameters["param_le"].constraints.le == 1.0

    # Check gt
    assert metadata.parameters["param_gt"].constraints is not None
    assert metadata.parameters["param_gt"].constraints.gt == 0.0

    # Check lt
    assert metadata.parameters["param_lt"].constraints is not None
    assert metadata.parameters["param_lt"].constraints.lt == 1.0
