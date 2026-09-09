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
- **Structured Docstring Parsing**: Parse Google-style docstrings into structured sections (args, examples, notes, warnings, references, etc.)
- **Complete Metadata**: Get transform type, supported targets, and module information
- **BBox Type Support**: Extract supported bounding box types (HBB, OBB) for dual transforms
- **Type Safety**: All data returned as typed Pydantic models
- **JSON Serializable**: Export all metadata as JSON for APIs and databases

## Installation

AlbumentationsX requires a PyTorch build selected for the target machine. For Linux CPU-only environments:

```bash
pip install "torch>=2.13.0" --index-url https://download.pytorch.org/whl/cpu
pip install albu-spec
```

For CUDA or macOS, install the matching PyTorch build first, then run `pip install albu-spec`. The `albu-spec`
installation includes AlbumentationsX and headless OpenCV.

## Quick Start

### Extract Metadata for a Single Transform

```python
import albumentations as A
from albu_spec import get_transform_metadata

# Get metadata for RandomCrop transform
metadata = get_transform_metadata(A.RandomCrop)

print(f"Transform: {metadata.name}")
print(f"Type: {metadata.transform_type}")
print(f"Module: {metadata.module}")
print(f"Targets: {metadata.targets}")
print(f"Has InitSchema: {metadata.has_init_schema}")
print(f"Supported BBox Types: {metadata.supported_bbox_types}")
```

**Output:**

```
Transform: RandomCrop
Type: dual
Module: albumentations.augmentations.crops.transforms
Targets: ['image', 'mask', 'bboxes', 'keypoints', 'volume', 'mask3d']
Has InitSchema: True
Supported BBox Types: ['hbb', 'obb']
```

**Full metadata as JSON (truncated for brevity):**

```json
{
  "name": "RandomCrop",
  "module": "albumentations.augmentations.crops.transforms",
  "transform_type": "dual",
  "targets": ["image", "mask", "bboxes", "keypoints", "volume", "mask3d"],
  "parameters": {
    "height": {
      "name": "height",
      "type_hint": "int",
      "default": null,
      "description": "height of the crop.",
      "constraints": {
        "ge": 1.0,
        "le": null
      }
    },
    "pad_position": {
      "name": "pad_position",
      "type_hint": ["center", "top_left", "top_right", "bottom_left", "bottom_right", "random"],
      "default": "center",
      "description": "Position of padding. Default: 'center'.",
      "constraints": null
    },
    "border_mode": {
      "name": "border_mode",
      "type_hint": [0, 1, 2, 3, 4],
      "default": 0,
      "description": "OpenCV border mode used for padding. Default: cv2.BORDER_CONSTANT.",
      "constraints": null
    },
    "fill": {
      "name": "fill",
      "type_hint": "tuple[float, ...] | float",
      "default": 0.0,
      "description": "Padding value for images if border_mode is cv2.BORDER_CONSTANT. Default: 0.",
      "constraints": null
    },
    "p": {
      "name": "p",
      "type_hint": "float",
      "default": 1.0,
      "description": "Probability of applying the transform. Default: 1.0.",
      "constraints": {
        "ge": 0.0,
        "le": 1.0
      }
    }
  },
  "docstring_short": "Crop a random part of the input.",
  "has_init_schema": true,
  "supported_bbox_types": ["hbb", "obb"]
}
```

**Note:** `pad_position` and `border_mode` return **lists** (perfect for dropdowns), while `fill` returns a **string** (union type).

### Inspect Individual Parameters

```python
# Check parameter details
for param_name, param_info in metadata.parameters.items():
    print(f"{param_name}:")
    print(f"  Type: {param_info.type_hint}")
    print(f"  Default: {param_info.default}")
    if param_info.constraints:
        print(f"  Constraints: {param_info.constraints}")
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

### Check Bounding Box Type Support

```python
from albu_spec import get_transform_metadata
import albumentations as A

# Check which bbox types a transform supports
transforms_to_check = [A.Affine, A.Rotate, A.CenterCrop, A.ColorJitter]

for transform_class in transforms_to_check:
    metadata = get_transform_metadata(transform_class)
    if metadata.supported_bbox_types:
        print(f"{metadata.name}: {metadata.supported_bbox_types}")
    else:
        print(f"{metadata.name}: No bbox support (not a dual transform)")
```

**Output:**

```
Affine: ['hbb', 'obb']
Rotate: ['hbb', 'obb']
CenterCrop: ['hbb', 'obb']
ColorJitter: No bbox support (not a dual transform)
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

### Working with Structured Docstrings

```python
from albu_spec import get_transform_metadata
import albumentations as A

# Get metadata with parsed docstring
metadata = get_transform_metadata(A.Blur)

if metadata.docstring_parsed:
    parsed = metadata.docstring_parsed

    # Short description for preview cards
    print(f"Description: {parsed.short_description}")

    # Parameters with types and descriptions
    print("\nParameters:")
    for arg in parsed.args:
        print(f"  {arg.name} ({arg.type}): {arg.description}")

    # Code examples
    if parsed.examples:
        print(f"\nFound {len(parsed.examples)} example(s)")
        print("First example:")
        print(parsed.examples[0][:200] + "...")

    # Additional sections
    if parsed.notes:
        print(f"\nNotes: {parsed.notes}")

    if parsed.warnings:
        print(f"\nWarnings: {parsed.warnings}")

    if parsed.references:
        print(f"\nReferences: {parsed.references}")

    # Extra sections (Image types, Targets, Mathematical Formulation, etc.)
    if parsed.extra_sections:
        print("\nExtra sections:")
        for section_name, section_content in parsed.extra_sections.items():
            print(f"  {section_name}: {section_content[:100]}...")
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

# Find transforms that support OBB (oriented bounding boxes)
transforms_with_obb = [
    t for t in collection.dual
    if t.supported_bbox_types and "obb" in t.supported_bbox_types
]

print(f"Transforms supporting OBB: {len(transforms_with_obb)}")
for t in transforms_with_obb[:5]:
    print(f"  - {t.name}: {t.supported_bbox_types}")
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
    docstring: str | None  # Complete docstring (raw)
    docstring_short: str | None  # Short description
    docstring_parsed: ParsedDocstring | None  # Structured parsed docstring
    has_init_schema: bool  # Whether InitSchema exists
    supported_bbox_types: list[str] | None  # Supported bbox types (hbb, obb) for dual transforms
```

### ParameterMetadata

Metadata for a single parameter:

```python
class ParameterMetadata(BaseModel):
    name: str  # Parameter name
    type_hint: str | list[Any]  # Type annotation string OR list of Literal values
    default: Any  # Default value
    description: str | None  # Description from docstring
    constraints: ConstraintInfo | None  # Pydantic constraints
```

**Notes on `type_hint`:**
- **String format**: Regular types like `"int"`, `"float"`, or unions like `"tuple[int, int] | int"`
- **List format**: Literal types return actual values, e.g., `["image", "mask", None]` or `[0, 1, 2, 3, 4]`
  - Perfect for rendering dropdowns in UIs
  - Preserves original types (int, str, None, etc.)
  - When a Union contains a Literal, all possible values are returned as a list including None

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

### ParsedDocstring

Structured parsed docstring with all sections:

```python
class ParsedDocstring(BaseModel):
    short_description: str | None  # First paragraph
    long_description: str | None  # Extended description
    args: list[DocstringArg]  # Parsed arguments
    returns: DocstringReturn | None  # Return value info
    raises: list[DocstringRaises]  # Exceptions
    yields: DocstringReturn | None  # Yield info (generators)
    examples: list[str]  # Code examples
    notes: str | None  # Additional notes
    warnings: str | None  # User warnings
    see_also: str | None  # Related items
    references: str | None  # Citations/links
    attributes: list[DocstringArg]  # Class attributes
    extra_sections: dict[str, Any]  # All other sections (Image types, Targets, etc.)
```

**Note**: `extra_sections` captures ALL docstring sections not explicitly handled above.
AlbumentationsX transforms use 90+ custom section names like "Image types", "Targets",
"Mathematical Formulation", "Number of channels", etc. These are automatically captured
in `extra_sections` dict, making the parser future-proof for any new sections.

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

    if transform.docstring_parsed:
        # Use structured docstring
        parsed = transform.docstring_parsed
        print(f"{parsed.short_description}\n")

        print("### Parameters\n")
        for arg in parsed.args:
            print(f"- **{arg.name}** (`{arg.type}`)")
            if arg.description:
                print(f"  - {arg.description}")

        # Include examples if available
        if parsed.examples:
            print("\n### Examples\n")
            for example in parsed.examples:
                print(f"```python\n{example}\n```\n")

        # Include notes if available
        if parsed.notes:
            print(f"\n### Notes\n\n{parsed.notes}\n")
```

### UI Generation

Build dynamic UIs for transform configuration:

```python
from albu_spec import get_transform_metadata
import albumentations as A

metadata = get_transform_metadata(A.RandomCrop)

# Generate UI controls based on parameter types and constraints
for param_name, param in metadata.parameters.items():
    if isinstance(param.type_hint, list):
        # Literal type - create dropdown with exact values
        print(f"Dropdown for {param_name}: options={param.type_hint}")
        # Example: pad_position -> ['center', 'top_left', 'top_right', 'bottom_left', 'bottom_right', 'random']
    elif param.type_hint == "int" and param.constraints:
        # Create slider with min/max from constraints
        min_val = param.constraints.ge or param.constraints.gt or 0
        max_val = param.constraints.le or param.constraints.lt or 100
        print(f"Slider for {param_name}: range({min_val}, {max_val})")
    elif "|" in param.type_hint:
        # Union type - render custom input (not dropdown)
        print(f"Union input for {param_name}: {param.type_hint}")
        # Example: fill -> "tuple[float, ...] | float"
```

### Website/Documentation Backend

Generate structured data for documentation websites:

```python
from albu_spec import get_transform_metadata
import albumentations as A
import json

metadata = get_transform_metadata(A.Blur)

# Create structured data for website rendering
doc_data = {
    "name": metadata.name,
    "type": metadata.transform_type,
    "description": metadata.docstring_parsed.short_description if metadata.docstring_parsed else "",
    "parameters": [],
    "examples": [],
    "notes": None,
}

if metadata.docstring_parsed:
    parsed = metadata.docstring_parsed

    # Parameter table data
    for arg in parsed.args:
        doc_data["parameters"].append({
            "name": arg.name,
            "type": arg.type,
            "description": arg.description,
            "default": metadata.parameters[arg.name].default if arg.name in metadata.parameters else None,
        })

    # Code examples
    doc_data["examples"] = [{"language": "python", "code": ex} for ex in parsed.examples]

    # Notes/warnings
    doc_data["notes"] = parsed.notes

# Export as JSON
print(json.dumps(doc_data, indent=2))
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
- google-docstring-parser >= 0.0.11
- typing-extensions >= 4.0
- PyTorch >= 2.13, installed for the target CPU, CUDA, or MPS environment
- albumentationsx >= 2.4.6 (installed with `albu-spec`, imported as `albumentations`)

## Contributing

Contributions are welcome! Before submitting your first contribution, please:

1. Read our [Contributing Guide](CONTRIBUTING.md)
2. Sign the [Contributor License Agreement (CLA)](CLA.md)

For questions, open an [issue](https://github.com/albumentations-team/albu-spec/issues) or email vladimir@albumentations.ai

## License

The public repository is available under
[AGPL-3.0-only](LICENSE). The AGPL permits commercial use subject to its
terms. Albumentations, LLC also offers separately negotiated commercial
licenses with alternative rights defined in the applicable agreement or order
form. See [LICENSING.md](LICENSING.md) for the current license boundary and
release history.

For licensing questions, contact vladimir@albumentations.ai.

## Related Projects

- [AlbumentationsX](https://github.com/albumentations-team/AlbumentationsX) -
Fast image augmentation library

## Credits

Developed by Vladimir Iglovikov and the Albumentations team.
