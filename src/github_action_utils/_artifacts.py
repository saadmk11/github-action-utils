"""Conditional workflow artifact declarations and read-only metadata access.

Runner support is conditional; exposed paths alone do not guarantee processing.
Declarations record identities without uploading files or images.
"""

import json
import os
import re
from typing import NamedTuple, cast

from ._files import append_line, validate_single_line
from ._serialization import JSONValue

_OCI_REFERENCE = re.compile(r"(.+)@(sha256|sha384|sha512):([0-9a-fA-F]+)")
_DIGEST_LENGTHS = {"sha256": 64, "sha384": 96, "sha512": 128}


class ArtifactSubject(NamedTuple):
    """An immutable declared identity: name, algorithm:hex digest, and file/oci kind."""

    name: str
    digest: str
    kind: str


def _artifact_file(variable: str) -> str:
    if not (path := os.environ.get(variable)):
        raise RuntimeError(f"{variable} is not configured by the runner")
    return path


def _validate_declaration(value: str) -> None:
    validate_single_line(value, "Artifact declaration")
    if "=" in value:
        raise ValueError(
            "Artifact declarations cannot contain the reserved '=' character"
        )
    if value != value.rstrip():
        raise ValueError("Artifact declarations cannot end in whitespace")


def declare_file_artifact(path: str) -> None:
    """Queue one file identity in GITHUB_ARTIFACTS using explicit file:// framing.

    The runner resolves paths against GITHUB_WORKSPACE and computes digests
    after the step. A successful write does not guarantee runner processing.
    """
    _validate_declaration(path)
    append_line(_artifact_file("GITHUB_ARTIFACTS"), "file://" + path)


def declare_oci_artifact(reference: str) -> None:
    """Queue an OCI reference pinned to a full sha256/sha384/sha512 digest.

    An optional oci:// prefix is accepted. Digest hex is normalized to lowercase.
    This does not push an image or enable the runner's conditional feature.
    """
    _validate_declaration(reference)
    if reference.lower().startswith("oci://"):
        reference = reference[len("oci://") :]
    match = _OCI_REFERENCE.fullmatch(reference)
    if match is None:
        raise ValueError(
            "OCI references require a name and a sha256/sha384/sha512 digest"
        )
    name, algorithm, digest = match.groups("")
    if len(digest) != _DIGEST_LENGTHS[algorithm]:
        raise ValueError("OCI digest has the wrong length for its algorithm")
    declaration = f"oci://{name}@{algorithm}:{digest.lower()}"
    append_line(_artifact_file("GITHUB_ARTIFACTS"), declaration)


def get_workflow_artifacts() -> tuple[ArtifactSubject, ...]:
    """Read fresh, immutable subjects from the current GITHUB_ARTIFACTS_LIST.

    An empty version-1 subjects array returns (). Missing configuration raises
    RuntimeError; empty, malformed, or unsupported metadata raises ValueError.
    File errors propagate.
    """
    with open(_artifact_file("GITHUB_ARTIFACTS_LIST"), encoding="utf-8") as file:
        try:
            payload = cast(JSONValue, json.load(file))
        except json.JSONDecodeError as error:
            raise ValueError(
                "Workflow artifact metadata is empty or invalid JSON"
            ) from error
    if not isinstance(payload, dict):
        raise ValueError("Workflow artifact metadata must be a JSON object")
    version = payload.get("version")
    if type(version) is not int or version != 1:
        raise ValueError("Unsupported workflow artifact metadata version; expected 1")
    subjects = payload.get("subjects")
    if not isinstance(subjects, list):
        raise ValueError("Workflow artifact metadata must contain a subjects array")
    result = []
    for subject in subjects:
        if not isinstance(subject, dict):
            raise ValueError(
                "Artifact subjects require nonempty name, digest, and kind strings"
            )
        name, digest, kind = (
            subject.get(field) for field in ("name", "digest", "kind")
        )
        if (
            not isinstance(name, str)
            or not name
            or not isinstance(digest, str)
            or not digest
            or not isinstance(kind, str)
            or not kind
        ):
            raise ValueError(
                "Artifact subjects require nonempty name, digest, and kind strings"
            )
        if kind not in ("file", "oci"):
            raise ValueError("Artifact subject kind must be file or oci")
        result.append(ArtifactSubject(name, digest, kind))
    return tuple(result)
