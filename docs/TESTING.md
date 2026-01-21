# Testing Guide for albu-spec

## Overview

Comprehensive pytest-based test framework validating metadata extraction consistency across different methods for AlbumentationsX transforms.

## Test Structure

```
tests/
├── __init__.py                      # Package marker
├── conftest.py                      # Shared fixtures and utilities
├── test_metadata_consistency.py     # Cross-method validation tests
├── test_property_based.py           # Universal invariant tests
├── test_schema_parser.py            # SchemaParser unit tests
└── test_report_generator.py         # AlbumentationsX issue reporting
```

## Running Tests

```bash
# Run all tests with coverage
pytest

# Run specific test file
pytest tests/test_metadata_consistency.py

# Run tests for specific transform
pytest -k "HorizontalFlip"

# Run with verbose output
pytest -v

# Generate coverage report
pytest --cov=albu_spec --cov-report=html
```

## Test Categories

### 1. Metadata Consistency Tests (`test_metadata_consistency.py`)

Tests that verify metadata extracted from different sources matches:

- **test_init_schema_params_exist_in_init**: InitSchema parameters must exist in `__init__`
- **test_init_params_have_metadata**: All `__init__` parameters should be extracted
- **test_type_hints_consistency**: Types from InitSchema vs `__init__` match
- **test_constraints_extracted_correctly**: Field constraints properly extracted
- **test_affine_specific_metadata**: Affine transform specific validation
- **test_horizontalflip_specific_metadata**: HorizontalFlip specific validation

### 2. Property-Based Tests (`test_property_based.py`)

Universal invariants that MUST hold for ALL transforms:

- **test_property_all_init_schema_params_in_init**: InitSchema ⊂ __init__ params
- **test_property_type_hints_are_non_empty**: No empty type hints
- **test_property_constraint_ranges_are_valid**: Constraints are logically valid
- **test_property_transform_type_is_valid**: Valid transform type category
- **test_property_dual_transforms_have_targets**: Dual transforms have targets
- **test_property_has_docstring**: All transforms documented
- **test_property_metadata_is_deterministic**: Extraction is repeatable
- **test_property_default_values_satisfy_constraints**: Defaults satisfy constraints

### 3. Schema Parser Tests (`test_schema_parser.py`)

Unit tests for Pydantic InitSchema constraint extraction:

- **test_extract_ge_constraint**: Greater than or equal extraction
- **test_extract_le_constraint**: Less than or equal extraction
- **test_extract_gt_constraint**: Greater than extraction
- **test_extract_lt_constraint**: Less than extraction
- **test_extract_multiple_constraints**: Multiple constraints on one field
- **test_extract_min_max_length**: Length constraints for sequences
- **test_extract_multiple_of_constraint**: Multiple-of constraint
- **test_extract_pattern_constraint**: Regex pattern extraction
- Plus edge cases and error handling

### 4. Report Generator (`test_report_generator.py`)

Generates markdown reports of AlbumentationsX inconsistencies:

- Collects xfail tests marked as `albumentationsx_bug`
- Creates `ALBUMENTATIONSX_ISSUES.md` with detailed issue descriptions
- Provides actionable suggestions for fixes

## Test Fixtures (conftest.py)

### Fixtures

- **extractor**: TransformMetadataExtractor instance
- **schema_parser**: SchemaParser instance
- **docstring_parser**: DocstringParser instance
- **transform_classes**: HorizontalFlip, Affine, ColorJitter test set
- **all_transform_classes**: All available transforms
- **snapshot_dir**: Temporary directory for snapshots
- **xfail_tracker**: Track xfail information

### Utilities

- **normalize_type_string()**: Normalize type hints for comparison
- **assert_types_match()**: Assert types match after normalization
- **get_init_params()**: Extract __init__ parameter names
- **get_init_schema_params()**: Extract InitSchema parameter names

## xfail Markers for Issue Tracking

Tests use pytest xfail to distinguish bugs:

```python
# AlbumentationsX bug
pytest.xfail("albumentationsx_bug: Affine.scale type mismatch")

# Parser bug
pytest.xfail("parser_bug: SchemaParser doesn't handle nested Annotated")
```

**Benefits**:
- CI stays green
- Issues documented in code
- Can generate reports for filing issues
- Clear responsibility (albu-spec vs AlbumentationsX)

## Tested Transforms

Primary test transforms:

1. **HorizontalFlip**: Simple dual transform, minimal parameters
2. **Affine**: Complex dual transform, many parameters, nested types
3. **ColorJitter**: Image-only transform with range constraints

Additional property tests cover: Rotate, Blur, Normalize

## Coverage Goals

- schema_parser.py: 100% line coverage
- docstring_parser.py: N/A (external package)
- extractor.py: 95%+ branch coverage
- models.py: 100% (Pydantic models)

## Common Test Patterns

### Parametrized Testing

```python
@pytest.mark.parametrize("transform_class", [
    A.HorizontalFlip,
    A.Affine,
    A.ColorJitter,
])
def test_something(transform_class):
    metadata = get_transform_metadata(transform_class)
    assert metadata.name == transform_class.__name__
```

### Type Normalization

```python
from conftest import normalize_type_string

# "int | float" vs "float | int" both => {"int", "float"}
assert normalize_type_string("int | float") == normalize_type_string("float | int")
```

### Constraint Validation

```python
if param.constraints:
    if param.constraints.ge is not None and param.constraints.le is not None:
        assert param.constraints.ge <= param.constraints.le
```

## Adding New Tests

### For a New Transform

1. Add to `transform_classes` fixture in conftest.py
2. Property-based tests automatically apply
3. Add specific test if needed in `test_metadata_consistency.py`

### For a New Property

1. Add test function to `test_property_based.py`
2. Parametrize with all transforms
3. Use descriptive assertion messages

### For New Parser Logic

1. Add unit test to `test_schema_parser.py`
2. Test both happy path and edge cases
3. Verify error handling

## CI Integration

Tests are designed for CI/CD:

```yaml
# Example GitHub Actions
- name: Run tests
  run: |
    pip install -e ".[dev]"
    pytest --cov=albu_spec --cov-report=xml

- name: Upload coverage
  uses: codecov/codecov-action@v3
```

## Troubleshooting

### Import Errors

AlbumentationsX is installed via `pip install albumentationsx` but imports as:

```python
import albumentations as A  # Correct
# NOT: import albumentationsx
```

### Skipped Tests

If transforms are missing:

```
pytest -v  # See which tests are skipped
```

ColorJitter may not be available in all AlbumentationsX versions.

### xfail Tests

To run xfail tests and see actual failures:

```bash
pytest --runxfail
```

## Documentation

- **CLAUDE.md**: Comprehensive AI assistant guide with testing philosophy
- **README.md**: User-facing documentation
- **This file**: Testing-specific guide

## References

- Pytest: https://docs.pytest.org/
- AlbumentationsX: https://github.com/albumentations-team/AlbumentationsX
- Pydantic: https://docs.pydantic.dev/
