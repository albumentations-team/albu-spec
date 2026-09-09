# Contributing to albu-spec

Thank you for your interest in contributing to albu-spec! This guide will help you get started.

## Quick Start

For small changes (bug fixes, typos, documentation improvements), feel free to submit a PR directly.

For larger changes:
1. Create an [issue](https://github.com/albumentations-team/albu-spec/issues) outlining your proposed change
2. Discuss the approach before investing significant time
3. Submit a PR once the approach is agreed upon

## Development Setup

### 1. Fork and Clone

```bash
# Fork the repository on GitHub, then clone your fork
git clone https://github.com/YOUR_USERNAME/albu-spec.git
cd albu-spec
```

### 2. Set Up Development Environment

```bash
# Install uv if you don't have it
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment and install dependencies
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv sync --all-extras --dev
uv pip install --torch-backend auto "torch>=2.13.0"
```

### 3. Install Pre-commit Hooks

```bash
uv run pre-commit install
```

This will automatically run linting and formatting checks before each commit.

## Making Changes

### 1. Create a Branch

```bash
git checkout -b feature/my-new-feature
# or
git checkout -b fix/bug-description
```

### 2. Write Code

Follow our coding guidelines:

- **Type hints**: Use modern syntax (`dict[str, int]` not `Dict[str, int]`)
- **Union types**: Use `|` not `Union` (`int | float` not `Union[int, float]`)
- **Docstrings**: Google style with proper indentation
- **Line length**: 120 characters (configured in pyproject.toml)
- **Imports**: Absolute imports, grouped (stdlib, third-party, local)

### 3. Add Tests

- Place tests in the `tests/` directory
- Follow existing test patterns
- Use pytest fixtures from `conftest.py`
- Aim for high test coverage

Example test:

```python
def test_extract_parameter_metadata(extractor):
    """Test that parameter metadata is extracted correctly."""
    import albumentations as A

    metadata = extractor.extract(A.HorizontalFlip)

    assert "p" in metadata.parameters
    assert metadata.parameters["p"].type_hint == "float"
    assert metadata.parameters["p"].default == 0.5
```

### 4. Run Tests

```bash
# Run all tests
uv run pytest

# Run specific test file
uv run pytest tests/test_schema_parser.py

# Run with coverage
uv run pytest --cov=albu_spec --cov-report=html
```

### 5. Run Linting and Formatting

```bash
# Runs automatically with pre-commit, but you can run manually:
uv run pre-commit run --all-files

# Or individual tools:
uv run ruff check albu_spec/ tests/
uv run ruff format albu_spec/ tests/
uv run mypy albu_spec/
```

## Contributor License Agreement (CLA)

Before we can accept your contribution, you must accept the
[albu-spec Contributor License Agreement Version 2.0](CLA.md). It lets
Albumentations, LLC publish accepted contributions under AGPL-3.0-only and
offer the same contributions under separately negotiated commercial terms.
You retain ownership of your work.

A Version 1 signature does **not** accept Version 2.0. Contributors recorded
only against Version 1 must review and accept Version 2.0 before another
contribution can be merged. The new acceptance covers qualifying contributions
submitted before, on, and after the Version 2.0 acceptance date; it does not
claim that Version 2.0 was accepted earlier.

For an individual contribution, comment on the pull request with this exact
statement:

```text
I have read and agree to the albu-spec CLA Version 2.0 (September 9, 2026) as an individual.
```

If an employer or another legal entity owns or controls the contribution, use
the Entity Acceptance process in [CLA.md](CLA.md). A corporate signer must
identify the exact legal entity, their authority, and the covered contributors.
Maintainers verify the applicable Version 2.0 Acceptance Record before merge.

## Pull Request Process

### 1. Update Your Branch

```bash
# Keep your branch up to date with main
git fetch upstream
git rebase upstream/main
```

### 2. Push Your Changes

```bash
git push origin feature/my-new-feature
```

### 3. Create Pull Request

- Go to GitHub and create a Pull Request from your fork
- Provide a clear description of your changes
- Reference any related issues (e.g., "Fixes #123")
- Wait for CI checks to pass
- Sign the CLA when prompted

### 4. Code Review

- Maintainers will review your PR
- Address any feedback or questions
- Make changes by pushing new commits to your branch
- Once approved, your PR will be merged

## Code Review Guidelines

When reviewing code, we look for:

- **Correctness**: Does it work as intended?
- **Tests**: Are there tests covering the changes?
- **Documentation**: Are docstrings and comments clear?
- **Style**: Does it follow our coding guidelines?
- **Performance**: Are there any obvious performance issues?
- **Security**: Are there any security concerns?

## Types of Contributions

### Bug Fixes

- Include a test that reproduces the bug
- Explain what was wrong and how you fixed it
- Reference the issue number

### New Features

- Discuss the feature in an issue first
- Add comprehensive tests
- Update documentation
- Add examples if applicable

### Documentation

- Fix typos or unclear explanations
- Add examples
- Improve docstrings
- Update README or guides in `docs/`

### Tests

- Improve test coverage
- Add edge case tests
- Add property-based tests for universal invariants

## Project Structure

```
albu-spec/
├── albu_spec/              # Main package
│   ├── __init__.py        # Public API
│   ├── models.py          # Pydantic data models
│   ├── schema_parser.py   # InitSchema constraint extraction
│   ├── docstring_parser.py # Docstring parsing
│   └── extractor.py       # Main metadata extractor
├── tests/                 # Test suite
│   ├── conftest.py        # Shared fixtures
│   ├── test_schema_parser.py
│   ├── test_metadata_consistency.py
│   └── ...
├── docs/                  # Documentation
│   └── TESTING.md
├── pyproject.toml         # Project configuration
├── README.md
├── LICENSE
├── LICENSING.md          # Current license boundary and release history
├── CLAUDE.md             # AI assistant guide
├── CLA.md                # Contributor License Agreement
└── CONTRIBUTING.md       # This file
```

## Documentation

- **README.md**: User-facing documentation and examples
- **CLAUDE.md**: Comprehensive AI assistant guide (architecture, testing philosophy, etc.)
- **docs/**: Additional documentation (TESTING.md, etc.)
- **Docstrings**: In-code documentation following Google style

All documentation should be:
- Clear and concise
- Include examples where appropriate
- Keep up to date with code changes

## Getting Help

- **Issues**: [GitHub Issues](https://github.com/albumentations-team/albu-spec/issues)
- **Discussions**: Open an issue for questions
- **Email**: vladimir@albumentations.ai

## Recognition

Contributors are recognized in several ways:
- Listed in GitHub contributors
- Mentioned in release notes for significant contributions
- Building a portfolio of open source contributions

## Code of Conduct

This project adheres to a code of professional conduct:
- Be respectful and constructive in discussions
- Focus on the technical merits of contributions
- Help create a welcoming environment for all contributors
- Report any unacceptable behavior to vladimir@albumentations.ai

## License

Accepted contributions are published under AGPL-3.0-only. The CLA also lets
Albumentations, LLC offer them under separately negotiated commercial terms.
See [LICENSING.md](LICENSING.md) for the repository license and release
history.

---

Thank you for contributing to albu-spec! Your contributions help improve metadata extraction for the entire AlbumentationsX community.
