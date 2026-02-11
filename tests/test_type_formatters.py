"""Unit tests for type formatter handlers."""

from __future__ import annotations

from collections.abc import Callable
from typing import Annotated, Literal

import pytest

from albu_spec.type_formatters import (
    AnnotatedTypeHandler,
    BasicTypeHandler,
    CallableTypeHandler,
    DefaultTypeHandler,
    DictTypeHandler,
    ListTypeHandler,
    LiteralTypeHandler,
    NoneTypeHandler,
    StringAnnotationHandler,
    TupleTypeHandler,
    TypeFormatter,
    UnionTypeHandler,
)


class TestNoneTypeHandler:
    """Tests for NoneTypeHandler."""

    def test_can_handle_none(self):
        """Test that handler recognizes None type."""
        handler = NoneTypeHandler()
        assert handler.can_handle(None)
        assert handler.can_handle(type(None))

    def test_cannot_handle_other_types(self):
        """Test that handler rejects non-None types."""
        handler = NoneTypeHandler()
        assert not handler.can_handle(int)
        assert not handler.can_handle("str")
        assert not handler.can_handle(42)

    def test_format_none(self):
        """Test that handler formats None as 'None'."""
        handler = NoneTypeHandler()
        formatter = TypeFormatter()
        assert handler.format(None, formatter) == "None"
        assert handler.format(type(None), formatter) == "None"


class TestBasicTypeHandler:
    """Tests for BasicTypeHandler."""

    @pytest.mark.parametrize(
        "type_obj,expected",
        [
            (int, "int"),
            (float, "float"),
            (bool, "bool"),
            (str, "str"),
        ],
    )
    def test_can_handle_basic_types(self, type_obj, expected):  # noqa: ARG002
        """Test that handler recognizes basic Python types."""
        handler = BasicTypeHandler()
        assert handler.can_handle(type_obj)

    def test_cannot_handle_other_types(self):
        """Test that handler rejects non-basic types."""
        handler = BasicTypeHandler()
        assert not handler.can_handle(None)
        assert not handler.can_handle(list)
        assert not handler.can_handle(dict)
        assert not handler.can_handle("string")

    @pytest.mark.parametrize(
        "type_obj,expected",
        [
            (int, "int"),
            (float, "float"),
            (bool, "bool"),
            (str, "str"),
        ],
    )
    def test_format_basic_types(self, type_obj, expected):
        """Test that handler formats basic types correctly."""
        handler = BasicTypeHandler()
        formatter = TypeFormatter()
        assert handler.format(type_obj, formatter) == expected


class TestStringAnnotationHandler:
    """Tests for StringAnnotationHandler."""

    def test_can_handle_string(self):
        """Test that handler recognizes string annotations."""
        handler = StringAnnotationHandler()
        assert handler.can_handle("int")
        assert handler.can_handle("list[int]")

    def test_cannot_handle_non_strings(self):
        """Test that handler rejects non-string types."""
        handler = StringAnnotationHandler()
        assert not handler.can_handle(int)
        assert not handler.can_handle(None)

    def test_format_simple_string(self):
        """Test formatting of simple type strings."""
        handler = StringAnnotationHandler()
        formatter = TypeFormatter()
        assert handler.format("int", formatter) == "int"

    def test_format_complex_string(self):
        """Test formatting of complex type strings."""
        handler = StringAnnotationHandler()
        formatter = TypeFormatter()
        result = handler.format("list[int]", formatter)
        assert result == "list[int]"

    def test_format_invalid_string(self):
        """Test that invalid strings are returned as-is."""
        handler = StringAnnotationHandler()
        formatter = TypeFormatter()
        invalid_str = "NotAValidType"
        result = handler.format(invalid_str, formatter)
        assert result == invalid_str


class TestLiteralTypeHandler:
    """Tests for LiteralTypeHandler."""

    def test_can_handle_literal(self):
        """Test that handler recognizes Literal types."""
        handler = LiteralTypeHandler()
        assert handler.can_handle(Literal[1, 2, 3])
        assert handler.can_handle(Literal["a", "b"])

    def test_cannot_handle_non_literal(self):
        """Test that handler rejects non-Literal types."""
        handler = LiteralTypeHandler()
        assert not handler.can_handle(int)
        assert not handler.can_handle(list[int])

    def test_format_literal_ints(self):
        """Test formatting of Literal with integers."""
        handler = LiteralTypeHandler()
        formatter = TypeFormatter()
        result = handler.format(Literal[0, 1, 2], formatter)
        assert result == [0, 1, 2]

    def test_format_literal_strings(self):
        """Test formatting of Literal with strings."""
        handler = LiteralTypeHandler()
        formatter = TypeFormatter()
        result = handler.format(Literal["a", "b", "c"], formatter)
        assert result == ["a", "b", "c"]

    def test_format_literal_mixed(self):
        """Test formatting of Literal with mixed types."""
        handler = LiteralTypeHandler()
        formatter = TypeFormatter()
        result = handler.format(Literal[0, "a", 1, "b"], formatter)
        assert result == [0, "a", 1, "b"]

    def test_format_literal_with_type_objects_returns_json_serializable(self):
        """Literal[int, str] must emit __name__ strings, not raw type objects."""
        import json

        handler = LiteralTypeHandler()
        formatter = TypeFormatter()
        result = handler.format(Literal[int, str, float], formatter)
        assert result == ["int", "str", "float"]
        assert not any(isinstance(v, type) for v in result)
        json.dumps(result)  # Should not raise


class TestUnionTypeHandler:
    """Tests for UnionTypeHandler."""

    def test_can_handle_union_pipe_syntax(self):
        """Test that handler recognizes Union with pipe syntax."""
        handler = UnionTypeHandler()
        assert handler.can_handle(int | str)
        assert handler.can_handle(int | float | None)

    def test_cannot_handle_non_union(self):
        """Test that handler rejects non-Union types."""
        handler = UnionTypeHandler()
        assert not handler.can_handle(int)
        assert not handler.can_handle(list[int])

    def test_format_simple_union(self):
        """Test formatting of simple Union."""
        handler = UnionTypeHandler()
        formatter = TypeFormatter()
        result = handler.format(int | str, formatter)
        assert result in ("int | str", "str | int")  # Order may vary

    def test_format_union_with_none(self):
        """Test formatting of Union with None (Optional)."""
        handler = UnionTypeHandler()
        formatter = TypeFormatter()
        result = handler.format(int | None, formatter)
        parts = set(result.split(" | "))
        assert parts == {"int", "None"}

    def test_format_complex_union(self):
        """Test formatting of complex Union."""
        handler = UnionTypeHandler()
        formatter = TypeFormatter()
        result = handler.format(int | float | str | None, formatter)
        parts = set(result.split(" | "))
        assert parts == {"int", "float", "str", "None"}

    def test_format_literal_union_none(self):
        """Test that Union with Literal returns a list of values."""
        handler = UnionTypeHandler()
        formatter = TypeFormatter()
        result = handler.format(Literal["image", "mask"] | None, formatter)
        assert isinstance(result, list)
        assert len(result) == 3
        assert set(result) == {"image", "mask", None}

    def test_format_literal_union_int_none(self):
        """Test that Union with Literal[int] returns a list of int values."""
        handler = UnionTypeHandler()
        formatter = TypeFormatter()
        result = handler.format(Literal[0, 1, 2] | None, formatter)
        assert isinstance(result, list)
        assert len(result) == 4
        assert set(result) == {0, 1, 2, None}

    def test_format_literal_union_multiple_literals_and_none(self):
        """Test that Union with multiple Literal parts merges all values plus None."""
        handler = UnionTypeHandler()
        formatter = TypeFormatter()
        result = handler.format(Literal[0, 1, 2, 3] | None, formatter)
        assert isinstance(result, list)
        assert len(result) == 5
        assert set(result) == {0, 1, 2, 3, None}

    def test_format_regular_union_stays_string(self):
        """Test that regular Union without Literal stays as string."""
        handler = UnionTypeHandler()
        formatter = TypeFormatter()
        result = handler.format(tuple[int, int] | int, formatter)
        assert isinstance(result, str)
        assert result in ("tuple[int, int] | int", "int | tuple[int, int]")

    def test_format_literal_union_unbounded_falls_back_to_string(self):
        """Literal | int cannot be a finite list - no type objects in output."""
        import json

        handler = UnionTypeHandler()
        formatter = TypeFormatter()
        result = handler.format(Literal["a", "b"] | int, formatter)
        assert isinstance(result, str)
        assert "<class" not in str(result)
        assert "int" in result
        json.dumps(result)  # Must be JSON-serializable (no raw type objects)

    def test_format_literal_union_dedupes_and_preserves_order(self):
        """Multiple Literals with overlap - deduped, stable order."""
        handler = UnionTypeHandler()
        formatter = TypeFormatter()
        result = handler.format(Literal[0, 1, 2, 3] | None, formatter)
        assert isinstance(result, list)
        assert len(result) == 5  # 0, 1, 2, 3, None - no duplicates
        assert set(result) == {0, 1, 2, 3, None}
        # Order: first-seen wins (from union arg order)
        assert result.index(0) < result.index(3)
        assert result[-1] is None  # None appended last per our iteration

    def test_format_literal_with_type_objects_returns_json_serializable(self):
        """Literal[int, str] etc. must emit strings, not raw type objects (JSON-safe)."""
        import json

        handler = UnionTypeHandler()
        formatter = TypeFormatter()
        result = handler.format(Literal[int, str, float] | None, formatter)
        assert isinstance(result, list)
        assert len(result) == 4
        assert set(result) == {"int", "str", "float", None}
        assert not any(isinstance(v, type) for v in result)
        json.dumps(result)  # Should not raise


class TestTupleTypeHandler:
    """Tests for TupleTypeHandler."""

    def test_can_handle_tuple(self):
        """Test that handler recognizes tuple types."""
        handler = TupleTypeHandler()
        assert handler.can_handle(tuple[int, int])
        assert handler.can_handle(tuple[str, ...])

    def test_cannot_handle_non_tuple(self):
        """Test that handler rejects non-tuple types."""
        handler = TupleTypeHandler()
        assert not handler.can_handle(int)
        assert not handler.can_handle(list[int])

    def test_format_fixed_tuple(self):
        """Test formatting of fixed-length tuple."""
        handler = TupleTypeHandler()
        formatter = TypeFormatter()
        result = handler.format(tuple[int, str], formatter)
        assert result == "tuple[int, str]"

    def test_format_variable_tuple(self):
        """Test formatting of variable-length tuple."""
        handler = TupleTypeHandler()
        formatter = TypeFormatter()
        result = handler.format(tuple[int, ...], formatter)
        assert result == "tuple[int, ...]"

    def test_format_empty_tuple(self):
        """Test formatting of unparameterized tuple."""
        handler = TupleTypeHandler()
        formatter = TypeFormatter()
        result = handler.format(tuple, formatter)
        assert result == "tuple"


class TestListTypeHandler:
    """Tests for ListTypeHandler."""

    def test_can_handle_list(self):
        """Test that handler recognizes list types."""
        handler = ListTypeHandler()
        assert handler.can_handle(list[int])
        assert handler.can_handle(list[str])

    def test_cannot_handle_non_list(self):
        """Test that handler rejects non-list types."""
        handler = ListTypeHandler()
        assert not handler.can_handle(int)
        assert not handler.can_handle(tuple[int])

    def test_format_parameterized_list(self):
        """Test formatting of parameterized list."""
        handler = ListTypeHandler()
        formatter = TypeFormatter()
        result = handler.format(list[int], formatter)
        assert result == "list[int]"

    def test_format_empty_list(self):
        """Test formatting of unparameterized list."""
        handler = ListTypeHandler()
        formatter = TypeFormatter()
        result = handler.format(list, formatter)
        assert result == "list"

    def test_format_nested_list(self):
        """Test formatting of nested list."""
        handler = ListTypeHandler()
        formatter = TypeFormatter()
        result = handler.format(list[list[int]], formatter)
        assert result == "list[list[int]]"


class TestDictTypeHandler:
    """Tests for DictTypeHandler."""

    def test_can_handle_dict(self):
        """Test that handler recognizes dict types."""
        handler = DictTypeHandler()
        assert handler.can_handle(dict[str, int])
        assert handler.can_handle(dict[str, list[int]])

    def test_cannot_handle_non_dict(self):
        """Test that handler rejects non-dict types."""
        handler = DictTypeHandler()
        assert not handler.can_handle(int)
        assert not handler.can_handle(list[int])

    def test_format_parameterized_dict(self):
        """Test formatting of parameterized dict."""
        handler = DictTypeHandler()
        formatter = TypeFormatter()
        result = handler.format(dict[str, int], formatter)
        assert result == "dict[str, int]"

    def test_format_empty_dict(self):
        """Test formatting of unparameterized dict."""
        handler = DictTypeHandler()
        formatter = TypeFormatter()
        result = handler.format(dict, formatter)
        assert result == "dict"

    def test_format_nested_dict(self):
        """Test formatting of nested dict."""
        handler = DictTypeHandler()
        formatter = TypeFormatter()
        result = handler.format(dict[str, dict[str, int]], formatter)
        assert result == "dict[str, dict[str, int]]"


class TestAnnotatedTypeHandler:
    """Tests for AnnotatedTypeHandler."""

    def test_can_handle_annotated(self):
        """Test that handler recognizes Annotated types."""
        handler = AnnotatedTypeHandler()
        assert handler.can_handle(Annotated[int, "metadata"])
        assert handler.can_handle(Annotated[str, "doc", "more"])

    def test_cannot_handle_non_annotated(self):
        """Test that handler rejects non-Annotated types."""
        handler = AnnotatedTypeHandler()
        assert not handler.can_handle(int)
        assert not handler.can_handle(list[int])

    def test_format_annotated(self):
        """Test formatting of Annotated type extracts base type."""
        handler = AnnotatedTypeHandler()
        formatter = TypeFormatter()
        result = handler.format(Annotated[int, "metadata"], formatter)
        assert result == "int"

    def test_format_annotated_complex(self):
        """Test formatting of Annotated with complex base type."""
        handler = AnnotatedTypeHandler()
        formatter = TypeFormatter()
        result = handler.format(Annotated[list[int], "doc"], formatter)
        assert result == "list[int]"


class TestCallableTypeHandler:
    """Tests for CallableTypeHandler."""

    def test_can_handle_callable(self):
        """Test that handler recognizes Callable types."""
        handler = CallableTypeHandler()
        assert handler.can_handle(Callable[[int], str])
        assert handler.can_handle(Callable[[], None])

    def test_cannot_handle_non_callable(self):
        """Test that handler rejects non-Callable types."""
        handler = CallableTypeHandler()
        assert not handler.can_handle(int)
        assert not handler.can_handle(list[int])

    def test_format_callable_with_args(self):
        """Test formatting of Callable with arguments."""
        handler = CallableTypeHandler()
        formatter = TypeFormatter()
        result = handler.format(Callable[[int, str], bool], formatter)
        assert result == "Callable[..., bool]"

    def test_format_callable_no_args(self):
        """Test formatting of Callable without arguments."""
        handler = CallableTypeHandler()
        formatter = TypeFormatter()
        result = handler.format(Callable[[], int], formatter)
        assert result == "Callable[..., int]"

    def test_format_unparameterized_callable(self):
        """Test formatting of bare Callable."""
        handler = CallableTypeHandler()
        formatter = TypeFormatter()
        result = handler.format(Callable, formatter)
        assert result == "Callable"


class TestDefaultTypeHandler:
    """Tests for DefaultTypeHandler."""

    def test_can_handle_anything(self):
        """Test that handler accepts any type."""
        handler = DefaultTypeHandler()
        assert handler.can_handle(int)
        assert handler.can_handle("string")
        assert handler.can_handle(None)
        assert handler.can_handle(object())

    def test_format_with_name(self):
        """Test formatting of type with __name__."""
        handler = DefaultTypeHandler()
        formatter = TypeFormatter()
        assert handler.format(int, formatter) == "int"
        assert handler.format(str, formatter) == "str"

    def test_format_without_name(self):
        """Test formatting of object without __name__."""
        handler = DefaultTypeHandler()
        formatter = TypeFormatter()
        obj = object()
        result = handler.format(obj, formatter)
        assert isinstance(result, str)
        assert "object" in result


class TestTypeFormatterIntegration:
    """Integration tests for TypeFormatter."""

    def test_format_basic_types(self):
        """Test formatting of basic types."""
        formatter = TypeFormatter()
        assert formatter.format(int) == "int"
        assert formatter.format(str) == "str"
        assert formatter.format(float) == "float"
        assert formatter.format(bool) == "bool"

    def test_format_none(self):
        """Test formatting of None."""
        formatter = TypeFormatter()
        assert formatter.format(None) == "None"
        assert formatter.format(type(None)) == "None"

    def test_format_union(self):
        """Test formatting of Union types."""
        formatter = TypeFormatter()
        result = formatter.format(int | str)
        parts = set(result.split(" | "))
        assert parts == {"int", "str"}

    def test_format_optional(self):
        """Test formatting of Optional (Union with None)."""
        formatter = TypeFormatter()
        result = formatter.format(int | None)
        parts = set(result.split(" | "))
        assert parts == {"int", "None"}

    def test_format_list(self):
        """Test formatting of list types."""
        formatter = TypeFormatter()
        assert formatter.format(list[int]) == "list[int]"
        assert formatter.format(list) == "list"

    def test_format_dict(self):
        """Test formatting of dict types."""
        formatter = TypeFormatter()
        assert formatter.format(dict[str, int]) == "dict[str, int]"
        assert formatter.format(dict) == "dict"

    def test_format_tuple(self):
        """Test formatting of tuple types."""
        formatter = TypeFormatter()
        assert formatter.format(tuple[int, str]) == "tuple[int, str]"
        assert formatter.format(tuple[int, ...]) == "tuple[int, ...]"
        assert formatter.format(tuple) == "tuple"

    def test_format_literal(self):
        """Test formatting of Literal types."""
        formatter = TypeFormatter()
        assert formatter.format(Literal[1, 2, 3]) == [1, 2, 3]
        assert formatter.format(Literal["a", "b"]) == ["a", "b"]

    def test_format_annotated(self):
        """Test formatting of Annotated types."""
        formatter = TypeFormatter()
        assert formatter.format(Annotated[int, "doc"]) == "int"

    def test_format_callable(self):
        """Test formatting of Callable types."""
        formatter = TypeFormatter()
        assert formatter.format(Callable[[int], str]) == "Callable[..., str]"
        assert formatter.format(Callable) == "Callable"

    def test_format_complex_nested(self):
        """Test formatting of complex nested types."""
        formatter = TypeFormatter()
        result = formatter.format(dict[str, list[int | None]])
        assert result in {"dict[str, list[int | None]]", "dict[str, list[None | int]]"}

    def test_format_string_annotation(self):
        """Test formatting of string annotations."""
        formatter = TypeFormatter()
        assert formatter.format("int") == "int"
        assert formatter.format("list[int]") == "list[int]"

    def test_handler_order_matters(self):
        """Test that handler order determines which handler is used."""
        formatter = TypeFormatter()
        # DefaultHandler should be last, so specific handlers take precedence
        assert formatter.format(int) == "int"  # BasicTypeHandler, not DefaultTypeHandler
        assert formatter.format(None) == "None"  # NoneTypeHandler, not DefaultTypeHandler

    def test_format_literal_union_none(self):
        """Test that Literal | None returns list of values including None."""
        formatter = TypeFormatter()
        result = formatter.format(Literal["image", "mask"] | None)
        assert isinstance(result, list)
        assert len(result) == 3
        assert set(result) == {"image", "mask", None}

    def test_format_literal_int_union_none(self):
        """Test that Literal[int] | None returns list of int values."""
        formatter = TypeFormatter()
        result = formatter.format(Literal[0, 1, 2, 3, 4] | None)
        assert isinstance(result, list)
        assert len(result) == 6
        assert set(result) == {0, 1, 2, 3, 4, None}

    def test_format_literal_union_multiple_literals_and_none(self):
        """Test that Union with multiple Literal parts merges all values plus None."""
        formatter = TypeFormatter()
        result = formatter.format(Literal[0, 1, 2, 3] | None)
        assert isinstance(result, list)
        assert len(result) == 5
        assert set(result) == {0, 1, 2, 3, None}

    def test_format_regular_union_no_literal(self):
        """Test that regular Union without Literal stays as string."""
        formatter = TypeFormatter()
        result = formatter.format(tuple[int, int] | int)
        assert isinstance(result, str)
        # Order may vary
        assert result in ("tuple[int, int] | int", "int | tuple[int, int]")

    def test_format_standalone_literal(self):
        """Test that standalone Literal returns list of values."""
        formatter = TypeFormatter()
        result = formatter.format(Literal["center", "top_left", "bottom_right"])
        assert isinstance(result, list)
        assert len(result) == 3
        assert set(result) == {"center", "top_left", "bottom_right"}

    def test_format_literal_union_unbounded_type(self):
        """Literal | int falls back to string, no type objects."""
        formatter = TypeFormatter()
        result = formatter.format(Literal["a", "b"] | int)
        assert isinstance(result, str)
        assert "<class" not in str(result)
