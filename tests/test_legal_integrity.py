"""Tests for license and CLA provenance verification."""

from __future__ import annotations

import io
import tarfile
import zipfile
from pathlib import Path

import pytest

from scripts.verify_legal_integrity import (
    FIRST_ONLY_RELEASE,
    REPO_ROOT,
    REQUIRED_LICENSE_FILES,
    collect_artifact_errors,
    collect_source_errors,
)


def _expected_files() -> dict[str, bytes]:
    return {relative_path: (REPO_ROOT / relative_path).read_bytes() for relative_path in REQUIRED_LICENSE_FILES}


def _metadata_bytes(*, license_expression: str = "AGPL-3.0-only", version: str = FIRST_ONLY_RELEASE) -> bytes:
    return "\n".join(
        (
            "Metadata-Version: 2.4",
            "Name: albu-spec",
            f"Version: {version}",
            f"License-Expression: {license_expression}",
            *(f"License-File: {relative_path}" for relative_path in REQUIRED_LICENSE_FILES),
            "",
        ),
    ).encode()


def _write_wheel(
    path: Path,
    *,
    license_expression: str = "AGPL-3.0-only",
    version: str = FIRST_ONLY_RELEASE,
    include_cla: bool = False,
    misplaced_license: str | None = None,
) -> None:
    with zipfile.ZipFile(path, "w") as archive:
        for relative_path, content in _expected_files().items():
            member_name = (
                f"arbitrary/{relative_path}"
                if relative_path == misplaced_license
                else f"albu_spec-{FIRST_ONLY_RELEASE}.dist-info/licenses/{relative_path}"
            )
            archive.writestr(member_name, content)
        archive.writestr(
            f"albu_spec-{FIRST_ONLY_RELEASE}.dist-info/METADATA",
            _metadata_bytes(license_expression=license_expression, version=version),
        )
        if include_cla:
            archive.writestr("CLA.md", b"inbound agreement")


def _write_tar_member(archive: tarfile.TarFile, name: str, content: bytes) -> None:
    member = tarfile.TarInfo(name)
    member.size = len(content)
    archive.addfile(member, io.BytesIO(content))


def _write_sdist(
    path: Path,
    *,
    duplicate_license: str | None = None,
    misplaced_license: str | None = None,
) -> None:
    root = f"albu_spec-{FIRST_ONLY_RELEASE}"
    with tarfile.open(path, "w:gz") as archive:
        for relative_path, content in _expected_files().items():
            member_name = (
                f"arbitrary/{relative_path}" if relative_path == misplaced_license else f"{root}/{relative_path}"
            )
            _write_tar_member(archive, member_name, content)
            if relative_path == duplicate_license:
                _write_tar_member(archive, member_name, content)
        _write_tar_member(archive, f"{root}/PKG-INFO", _metadata_bytes())


def test_source_legal_integrity() -> None:
    """The checked-in legal sources match their recorded provenance."""
    assert collect_source_errors() == []


def test_artifact_accepts_license_metadata_and_files(tmp_path: Path) -> None:
    """A distribution with the current license metadata passes."""
    wheel = tmp_path / f"albu_spec-{FIRST_ONLY_RELEASE}-py3-none-any.whl"
    _write_wheel(wheel)

    assert collect_artifact_errors(wheel, _expected_files()) == []


def test_artifact_rejects_duplicate_wheel_member(tmp_path: Path) -> None:
    """Archive members must be unique even when their contents match."""
    wheel = tmp_path / f"albu_spec-{FIRST_ONLY_RELEASE}-py3-none-any.whl"
    _write_wheel(wheel)
    duplicate_name = f"albu_spec-{FIRST_ONLY_RELEASE}.dist-info/licenses/LICENSE"

    with pytest.warns(UserWarning, match="Duplicate name"), zipfile.ZipFile(wheel, "a") as archive:
        archive.writestr(duplicate_name, _expected_files()["LICENSE"])

    assert collect_artifact_errors(wheel, _expected_files()) == [
        f"{wheel.name}: duplicate archive member: {duplicate_name}",
    ]


def test_artifact_rejects_misplaced_wheel_license(tmp_path: Path) -> None:
    """Wheel license files must use the path declared by the packaging standard."""
    wheel = tmp_path / f"albu_spec-{FIRST_ONLY_RELEASE}-py3-none-any.whl"
    _write_wheel(wheel, misplaced_license="LICENSE")
    expected_name = f"albu_spec-{FIRST_ONLY_RELEASE}.dist-info/licenses/LICENSE"

    assert collect_artifact_errors(wheel, _expected_files()) == [
        f"{wheel.name}: missing license file at {expected_name}",
    ]


def test_artifact_rejects_duplicate_sdist_member(tmp_path: Path) -> None:
    """Duplicate file entries invalidate source distributions."""
    sdist = tmp_path / f"albu_spec-{FIRST_ONLY_RELEASE}.tar.gz"
    _write_sdist(sdist, duplicate_license="LICENSE")
    duplicate_name = f"albu_spec-{FIRST_ONLY_RELEASE}/LICENSE"

    assert collect_artifact_errors(sdist, _expected_files()) == [
        f"{sdist.name}: duplicate archive member: {duplicate_name}",
    ]


def test_artifact_rejects_misplaced_sdist_license(tmp_path: Path) -> None:
    """Source-distribution license files must be beside PKG-INFO."""
    sdist = tmp_path / f"albu_spec-{FIRST_ONLY_RELEASE}.tar.gz"
    _write_sdist(sdist, misplaced_license="LICENSE")
    expected_name = f"albu_spec-{FIRST_ONLY_RELEASE}/LICENSE"

    assert collect_artifact_errors(sdist, _expected_files()) == [
        f"{sdist.name}: missing license file at {expected_name}",
    ]


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
