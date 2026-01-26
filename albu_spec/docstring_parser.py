"""Parser for extracting information from transform docstrings."""

from typing import Any

from google_docstring_parser import parse_google_docstring

from albu_spec.models import DocstringArg, DocstringRaises, DocstringReturn, ParsedDocstring


class DocstringParser:
    """Extract parameter descriptions and other information from docstrings."""

    def parse_docstring(self, transform_class: type) -> dict[str, str]:
        """Parse docstring and extract parameter descriptions.

        Args:
            transform_class: The transform class to parse

        Returns:
            Dictionary mapping parameter names to their descriptions

        """
        if not transform_class.__doc__:
            return {}

        try:
            parsed = parse_google_docstring(transform_class.__doc__)
            return self._extract_parameter_descriptions(parsed)
        except (ValueError, KeyError, AttributeError):
            # If parsing fails, return empty dict
            return {}

    def _extract_parameter_descriptions(self, parsed_docstring: dict[str, Any]) -> dict[str, str]:
        """Extract parameter descriptions from parsed docstring.

        Args:
            parsed_docstring: Parsed docstring dictionary

        Returns:
            Dictionary mapping parameter names to descriptions

        """
        descriptions: dict[str, str] = {}

        # Check if 'Args' key exists in parsed docstring (capitalized)
        args_list = parsed_docstring.get("Args") or parsed_docstring.get("args")
        if args_list:
            for arg in args_list:
                if isinstance(arg, dict) and "name" in arg and "description" in arg:
                    param_name = arg["name"]
                    param_description = arg["description"]

                    # Clean up the description
                    if param_description:
                        descriptions[param_name] = param_description.strip()

        return descriptions

    def get_short_description(self, transform_class: type) -> str | None:
        """Get the short description from the docstring.

        Args:
            transform_class: The transform class to parse

        Returns:
            Short description or None if not found

        """
        if not transform_class.__doc__:
            return None

        # Try multiple strategies in order
        strategies = [
            self._try_short_description,
            self._try_long_description,
            self._try_first_line,
        ]

        for strategy in strategies:
            result = strategy(transform_class)
            if result:
                return result

        return None

    def _try_short_description(self, transform_class: type) -> str | None:
        """Try to extract short description from parsed docstring.

        Args:
            transform_class: The transform class to parse

        Returns:
            Short description or None if not found

        """
        if not transform_class.__doc__:
            return None

        try:
            parsed = parse_google_docstring(transform_class.__doc__)
            description = parsed.get("Description") or parsed.get("short_description")
            if description:
                desc_str = str(description).strip()
                paragraphs = desc_str.split("\n\n")
                return paragraphs[0].strip() if paragraphs else desc_str
        except (ValueError, KeyError, AttributeError):
            # Parsing failed, try next strategy
            pass
        return None

    def _try_long_description(self, transform_class: type) -> str | None:
        """Try to extract first paragraph from long description.

        Args:
            transform_class: The transform class to parse

        Returns:
            First paragraph of long description or None if not found

        """
        if not transform_class.__doc__:
            return None

        try:
            parsed = parse_google_docstring(transform_class.__doc__)
            long_desc = parsed.get("Long Description") or parsed.get("long_description")
            if long_desc:
                long_desc_str = str(long_desc).strip()
                paragraphs = long_desc_str.split("\n\n")
                return paragraphs[0].strip() if paragraphs else long_desc_str
        except (ValueError, KeyError, AttributeError):
            # Parsing failed, try next strategy
            pass
        return None

    def _try_first_line(self, transform_class: type) -> str | None:
        """Try to extract first non-empty line from raw docstring.

        Args:
            transform_class: The transform class to parse

        Returns:
            First non-empty line or None if not found

        """
        if transform_class.__doc__:
            for doc_line in transform_class.__doc__.split("\n"):
                stripped_line = doc_line.strip()
                if stripped_line:
                    return stripped_line
        return None

    def parse_full_docstring(self, transform_class: type) -> ParsedDocstring | None:
        """Parse complete docstring into structured format.

        Args:
            transform_class: The transform class to parse

        Returns:
            ParsedDocstring with all sections or None if parsing fails

        """
        if not transform_class.__doc__:
            return None

        try:
            parsed = parse_google_docstring(transform_class.__doc__)
            return self._convert_to_parsed_docstring(parsed)
        except (ValueError, KeyError, AttributeError, TypeError):
            return None

    def _convert_to_parsed_docstring(self, parsed: dict[str, Any]) -> ParsedDocstring:
        """Convert google-docstring-parser output to ParsedDocstring model.

        Args:
            parsed: Raw parsed docstring dictionary

        Returns:
            Structured ParsedDocstring object

        """
        # Known section keys that we handle explicitly
        known_keys = {
            "Description",
            "short_description",
            "Long Description",
            "long_description",
            "Args",
            "args",
            "Returns",
            "returns",
            "Raises",
            "raises",
            "Yields",
            "yields",
            "Examples",
            "examples",
            "Example",
            "example",
            "Notes",
            "notes",
            "Note",
            "note",
            "Warnings",
            "warnings",
            "Warning",
            "warning",
            "See Also",
            "see_also",
            "References",
            "references",
            "Attributes",
            "attributes",
            "errors",  # Sometimes appears as a key but isn't a real section
        }

        # Extract short and long descriptions
        short_desc = self._extract_description(parsed, "Description", "short_description")
        long_desc = self._extract_description(parsed, "Long Description", "long_description")

        # Extract args
        args = self._extract_args(parsed)

        # Extract returns
        returns = self._extract_returns(parsed)

        # Extract raises
        raises = self._extract_raises(parsed)

        # Extract yields
        yields_info = self._extract_yields(parsed)

        # Extract examples
        examples = self._extract_examples(parsed)

        # Extract notes, warnings, see also, references
        notes = self._extract_text_section(parsed, "Notes", "notes", "Note", "note")
        warnings = self._extract_text_section(parsed, "Warnings", "warnings", "Warning", "warning")
        see_also = self._extract_text_section(parsed, "See Also", "see_also")
        references = self._extract_text_section(parsed, "References", "references")

        # Extract attributes (for class docstrings)
        attributes = self._extract_attributes(parsed)

        # Capture ALL other sections that aren't in known_keys
        extra_sections: dict[str, Any] = {}
        for key, value in parsed.items():
            if key not in known_keys and value:
                # Convert value to string or keep as-is if it's already structured
                if isinstance(value, str):
                    extra_sections[key] = value.strip()
                elif isinstance(value, (list, dict)):
                    extra_sections[key] = value
                else:
                    extra_sections[key] = str(value).strip()

        return ParsedDocstring(
            short_description=short_desc,
            long_description=long_desc,
            args=args,
            returns=returns,
            raises=raises,
            yields=yields_info,
            examples=examples,
            notes=notes,
            warnings=warnings,
            see_also=see_also,
            references=references,
            attributes=attributes,
            extra_sections=extra_sections,
        )

    def _extract_description(self, parsed: dict[str, Any], *keys: str) -> str | None:
        """Extract description from parsed docstring.

        Args:
            parsed: Parsed docstring dictionary
            keys: Possible keys to check (in order)

        Returns:
            Description string or None

        """
        for key in keys:
            value = parsed.get(key)
            if value:
                return str(value).strip()
        return None

    def _extract_args(self, parsed: dict[str, Any]) -> list[DocstringArg]:
        """Extract arguments from parsed docstring.

        Args:
            parsed: Parsed docstring dictionary

        Returns:
            List of DocstringArg objects

        """
        args_list = parsed.get("Args") or parsed.get("args") or []
        return [
            DocstringArg(
                name=arg.get("name", ""),
                type=arg.get("type"),
                description=arg.get("description", "").strip() if arg.get("description") else None,
            )
            for arg in args_list
            if isinstance(arg, dict)
        ]

    def _extract_returns(self, parsed: dict[str, Any]) -> DocstringReturn | None:
        """Extract return information from parsed docstring.

        Args:
            parsed: Parsed docstring dictionary

        Returns:
            DocstringReturn object or None

        """
        returns = parsed.get("Returns") or parsed.get("returns")
        if not returns:
            return None

        if isinstance(returns, dict):
            return DocstringReturn(
                type=returns.get("type"),
                description=returns.get("description", "").strip() if returns.get("description") else None,
            )

        if isinstance(returns, str):
            return DocstringReturn(description=returns.strip())

        return None

    def _extract_raises(self, parsed: dict[str, Any]) -> list[DocstringRaises]:
        """Extract raises information from parsed docstring.

        Args:
            parsed: Parsed docstring dictionary

        Returns:
            List of DocstringRaises objects

        """
        raises_list = parsed.get("Raises") or parsed.get("raises") or []
        result: list[DocstringRaises] = []

        for raises in raises_list:
            if isinstance(raises, dict):
                exc_type = raises.get("type") or raises.get("name") or "Exception"
                result.append(
                    DocstringRaises(
                        type=exc_type,
                        description=raises.get("description", "").strip() if raises.get("description") else None,
                    ),
                )

        return result

    def _extract_yields(self, parsed: dict[str, Any]) -> DocstringReturn | None:
        """Extract yields information from parsed docstring.

        Args:
            parsed: Parsed docstring dictionary

        Returns:
            DocstringReturn object or None

        """
        yields_info = parsed.get("Yields") or parsed.get("yields")
        if not yields_info:
            return None

        if isinstance(yields_info, dict):
            return DocstringReturn(
                type=yields_info.get("type"),
                description=yields_info.get("description", "").strip() if yields_info.get("description") else None,
            )

        if isinstance(yields_info, str):
            return DocstringReturn(description=yields_info.strip())

        return None

    def _extract_examples(self, parsed: dict[str, Any]) -> list[str]:
        """Extract examples from parsed docstring.

        Args:
            parsed: Parsed docstring dictionary

        Returns:
            List of example strings

        """
        examples = parsed.get("Examples") or parsed.get("examples") or parsed.get("Example") or parsed.get("example")
        if not examples:
            return []

        if isinstance(examples, str):
            return [examples.strip()]

        if isinstance(examples, list):
            return [str(ex).strip() for ex in examples if ex]

        return []

    def _extract_text_section(self, parsed: dict[str, Any], *keys: str) -> str | None:
        """Extract text section from parsed docstring.

        Args:
            parsed: Parsed docstring dictionary
            keys: Possible keys to check (in order)

        Returns:
            Section text or None

        """
        for key in keys:
            value = parsed.get(key)
            if value:
                if isinstance(value, str):
                    return value.strip()
                return str(value).strip()
        return None

    def _extract_attributes(self, parsed: dict[str, Any]) -> list[DocstringArg]:
        """Extract attributes from parsed docstring (for class docstrings).

        Args:
            parsed: Parsed docstring dictionary

        Returns:
            List of DocstringArg objects representing attributes

        """
        attrs_list = parsed.get("Attributes") or parsed.get("attributes") or []
        return [
            DocstringArg(
                name=attr.get("name", ""),
                type=attr.get("type"),
                description=attr.get("description", "").strip() if attr.get("description") else None,
            )
            for attr in attrs_list
            if isinstance(attr, dict)
        ]
