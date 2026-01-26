"""Data models for transform metadata."""

from typing import Any, Literal

from pydantic import BaseModel, Field


class DocstringArg(BaseModel):
    """Parsed argument from docstring Args section.

    Attributes:
        name: Parameter name
        type: Type annotation string (if present in docstring)
        description: Parameter description

    """

    name: str
    type: str | None = None
    description: str | None = None


class DocstringReturn(BaseModel):
    """Parsed return information from docstring Returns section.

    Attributes:
        type: Return type annotation string (if present)
        description: Return value description

    """

    type: str | None = None
    description: str | None = None


class DocstringRaises(BaseModel):
    """Parsed exception from docstring Raises section.

    Attributes:
        type: Exception type name
        description: When/why this exception is raised

    """

    type: str
    description: str | None = None


class ParsedDocstring(BaseModel):
    """Structured parsed docstring from google-docstring-parser.

    Attributes:
        short_description: First paragraph/sentence
        long_description: Extended description
        args: List of parsed arguments
        returns: Return value information
        raises: List of exceptions that may be raised
        yields: Yield information (for generators)
        examples: Code examples from Examples section
        notes: Additional notes
        warnings: Warnings for users
        see_also: Related functions/classes
        references: Citations or links
        attributes: Class attributes (for class docstrings)
        extra_sections: Dictionary of all other sections found in docstring
                       (e.g., "Image types", "Targets", "Mathematical Formulation", etc.)

    """

    short_description: str | None = None
    long_description: str | None = None
    args: list[DocstringArg] = Field(default_factory=list)
    returns: DocstringReturn | None = None
    raises: list[DocstringRaises] = Field(default_factory=list)
    yields: DocstringReturn | None = None
    examples: list[str] = Field(default_factory=list)
    notes: str | None = None
    warnings: str | None = None
    see_also: str | None = None
    references: str | None = None
    attributes: list[DocstringArg] = Field(default_factory=list)
    extra_sections: dict[str, Any] = Field(default_factory=dict)


class ConstraintInfo(BaseModel):
    """Information about parameter constraints from Pydantic Field and validators.

    Attributes:
        ge: Greater than or equal to (>=)
        le: Less than or equal to (<=)
        gt: Greater than (>)
        lt: Less than (<)
        min_length: Minimum length for sequences
        max_length: Maximum length for sequences
        multiple_of: Value must be a multiple of this
        min_value: Minimum value (from custom validators)
        max_value: Maximum value (from custom validators)
        pattern: Regex pattern for strings
        validators: List of validator function names
        validator_info: Additional information from validators

    """

    ge: float | None = None
    le: float | None = None
    gt: float | None = None
    lt: float | None = None
    min_length: int | None = None
    max_length: int | None = None
    multiple_of: float | None = None
    min_value: float | None = None
    max_value: float | None = None
    pattern: str | None = None
    validators: list[str] = Field(default_factory=list)
    validator_info: dict[str, Any] = Field(default_factory=dict)


class ParameterMetadata(BaseModel):
    """Complete metadata for a single transform parameter.

    Attributes:
        name: Parameter name
        type_hint: Type annotation as string (e.g., "int", "tuple[int, int] | int")
                   or list of values for Literal types (e.g., [0, 1, 2] or ["a", "b"])
        default: Default value
        description: Description from docstring
        constraints: Pydantic Field constraints and validators

    """

    name: str
    type_hint: str | list[Any]  # Can be a list for Literal types (preserves int, str, etc.)
    default: Any = None
    description: str | None = None
    constraints: ConstraintInfo | None = None


class TransformMetadata(BaseModel):
    """Complete metadata for an Albumentations transform.

    Attributes:
        name: Transform class name
        module: Module path (e.g., "albumentations.augmentations.blur")
        transform_type: Type of transform (image_only, dual, transforms_3d)
        targets: List of supported targets (image, mask, bboxes, keypoints, etc.)
        parameters: Dictionary of parameter metadata keyed by parameter name
        docstring: Complete docstring text (raw)
        docstring_short: Short description from docstring
        docstring_parsed: Structured parsed docstring with all sections
        has_init_schema: Whether the transform has an InitSchema

    """

    name: str
    module: str
    transform_type: Literal["image_only", "dual", "transforms_3d", "unknown"]
    targets: list[str]
    parameters: dict[str, ParameterMetadata]
    docstring: str | None = None
    docstring_short: str | None = None
    docstring_parsed: ParsedDocstring | None = None
    has_init_schema: bool = False


class TransformCollection(BaseModel):
    """Collection of transforms grouped by type.

    Attributes:
        image_only: Image-only transforms
        dual: Dual transforms (affect image and targets)
        transforms_3d: 3D transforms
        unknown: Transforms with unknown type
        total_count: Total number of transforms

    """

    image_only: list[TransformMetadata] = Field(default_factory=list)
    dual: list[TransformMetadata] = Field(default_factory=list)
    transforms_3d: list[TransformMetadata] = Field(default_factory=list)
    unknown: list[TransformMetadata] = Field(default_factory=list)

    @property
    def total_count(self) -> int:
        """Total number of transforms across all categories."""
        return len(self.image_only) + len(self.dual) + len(self.transforms_3d) + len(self.unknown)

    def get_all(self) -> list[TransformMetadata]:
        """Get all transforms as a flat list."""
        return self.image_only + self.dual + self.transforms_3d + self.unknown
