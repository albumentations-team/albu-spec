"""Test for Bug 1 fix: field_validators correctly maps to field names."""

from pydantic import BaseModel, field_validator

from albu_spec.schema_parser import SchemaParser


def test_field_validator_maps_to_correct_field_names():
    """Test that validators are stored under field names, not validator method names.

    This is a regression test for Bug 1 where decorators.field_validators.items()
    was incorrectly assumed to return (field_name, decorator) pairs when it actually
    returns (validator_method_name, decorator) pairs. The actual field names are in
    decorator.info.fields.
    """

    class TestSchema(BaseModel):
        scale: float
        rotate: int

        @field_validator("scale")
        @classmethod
        def validate_scale(cls, v):
            """Validator for scale field."""
            return v

        @field_validator("rotate")
        @classmethod
        def validate_rotate(cls, v):
            """Validator for rotate field."""
            return v

    class TestTransform:
        InitSchema = TestSchema

    parser = SchemaParser()
    constraints = parser.extract_schema_constraints(TestTransform)

    # Should have constraints for 'scale' and 'rotate' (field names)
    assert "scale" in constraints, "Missing constraints for 'scale' field"
    assert "rotate" in constraints, "Missing constraints for 'rotate' field"

    # Should NOT have constraints for validator method names
    assert "validate_scale" not in constraints, "Bug: validators stored under method name instead of field name"
    assert "validate_rotate" not in constraints, "Bug: validators stored under method name instead of field name"

    # Validators should be properly associated with their fields
    assert "validate_scale" in constraints["scale"].validators, (
        "Validator 'validate_scale' should be associated with 'scale' field"
    )
    assert "validate_rotate" in constraints["rotate"].validators, (
        "Validator 'validate_rotate' should be associated with 'rotate' field"
    )


def test_field_validator_with_multiple_fields():
    """Test that a single validator applied to multiple fields is correctly mapped."""

    class TestSchema(BaseModel):
        x: float
        y: float
        z: float

        @field_validator("x", "y", "z")
        @classmethod
        def validate_coords(cls, v):
            """Validator for all coordinate fields."""
            return v

    class TestTransform:
        InitSchema = TestSchema

    parser = SchemaParser()
    constraints = parser.extract_schema_constraints(TestTransform)

    # All three fields should have the validator
    for field in ["x", "y", "z"]:
        assert field in constraints, f"Missing constraints for '{field}' field"
        assert "validate_coords" in constraints[field].validators, (
            f"Validator 'validate_coords' should be associated with '{field}' field"
        )

    # Should NOT have constraint under method name
    assert "validate_coords" not in constraints, "Bug: validator stored under method name instead of field names"
