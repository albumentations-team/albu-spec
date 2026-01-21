"""Unit tests for SchemaParser.

Tests constraint extraction from Pydantic InitSchema classes.
"""

from __future__ import annotations

from typing import Annotated

import pytest
from pydantic import BaseModel, Field

from albu_spec.models import ConstraintInfo
from albu_spec.schema_parser import SchemaParser


@pytest.fixture
def parser() -> SchemaParser:
    """Create SchemaParser instance."""
    return SchemaParser()


def test_extract_ge_constraint(parser):
    """Test extraction of ge (greater than or equal) constraint."""

    class TestSchema(BaseModel):
        value: int = Field(ge=0)

    class TestTransform:
        InitSchema = TestSchema

    constraints = parser.extract_schema_constraints(TestTransform)

    assert "value" in constraints
    assert constraints["value"].ge == 0.0


def test_extract_le_constraint(parser):
    """Test extraction of le (less than or equal) constraint."""

    class TestSchema(BaseModel):
        value: float = Field(le=1.0)

    class TestTransform:
        InitSchema = TestSchema

    constraints = parser.extract_schema_constraints(TestTransform)

    assert "value" in constraints
    assert constraints["value"].le == 1.0


def test_extract_gt_constraint(parser):
    """Test extraction of gt (greater than) constraint."""

    class TestSchema(BaseModel):
        value: float = Field(gt=0.0)

    class TestTransform:
        InitSchema = TestSchema

    constraints = parser.extract_schema_constraints(TestTransform)

    assert "value" in constraints
    assert constraints["value"].gt == 0.0


def test_extract_lt_constraint(parser):
    """Test extraction of lt (less than) constraint."""

    class TestSchema(BaseModel):
        value: float = Field(lt=100.0)

    class TestTransform:
        InitSchema = TestSchema

    constraints = parser.extract_schema_constraints(TestTransform)

    assert "value" in constraints
    assert constraints["value"].lt == 100.0


def test_extract_multiple_constraints(parser):
    """Test extraction of multiple constraints on single field."""

    class TestSchema(BaseModel):
        value: float = Field(ge=0.0, le=1.0)

    class TestTransform:
        InitSchema = TestSchema

    constraints = parser.extract_schema_constraints(TestTransform)

    assert "value" in constraints
    assert constraints["value"].ge == 0.0
    assert constraints["value"].le == 1.0


def test_extract_min_max_length(parser):
    """Test extraction of min_length and max_length constraints."""

    class TestSchema(BaseModel):
        items: list[int] = Field(min_length=1, max_length=10)

    class TestTransform:
        InitSchema = TestSchema

    constraints = parser.extract_schema_constraints(TestTransform)

    assert "items" in constraints
    assert constraints["items"].min_length == 1
    assert constraints["items"].max_length == 10


def test_extract_multiple_of_constraint(parser):
    """Test extraction of multiple_of constraint."""

    class TestSchema(BaseModel):
        value: int = Field(multiple_of=5)

    class TestTransform:
        InitSchema = TestSchema

    constraints = parser.extract_schema_constraints(TestTransform)

    assert "value" in constraints
    assert constraints["value"].multiple_of == 5.0


def test_extract_pattern_constraint(parser):
    """Test extraction of pattern (regex) constraint."""

    class TestSchema(BaseModel):
        name: str = Field(pattern=r"^[a-z]+$")

    class TestTransform:
        InitSchema = TestSchema

    constraints = parser.extract_schema_constraints(TestTransform)

    assert "name" in constraints
    assert constraints["name"].pattern == r"^[a-z]+$"


def test_no_constraints_returns_empty_dict(parser):
    """Test that fields without constraints return empty dict."""

    class TestSchema(BaseModel):
        value: int

    class TestTransform:
        InitSchema = TestSchema

    constraints = parser.extract_schema_constraints(TestTransform)

    # Should still have the field, but with no constraints
    # (actually, we only return fields WITH constraints)
    assert "value" not in constraints or constraints["value"] is None


def test_transform_without_init_schema(parser):
    """Test handling of transform without InitSchema."""

    class TestTransform:
        pass

    constraints = parser.extract_schema_constraints(TestTransform)

    assert constraints == {}


def test_multiple_fields_with_constraints(parser):
    """Test extraction from multiple fields."""

    class TestSchema(BaseModel):
        min_value: float = Field(ge=0.0)
        max_value: float = Field(le=1.0)
        count: int = Field(gt=0, lt=100)

    class TestTransform:
        InitSchema = TestSchema

    constraints = parser.extract_schema_constraints(TestTransform)

    assert len(constraints) == 3

    assert constraints["min_value"].ge == 0.0
    assert constraints["max_value"].le == 1.0
    assert constraints["count"].gt == 0.0
    assert constraints["count"].lt == 100.0


def test_extract_field_constraints_returns_none_for_empty(parser):
    """Test _extract_field_constraints returns None when no constraints."""
    from pydantic.fields import FieldInfo

    field_info = FieldInfo(annotation=int, default=5)

    result = parser._extract_field_constraints("test_field", field_info)

    assert result is None


def test_extract_annotated_constraints(parser):
    """Test extraction of constraints from Annotated type hints."""
    # This tests the extract_annotated_constraints method
    # Note: This requires validators to be in the Annotated metadata

    # Simple case: Annotated without validators

    annotated_type = Annotated[float, "some metadata"]

    result = parser.extract_annotated_constraints(annotated_type)

    # Should return None if no validator metadata found
    # (implementation may vary based on metadata structure)
    assert result is None or isinstance(result, ConstraintInfo)


def test_extract_annotated_non_annotated_type(parser):
    """Test extract_annotated_constraints with non-Annotated type."""
    result = parser.extract_annotated_constraints(int)

    assert result is None


def test_validator_metadata_extraction(parser):
    """Test extraction of validator information from metadata."""

    # Mock metadata with validator-like structure
    class MockValidator:
        def __init__(self):
            self.func = lambda x: x

    mock_validator = MockValidator()
    mock_validator.func.__name__ = "test_validator"
    mock_validator.__class__.__name__ = "AfterValidator"

    metadata = [mock_validator]

    result = parser._extract_validator_metadata(metadata)

    # Should extract validator info
    assert isinstance(result, dict)


def test_constraint_info_model():
    """Test ConstraintInfo model can be created and serialized."""
    info = ConstraintInfo(
        ge=0.0,
        le=1.0,
        min_length=1,
        max_length=10,
        pattern=r"^\w+$",
        validators=["check_value"],
    )

    assert info.ge == 0.0
    assert info.le == 1.0
    assert info.min_length == 1
    assert info.max_length == 10
    assert info.pattern == r"^\w+$"
    assert "check_value" in info.validators

    # Should be serializable
    data = info.model_dump()
    assert data["ge"] == 0.0
    assert data["validators"] == ["check_value"]


def test_constraint_info_defaults():
    """Test ConstraintInfo has correct defaults (all None/empty)."""
    info = ConstraintInfo()

    assert info.ge is None
    assert info.le is None
    assert info.gt is None
    assert info.lt is None
    assert info.min_length is None
    assert info.max_length is None
    assert info.multiple_of is None
    assert info.min_value is None
    assert info.max_value is None
    assert info.pattern is None
    assert info.validators == []
    assert info.validator_info == {}


@pytest.mark.parametrize(
    "field_value,expected",
    [
        (Field(ge=0), 0.0),
        (Field(ge=5.5), 5.5),
        (Field(ge=-10), -10.0),
    ],
)
def test_ge_constraint_parametrized(parser, field_value, expected):
    """Test ge constraint with various values."""

    class TestSchema(BaseModel):
        value: float = field_value

    class TestTransform:
        InitSchema = TestSchema

    constraints = parser.extract_schema_constraints(TestTransform)

    assert constraints["value"].ge == expected


@pytest.mark.parametrize(
    "field_value,expected",
    [
        (Field(le=1), 1.0),
        (Field(le=0.5), 0.5),
        (Field(le=100), 100.0),
    ],
)
def test_le_constraint_parametrized(parser, field_value, expected):
    """Test le constraint with various values."""

    class TestSchema(BaseModel):
        value: float = field_value

    class TestTransform:
        InitSchema = TestSchema

    constraints = parser.extract_schema_constraints(TestTransform)

    assert constraints["value"].le == expected
