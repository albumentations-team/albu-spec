"""Regression test for constraint extraction bug (without ForwardRef issues)."""

from typing import Annotated

from pydantic import AfterValidator, BaseModel, Field

from albu_spec import get_transform_metadata


def check_positive(v: float) -> float:
    """Validator."""
    if v <= 0:
        msg = "Must be positive"
        raise ValueError(msg)
    return v


def test_bug_constraints_not_extracted_when_init_lacks_annotation():
    """Regression test: constraints should be extracted even when __init__ has no annotation.

    BUG: The constraint extraction logic checked param.annotation instead of raw_type.
    When __init__ has no annotation but InitSchema does, the condition failed and
    constraints from InitSchema were not extracted.

    FIX: Change line 142 from checking param.annotation to checking raw_type.
    """

    class MockTransform:
        """Mock transform."""

        class InitSchema(BaseModel):
            """InitSchema with constraints."""

            scale: Annotated[float, AfterValidator(check_positive)]
            value: Annotated[float, Field(ge=0.0, le=1.0)]

        def __init__(self, scale, value):  # NO type annotations
            """Init without annotations."""
            self.scale = scale
            self.value = value

    metadata = get_transform_metadata(MockTransform)

    # Both parameters should be extracted
    assert "scale" in metadata.parameters
    assert "value" in metadata.parameters

    # Type should be extracted from InitSchema
    assert metadata.parameters["scale"].type_hint == "float"
    assert metadata.parameters["value"].type_hint == "float"

    # Constraints should be extracted from InitSchema (THIS WAS THE BUG)
    assert metadata.parameters["scale"].constraints is not None, "scale constraints should be extracted from InitSchema"
    assert metadata.parameters["scale"].constraints.validator_info, (
        "scale should have validator_info from AfterValidator"
    )

    assert metadata.parameters["value"].constraints is not None, "value constraints should be extracted from InitSchema"
    assert metadata.parameters["value"].constraints.ge == 0.0
    assert metadata.parameters["value"].constraints.le == 1.0


def test_bug_fix_doesnt_break_existing_behavior():
    """Ensure the fix doesn't break the case when __init__ HAS annotations."""

    class MockTransform2:
        """Mock transform."""

        class InitSchema(BaseModel):
            """InitSchema with constraints."""

            scale: Annotated[float, AfterValidator(check_positive)]
            value: Annotated[float, Field(ge=0.0, le=1.0)]

        def __init__(self, scale: float, value: float):  # WITH annotations
            """Init with annotations."""
            self.scale = scale
            self.value = value

    metadata = get_transform_metadata(MockTransform2)

    # Should still work
    assert metadata.parameters["scale"].type_hint == "float"
    assert metadata.parameters["value"].type_hint == "float"

    assert metadata.parameters["scale"].constraints is not None
    assert metadata.parameters["scale"].constraints.validator_info

    assert metadata.parameters["value"].constraints is not None
    assert metadata.parameters["value"].constraints.ge == 0.0
    assert metadata.parameters["value"].constraints.le == 1.0
