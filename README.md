# albu-spec

Extract comprehensive metadata from
[AlbumentationsX](https://github.com/albumentations-team/AlbumentationsX)
transforms including parameter names, types, constraints, and docstrings.

## Features

- **Parameter Extraction**: Extract parameter names, types, and default
values from `__init__` signatures
- **Deep Constraint Analysis**: Parse Pydantic `Field` constraints
(ge, le, gt, lt, etc.)
- **Validator Introspection**: Extract information from `AfterValidator`
bounds and custom validators
- **Docstring Parsing**: Extract parameter descriptions from Google-style docstrings
- **Complete Metadata**: Get transform type, supported targets, and module information
- **Type Safety**: All data returned as typed Pydantic models

## Installation

```bash
pip install albu-spec
```

**Note**: This package requires `albumentationsx` to be installed separately,
as it's designed to introspect an existing AlbumentationsX installation:

```bash
pip install albumentationsx
```

## Quick Start

### Extract Metadata for a Single Transform

```python
import albumentations as A
from albu_spec import get_transform_metadata

# Get metadata for Blur transform
metadata = get_transform_metadata(A.Blur)

print(f"Transform: {metadata.name}")
print(f"Type: {metadata.transform_type}")
print(f"Module: {metadata.module}")
print(f"Has InitSchema: {metadata.has_init_schema}")
print(f"\nParameters:")

for param_name, param_info in metadata.parameters.items():
    print(f"  {param_name}:")
    print(f"    Type: {param_info.type_hint}")
    print(f"    Default: {param_info.default}")
    if param_info.description:
        print(f"    Description: {param_info.description[:100]}...")
    if param_info.constraints:
        print(f"    Constraints: {param_info.constraints}")
```

### Extract All Transforms

```python
from albu_spec import get_all_transforms_metadata

# Get all transforms grouped by type
collection = get_all_transforms_metadata()

print(f"Total transforms: {collection.total_count}")
print(f"Image-only transforms: {len(collection.image_only)}")
print(f"Dual transforms: {len(collection.dual)}")
print(f"3D transforms: {len(collection.transforms_3d)}")

# Iterate through all transforms
for transform in collection.get_all():
    print(f"{transform.name} ({transform.transform_type})")
```

## Detailed Examples

### Examining Parameter Constraints

```python
from albu_spec import get_transform_metadata
import albumentations as A

# Get GlassBlur metadata
metadata = get_transform_metadata(A.GlassBlur)

# Check sigma parameter
sigma_param = metadata.parameters['sigma']
print(f"Parameter: {sigma_param.name}")
print(f"Type: {sigma_param.type_hint}")
print(f"Default: {sigma_param.default}")

if sigma_param.constraints:
    print(f"Constraints:")
    if sigma_param.constraints.ge is not None:
        print(f"  >= {sigma_param.constraints.ge}")
    if sigma_param.constraints.le is not None:
        print(f"  <= {sigma_param.constraints.le}")
```

### Accessing Validator Information

```python
from albu_spec import get_transform_metadata
import albumentations as A

# Get MotionBlur metadata
metadata = get_transform_metadata(A.MotionBlur)

# Check angle_range parameter
angle_param = metadata.parameters['angle_range']

if angle_param.constraints and angle_param.constraints.validator_info:
    print("Validator information:")
    for validator_name, validator_data in angle_param.constraints.validator_info.items():
        print(f"  {validator_name}: {validator_data}")
```

### Export to JSON

```python
from albu_spec import get_all_transforms_metadata
import json

# Get all transforms
collection = get_all_transforms_metadata()

# Convert to dict and export
data = collection.model_dump()

with open("transforms_metadata.json", "w") as f:
    json.dump(data, f, indent=2)

print("Metadata exported to transforms_metadata.json")
```

### Filter Transforms by Criteria

```python
from albu_spec import get_all_transforms_metadata

collection = get_all_transforms_metadata()

# Find all transforms with InitSchema
transforms_with_schema = [
    t for t in collection.get_all()
    if t.has_init_schema
]

print(f"Transforms with InitSchema: {len(transforms_with_schema)}")

# Find all transforms that support bboxes
transforms_with_bboxes = [
    t for t in collection.get_all()
    if "bboxes" in t.targets
]

print(f"Transforms supporting bboxes: {len(transforms_with_bboxes)}")
```

## Data Models

### TransformMetadata

Complete metadata for a transform:

```python
class TransformMetadata(BaseModel):
    name: str  # Transform class name
    module: str  # Module path
    transform_type: Literal["image_only", "dual", "transforms_3d", "unknown"]
    targets: list[str]  # Supported targets
    parameters: dict[str, ParameterMetadata]  # Parameter metadata
    docstring: str | None  # Complete docstring
    docstring_short: str | None  # Short description
    has_init_schema: bool  # Whether InitSchema exists
```

### ParameterMetadata

Metadata for a single parameter:

```python
class ParameterMetadata(BaseModel):
    name: str  # Parameter name
    type_hint: str | list[str]  # Type annotation
    default: Any  # Default value
    description: str | None  # Description from docstring
    constraints: ConstraintInfo | None  # Pydantic constraints
```

### ConstraintInfo

Constraint information from Pydantic:

```python
class ConstraintInfo(BaseModel):
    ge: float | None  # Greater than or equal to
    le: float | None  # Less than or equal to
    gt: float | None  # Greater than
    lt: float | None  # Less than
    min_length: int | None  # Minimum length
    max_length: int | None  # Maximum length
    multiple_of: float | None  # Must be multiple of
    min_value: float | None  # Min value (from validators)
    max_value: float | None  # Max value (from validators)
    pattern: str | None  # Regex pattern
    validators: list[str]  # Validator function names
    validator_info: dict[str, Any]  # Additional validator info
```

### TransformCollection

Collection of transforms grouped by type:

```python
class TransformCollection(BaseModel):
    image_only: list[TransformMetadata]
    dual: list[TransformMetadata]
    transforms_3d: list[TransformMetadata]
    unknown: list[TransformMetadata]

    @property
    def total_count(self) -> int:
        """Total number of transforms"""

    def get_all(self) -> list[TransformMetadata]:
        """Get all transforms as a flat list"""
```

## Use Cases

### Documentation Generation

Generate comprehensive API documentation for Albumentations transforms:

```python
from albu_spec import get_all_transforms_metadata

collection = get_all_transforms_metadata()

for transform in collection.image_only:
    print(f"## {transform.name}\n")
    print(f"{transform.docstring_short}\n")
    print("### Parameters\n")

    for param_name, param in transform.parameters.items():
        print(f"- **{param_name}** (`{param.type_hint}`)")
        if param.default is not None:
            print(f"  - Default: `{param.default}`")
        if param.description:
            print(f"  - {param.description}")
        print()
```

### UI Generation

Build dynamic UIs for transform configuration:

```python
from albu_spec import get_transform_metadata
import albumentations as A

metadata = get_transform_metadata(A.Blur)

# Generate UI controls based on parameter types and constraints
for param_name, param in metadata.parameters.items():
    if param.type_hint == "int" and param.constraints:
        # Create slider with min/max from constraints
        min_val = param.constraints.ge or param.constraints.gt or 0
        max_val = param.constraints.le or param.constraints.lt or 100
        print(f"Slider for {param_name}: range({min_val}, {max_val})")
    elif isinstance(param.type_hint, list):
        # Create dropdown for Literal types
        print(f"Dropdown for {param_name}: options={param.type_hint}")
```

### Validation Testing

Test transform initialization with various parameter values:

```python
from albu_spec import get_transform_metadata
import albumentations as A

metadata = get_transform_metadata(A.GlassBlur)

# Test edge cases based on constraints
for param_name, param in metadata.parameters.items():
    if param.constraints:
        print(f"Testing {param_name}:")

        if param.constraints.ge is not None:
            print(f"  Min value: {param.constraints.ge}")
            # Test with min value

        if param.constraints.le is not None:
            print(f"  Max value: {param.constraints.le}")
            # Test with max value
```

## Requirements

- Python >= 3.10
- pydantic >= 2.0
- google-docstring-parser >= 0.0.8
- typing-extensions >= 4.0
- albumentationsx (installed separately, imports as `albumentations`)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

MIT License

## Related Projects

- [AlbumentationsX](https://github.com/albumentations-team/AlbumentationsX) -
Fast image augmentation library

## Credits

Developed by Vladimir Iglovikov and the Albumentations team.
