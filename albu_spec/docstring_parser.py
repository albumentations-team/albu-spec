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
        except Exception:
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

        try:
            parsed = parse_google_docstring(transform_class.__doc__)
            # Try capitalized keys first, then lowercase
            description = parsed.get("Description") or parsed.get("short_description")
            if description:
                # Extract first paragraph (before blank line)
                desc_str = str(description).strip()
                # Split by double newline or find first paragraph
                paragraphs = desc_str.split("\n\n")
                return paragraphs[0].strip() if paragraphs else desc_str

            long_desc = parsed.get("Long Description") or parsed.get("long_description")
            if long_desc:
                # Use first paragraph of long description
                long_desc_str = str(long_desc).strip()
                paragraphs = long_desc_str.split("\n\n")
                return paragraphs[0].strip() if paragraphs else long_desc_str
        except Exception:
            pass

        # Fallback: get first non-empty line from docstring
        if transform_class.__doc__:
            for line in transform_class.__doc__.split("\n"):
                line = line.strip()
                if line:
                    return line

        return None
