"""Tests for license and CLA provenance verification."""

from __future__ import annotations

import zipfile
from pathlib import Path

from scripts.verify_legal_integrity import (
    FIRST_ONLY_RELEASE,
    REPO_ROOT,
    REQUIRED_LICENSE_FILES,
    collect_artifact_errors,
    collect_source_errors,
)


def _expected_files() -> dict[str, bytes]:
    return {relative_path: (REPO_ROOT / relative_path).read_bytes() for relative_path in REQUIRED_LICENSE_FILES}


def _write_wheel(
    path: Path,
    *,
    license_expression: str = "AGPL-3.0-only",
    version: str = FIRST_ONLY_RELEASE,
    include_cla: bool = False,
) -> None:
    metadata = "\n".join(
        (
            "Metadata-Version: 2.4",
            "Name: albu-spec",
            f"Version: {version}",
            f"License-Expression: {license_expression}",
            *(f"License-File: {relative_path}" for relative_path in REQUIRED_LICENSE_FILES),
            "",
        ),
    ).encode()
    with zipfile.ZipFile(path, "w") as archive:
        for relative_path, content in _expected_files().items():
            archive.writestr(f"albu_spec-{FIRST_ONLY_RELEASE}.dist-info/licenses/{relative_path}", content)
        archive.writestr(f"albu_spec-{FIRST_ONLY_RELEASE}.dist-info/METADATA", metadata)
        if include_cla:
            archive.writestr("CLA.md", b"inbound agreement")


def test_source_legal_integrity() -> None:
    """The checked-in legal sources match their recorded provenance."""
    assert collect_source_errors() == []


def test_artifact_accepts_license_metadata_and_files(tmp_path: Path) -> None:
    """A distribution with the current license metadata passes."""
    wheel = tmp_path / f"albu_spec-{FIRST_ONLY_RELEASE}-py3-none-any.whl"
    _write_wheel(wheel)

    assert collect_artifact_errors(wheel, _expected_files()) == []


def test_artifact_rejects_previous_license_expression(tmp_path: Path) -> None:
    """New artifacts cannot reuse the earlier or-later expression."""
    wheel = tmp_path / f"albu_spec-{FIRST_ONLY_RELEASE}-py3-none-any.whl"
    _write_wheel(wheel, license_expression="AGPL-3.0-or-later")

    assert collect_artifact_errors(wheel, _expected_files()) == [
        f"{wheel.name}: License-Expression must be 'AGPL-3.0-only', found 'AGPL-3.0-or-later'",
    ]


def test_artifact_rejects_version_published_with_previous_license(tmp_path: Path) -> None:
    """New license metadata cannot replace an already published release."""
    wheel = tmp_path / f"albu_spec-{FIRST_ONLY_RELEASE}-py3-none-any.whl"
    _write_wheel(wheel, version="0.0.6")

    assert collect_artifact_errors(wheel, _expected_files()) == [
        f"{wheel.name}: reuses published version 0.0.6; AGPL-3.0-only artifacts start at {FIRST_ONLY_RELEASE}",
    ]


def test_artifact_rejects_cla_material(tmp_path: Path) -> None:
    """Contributor agreements stay out of public package artifacts."""
    wheel = tmp_path / f"albu_spec-{FIRST_ONLY_RELEASE}-py3-none-any.whl"
    _write_wheel(wheel, include_cla=True)

    assert collect_artifact_errors(wheel, _expected_files()) == [
        f"{wheel.name}: private CLA material leaked into artifact as CLA.md",
    ]
