"""Parser for extracting information from transform docstrings."""

from typing import Any

from google_docstring_parser import parse_google_docstring


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
