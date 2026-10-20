"""Conditional artifact file formats, validation, and immutable metadata reads."""

import json
import os
from collections.abc import Callable
from pathlib import Path
from unittest import mock

import pytest

import github_action_utils as gha
from github_action_utils._serialization import JSONValue

from ._types import LegacyValue


def test_file_artifact_declarations_are_explicit_raw_records(tmp_path: Path) -> None:
    path = tmp_path / "commands"
    paths = [
        "dist/my file%0A",
        "#ambiguous",
        "image@sha256:" + "a" * 64,
        "dist/বাংলা",
        "/absolute/path",
        "C:\\build\\app.exe",
        " leading-space",
    ]
    with mock.patch.dict(os.environ, {"GITHUB_ARTIFACTS": str(path)}):
        for declaration in paths:
            gha.declare_file_artifact(declaration)
    assert path.read_bytes() == "".join(
        "file://" + item + os.linesep for item in paths
    ).encode("utf-8")
    # No filesystem existence check or upload is performed at declaration time.


@pytest.mark.parametrize(
    "algorithm,length", [("sha256", 64), ("sha384", 96), ("sha512", 128)]
)
@pytest.mark.parametrize("prefix", ["", "oci://", "OCI://"])
def test_oci_artifact_declarations(
    tmp_path: Path, algorithm: str, length: int, prefix: str
) -> None:
    path = tmp_path / "commands"
    reference = "ghcr.io/owner/image:tag@{}:{}".format(algorithm, "A" * length)
    with mock.patch.dict(os.environ, {"GITHUB_ARTIFACTS": str(path)}):
        gha.declare_oci_artifact(prefix + reference)
    assert path.read_bytes() == ("oci://" + reference.lower() + os.linesep).encode(
        "utf-8"
    )


@pytest.mark.parametrize(
    "value",
    [
        "",
        "bad\nname",
        "bad\rname",
        "bad\0name",
        "bad=name",
        "trailing ",
        "trailing\t",
        123,
    ],
)
@pytest.mark.parametrize(
    "helper", [gha.declare_file_artifact, gha.declare_oci_artifact]
)
def test_invalid_artifact_declarations_do_not_change_file(
    tmp_path: Path, value: LegacyValue, helper: Callable[[str], None]
) -> None:
    path = tmp_path / "commands"
    with mock.patch.dict(os.environ, {"GITHUB_ARTIFACTS": str(path)}):
        with pytest.raises((TypeError, ValueError)):
            helper(value)  # type: ignore[arg-type]  # Deliberately invalid runtime input.
        assert not path.exists()
        path.write_bytes(b"unchanged")
        with pytest.raises((TypeError, ValueError)):
            helper(value)  # type: ignore[arg-type]  # Deliberately invalid runtime input.
    assert path.read_bytes() == b"unchanged"


@pytest.mark.parametrize(
    "reference",
    [
        "image:tag",
        "@sha256:" + "a" * 64,
        "image@md5:" + "a" * 32,
        "image@sha256:" + "a" * 63,
        "image@sha256:" + "g" * 64,
        "image@sha384:" + "a" * 64,
        "oci://",
        "image@sha256:" + "a" * 65,
    ],
)
def test_invalid_oci_reference(tmp_path: Path, reference: str) -> None:
    path = tmp_path / "commands"
    with mock.patch.dict(os.environ, {"GITHUB_ARTIFACTS": str(path)}):
        with pytest.raises(ValueError):
            gha.declare_oci_artifact(reference)
    assert not path.exists()


@pytest.mark.parametrize(
    "environment", [{}, {"GITHUB_ARTIFACTS": "", "GITHUB_ARTIFACTS_LIST": ""}]
)
def test_artifact_configuration_is_required(environment: dict[str, str]) -> None:
    with mock.patch.dict(os.environ, environment, clear=True):
        with pytest.raises(RuntimeError, match="GITHUB_ARTIFACTS"):
            gha.declare_file_artifact("file")
        with pytest.raises(RuntimeError, match="GITHUB_ARTIFACTS"):
            gha.declare_oci_artifact("image@sha256:" + "a" * 64)
        with pytest.raises(RuntimeError, match="GITHUB_ARTIFACTS_LIST"):
            gha.get_workflow_artifacts()


def test_artifact_metadata_is_fresh_readonly_and_immutable(tmp_path: Path) -> None:
    path = tmp_path / "metadata"
    payload = {
        "version": 1,
        "subjects": [
            {
                "name": "বাংলা",
                "digest": "sha256:" + "a" * 64,
                "kind": "file",
                "future": "ignored",
            },
            {
                "name": "ghcr.io/image:tag",
                "digest": "sha384:" + "b" * 96,
                "kind": "oci",
            },
        ],
    }
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    path.write_bytes(data)
    with mock.patch.dict(os.environ, {"GITHUB_ARTIFACTS_LIST": str(path)}):
        subjects = gha.get_workflow_artifacts()
        assert subjects == (
            gha.ArtifactSubject("বাংলা", "sha256:" + "a" * 64, "file"),
            gha.ArtifactSubject("ghcr.io/image:tag", "sha384:" + "b" * 96, "oci"),
        )
        subject = subjects[0]
        with pytest.raises(AttributeError):
            subject.name = "replacement"  # type: ignore[misc]  # Deliberately mutate an immutable tuple.
        assert path.read_bytes() == data
        path.write_text('{"version":1,"subjects":[]}', encoding="utf-8")
        assert gha.get_workflow_artifacts() == ()
        other = tmp_path / "other"
        other.write_bytes(data)
        with mock.patch.dict(os.environ, {"GITHUB_ARTIFACTS_LIST": str(other)}):
            assert gha.get_workflow_artifacts() == subjects


@pytest.mark.parametrize(
    "payload",
    [
        [],
        {},
        {"version": True, "subjects": []},
        {"version": 2, "subjects": []},
        {"version": 1, "subjects": {}},
        {"version": 1, "subjects": [None]},
        {"version": 1, "subjects": [{"name": "sensitive-value"}]},
        {"version": 1, "subjects": [{"name": "n", "digest": 123, "kind": "file"}]},
        {"version": 1, "subjects": [{"name": "n", "digest": "d", "kind": "unknown"}]},
        {"version": 1, "subjects": [{"name": "", "digest": "d", "kind": "file"}]},
    ],
)
def test_invalid_artifact_metadata(tmp_path: Path, payload: JSONValue) -> None:
    path = tmp_path / "metadata"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with mock.patch.dict(os.environ, {"GITHUB_ARTIFACTS_LIST": str(path)}):
        with pytest.raises(ValueError) as error:
            gha.get_workflow_artifacts()
    assert "sensitive-value" not in str(error.value)


@pytest.mark.parametrize("data", [b"", b"not-json"])
def test_unpopulated_or_malformed_metadata_is_not_empty_success(
    tmp_path: Path, data: bytes
) -> None:
    path = tmp_path / "metadata"
    path.write_bytes(data)
    with mock.patch.dict(os.environ, {"GITHUB_ARTIFACTS_LIST": str(path)}):
        with pytest.raises(ValueError, match="empty or invalid JSON"):
            gha.get_workflow_artifacts()


def test_missing_configured_artifact_file_propagates(tmp_path: Path) -> None:
    with mock.patch.dict(
        os.environ, {"GITHUB_ARTIFACTS_LIST": str(tmp_path / "missing")}
    ):
        with pytest.raises(FileNotFoundError):
            gha.get_workflow_artifacts()
