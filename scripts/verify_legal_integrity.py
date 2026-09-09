"""Verify license, CLA provenance, and distribution artifact integrity."""

from __future__ import annotations

import argparse
import hashlib
import sys
import tarfile
import zipfile
from email.parser import BytesParser
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python 3.10 uses the dev dependency
    import tomli as tomllib

REPO_ROOT = Path(__file__).resolve().parents[1]

SPDX_LICENSE = "AGPL-3.0-only"
FIRST_ONLY_RELEASE = "0.0.7"
PUBLISHED_OR_LATER_VERSIONS = frozenset({"0.0.1", "0.0.2", "0.0.3", "0.0.4", "0.0.5", "0.0.6"})
AGPL_TEXT_SHA256 = "0d96a4ff68ad6d4b6f1f30f713b18d5184912ba8dd389f86aa7710db079abcb0"
CLA_V1_SHA256 = "126fa969d9961f7417bbdb749280b041adcc299bcc3f3d4887794da858282c51"
CLA_V2_SHA256 = "7951d80788a1bae3abd89473f2a959fc27300838bd93265de57d3897113247b2"
CLA_GIST_URL = "https://gist.github.com/ternaus/e6e90220438d04c0023cb80658cb8823"
CLA_GIST_REVISION = "8af30991a0c8eddc57ca9b4ab7907183992aaa08"

REQUIRED_LICENSE_FILES = ("LICENSE", "LICENSING.md")
SDIST_ROOT_METADATA_DEPTH = 2


def sha256(data: bytes) -> str:
    """Return the lowercase SHA-256 digest for data."""
    return hashlib.sha256(data).hexdigest()


def _read_required_files(repo_root: Path) -> dict[str, bytes]:
    return {relative_path: (repo_root / relative_path).read_bytes() for relative_path in REQUIRED_LICENSE_FILES}


def _check_project_metadata(repo_root: Path) -> list[str]:
    pyproject = tomllib.loads((repo_root / "pyproject.toml").read_text(encoding="utf-8"))
    project = pyproject.get("project", {})
    errors: list[str] = []

    if project.get("license") != SPDX_LICENSE:
        errors.append(f"pyproject project.license must be {SPDX_LICENSE!r}")
    if set(project.get("license-files", [])) != set(REQUIRED_LICENSE_FILES):
        errors.append("pyproject project.license-files must contain LICENSE and LICENSING.md")

    project_version = project.get("version")
    if not isinstance(project_version, str) or not project_version:
        errors.append("pyproject project.version must be a non-empty string")
    elif project_version in PUBLISHED_OR_LATER_VERSIONS:
        errors.append(
            f"pyproject version {project_version} is already published with AGPL-3.0-or-later metadata; "
            f"AGPL-3.0-only starts at {FIRST_ONLY_RELEASE}",
        )

    manifest = (repo_root / "MANIFEST.in").read_text(encoding="utf-8")
    required_manifest_lines = (
        "include LICENSE",
        "include LICENSING.md",
        "exclude CLA.md",
        "prune legal",
        "prune signatures",
        "prune tests",
        "prune scripts",
    )
    errors.extend(
        f"MANIFEST.in is missing {line!r}" for line in required_manifest_lines if line not in manifest.splitlines()
    )
    return errors


def _check_license_and_cla(repo_root: Path) -> list[str]:
    archive = repo_root / "legal/cla/archive"
    cla_v1 = (archive / "CLA-v1-eb00f75.md").read_bytes()
    cla_v2 = (repo_root / "CLA.md").read_bytes()
    archived_cla_v2 = (archive / "CLA-v2.0-2026-09-09.md").read_bytes()
    errors: list[str] = []

    expected_digests = {
        "LICENSE": ((repo_root / "LICENSE").read_bytes(), AGPL_TEXT_SHA256),
        "archived CLA Version 1": (cla_v1, CLA_V1_SHA256),
        "CLA.md": (cla_v2, CLA_V2_SHA256),
        "archived CLA Version 2.0": (archived_cla_v2, CLA_V2_SHA256),
    }
    errors.extend(
        f"{label} does not match its immutable SHA-256 identifier"
        for label, (content, expected_digest) in expected_digests.items()
        if sha256(content) != expected_digest
    )
    if cla_v2 != archived_cla_v2:
        errors.append("CLA.md is not byte-identical to the archived Version 2.0 text")

    manifest = (archive / "MANIFEST.md").read_text(encoding="utf-8")
    required_manifest_values = (
        CLA_V1_SHA256,
        CLA_V2_SHA256,
        CLA_GIST_URL,
        CLA_GIST_REVISION,
    )
    errors.extend(f"CLA manifest is missing {value}" for value in required_manifest_values if value not in manifest)

    normalized_cla = " ".join(cla_v2.decode().split())
    required_cla_phrases = (
        "Albumentations, LLC",
        "AGPL-3.0-only",
        "scope and covered period",
        "Additional Individual Representations",
        "Additional Entity Representations",
        "Contributor Consequential-Damages Waiver",
        "September 9, 2026",
    )
    errors.extend(
        f"CLA Version 2.0 is missing {phrase!r}" for phrase in required_cla_phrases if phrase not in normalized_cla
    )
    return errors


def _check_public_copy(repo_root: Path) -> list[str]:
    readme = " ".join((repo_root / "README.md").read_text(encoding="utf-8").split())
    contributing = " ".join((repo_root / "CONTRIBUTING.md").read_text(encoding="utf-8").split())
    licensing = " ".join((repo_root / "LICENSING.md").read_text(encoding="utf-8").split())
    errors: list[str] = []

    required_readme = (
        "AGPL-3.0-only",
        "The AGPL permits commercial use subject to its terms.",
        "separately negotiated commercial licenses",
    )
    errors.extend(f"README.md is missing {phrase!r}" for phrase in required_readme if phrase not in readme)

    required_contributing = (
        "A Version 1 signature does **not** accept Version 2.0.",
        "I have read and agree to the albu-spec CLA Version 2.0 (September 9, 2026) as an individual.",
    )
    errors.extend(
        f"CONTRIBUTING.md is missing {phrase!r}" for phrase in required_contributing if phrase not in contributing
    )

    required_licensing = (
        "Versions 0.0.1 through 0.0.6.",
        "Beginning with version 0.0.7.",
        "Already published artifacts must never be rebuilt or republished with different license metadata.",
    )
    errors.extend(f"LICENSING.md is missing {phrase!r}" for phrase in required_licensing if phrase not in licensing)
    return errors


def collect_source_errors(repo_root: Path = REPO_ROOT) -> list[str]:
    """Collect legal-integrity violations from the source tree."""
    required_files = (
        *REQUIRED_LICENSE_FILES,
        "CLA.md",
        "MANIFEST.in",
        "legal/cla/archive/CLA-v1-eb00f75.md",
        "legal/cla/archive/CLA-v2.0-2026-09-09.md",
        "legal/cla/archive/MANIFEST.md",
    )
    errors = [f"missing required legal file: {path}" for path in required_files if not (repo_root / path).is_file()]
    if errors:
        return errors

    errors.extend(_check_project_metadata(repo_root))
    errors.extend(_check_license_and_cla(repo_root))
    errors.extend(_check_public_copy(repo_root))
    return errors


def _artifact_members(artifact: Path) -> tuple[dict[str, bytes], list[str]]:
    members: dict[str, bytes] = {}
    duplicates: set[str] = set()
    if zipfile.is_zipfile(artifact):
        with zipfile.ZipFile(artifact) as archive:
            for member in archive.infolist():
                if member.is_dir():
                    continue
                if member.filename in members:
                    duplicates.add(member.filename)
                else:
                    members[member.filename] = archive.read(member)
    else:
        with tarfile.open(artifact, "r:*") as archive:
            for member in archive.getmembers():
                if not member.isfile():
                    continue
                if member.name in members:
                    duplicates.add(member.name)
                    continue
                extracted = archive.extractfile(member)
                if extracted is not None:
                    members[member.name] = extracted.read()
    return members, sorted(duplicates)


def _metadata_member_names(artifact: Path, members: Mapping[str, bytes]) -> list[str]:
    metadata_name = "METADATA" if artifact.suffix == ".whl" else "PKG-INFO"
    if artifact.suffix == ".whl":
        return [
            name
            for name in members
            if PurePosixPath(name).name == metadata_name and PurePosixPath(name).parent.name.endswith(".dist-info")
        ]
    return [
        name
        for name in members
        if PurePosixPath(name).name == metadata_name and len(PurePosixPath(name).parts) == SDIST_ROOT_METADATA_DEPTH
    ]


def _metadata_errors(artifact: Path, members: Mapping[str, bytes]) -> list[str]:
    metadata_name = "METADATA" if artifact.suffix == ".whl" else "PKG-INFO"
    metadata_members = _metadata_member_names(artifact, members)
    errors: list[str] = []

    if len(metadata_members) != 1:
        return [f"{artifact.name}: expected one {metadata_name} file, found {len(metadata_members)}"]

    metadata = BytesParser().parsebytes(members[metadata_members[0]], headersonly=True)
    license_expressions = metadata.get_all("License-Expression", [])
    if license_expressions != [SPDX_LICENSE]:
        found = ", ".join(license_expressions) if license_expressions else "missing"
        errors.append(f"{artifact.name}: License-Expression must be {SPDX_LICENSE!r}, found {found!r}")
    versions = metadata.get_all("Version", [])
    if len(versions) != 1:
        errors.append(f"{artifact.name}: expected exactly one Version field")
    elif versions[0] in PUBLISHED_OR_LATER_VERSIONS:
        errors.append(
            f"{artifact.name}: reuses published version {versions[0]}; "
            f"AGPL-3.0-only artifacts start at {FIRST_ONLY_RELEASE}",
        )
    if set(metadata.get_all("License-File", [])) != set(REQUIRED_LICENSE_FILES):
        errors.append(f"{artifact.name}: License-File entries must be LICENSE and LICENSING.md")
    return errors


def _license_file_errors(
    artifact: Path,
    members: Mapping[str, bytes],
    expected_files: Mapping[str, bytes],
) -> list[str]:
    errors: list[str] = []
    metadata_members = _metadata_member_names(artifact, members)
    if len(metadata_members) != 1:
        return errors

    license_root = PurePosixPath(metadata_members[0]).parent
    if artifact.suffix == ".whl":
        license_root /= "licenses"

    for relative_path, expected_bytes in expected_files.items():
        member_name = str(license_root / relative_path)
        if member_name not in members:
            errors.append(f"{artifact.name}: missing license file at {member_name}")
        elif members[member_name] != expected_bytes:
            errors.append(f"{artifact.name}: {relative_path} differs from the source file")
    return errors


def _forbidden_file_errors(artifact: Path, members: Mapping[str, bytes]) -> list[str]:
    errors: list[str] = []

    for name in members:
        normalized_name = "/" + name.replace("\\", "/")
        is_private_cla = (
            PurePosixPath(name).name == "CLA.md"
            or "/legal/cla/" in normalized_name
            or "/signatures/" in normalized_name
        )
        if is_private_cla:
            errors.append(f"{artifact.name}: private CLA material leaked into artifact as {name}")
        if "/tests/" in normalized_name or "/scripts/" in normalized_name:
            errors.append(f"{artifact.name}: source-only file leaked into artifact as {name}")
    return errors


def collect_artifact_errors(artifact: Path, expected_files: Mapping[str, bytes]) -> list[str]:
    """Collect license metadata and source-only file violations from an artifact."""
    members, duplicates = _artifact_members(artifact)
    return [
        *(f"{artifact.name}: duplicate archive member: {name}" for name in duplicates),
        *_metadata_errors(artifact, members),
        *_license_file_errors(artifact, members, expected_files),
        *_forbidden_file_errors(artifact, members),
    ]


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifacts", nargs="*", type=Path, default=())
    return parser.parse_args()


def main() -> int:
    """Run source and optional artifact checks."""
    args = parse_args()
    errors = collect_source_errors()
    expected_files = _read_required_files(REPO_ROOT)
    for artifact in args.artifacts:
        if not artifact.is_file():
            errors.append(f"artifact does not exist: {artifact}")
        else:
            errors.extend(collect_artifact_errors(artifact, expected_files))

    if errors:
        sys.stderr.write("".join(f"ERROR: {error}\n" for error in errors))
    return int(bool(errors))


if __name__ == "__main__":
    raise SystemExit(main())
