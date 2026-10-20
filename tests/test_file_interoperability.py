"""Encoding, record separation, BOM compatibility, and literal summary content."""

import io
import json
import os
from pathlib import Path
from unittest import mock

import pytest

import github_action_utils as gha

from ._types import LegacyValue


def test_repeated_path_entries_preserve_literal_text(tmp_path: Path) -> None:
    path = tmp_path / "paths"
    path.write_bytes(("existing" + os.linesep).encode("utf-8"))
    entries = ["/tmp/first", "C:\\Program Files\\second", "বাংলা %0A"]
    with mock.patch.dict(os.environ, {"GITHUB_PATH": str(path)}):
        original = os.environ.get("PATH")
        for entry in entries:
            gha.add_system_path(entry)
        assert os.environ.get("PATH") == original
    assert path.read_bytes() == (
        os.linesep.join(["existing"] + entries) + os.linesep
    ).encode("utf-8")


@pytest.mark.parametrize(
    "value", ["", "bad\nentry", "bad\rentry", "bad\0entry", None, 123]
)
def test_invalid_path_entries_leave_file_unchanged(
    tmp_path: Path, value: LegacyValue
) -> None:
    path = tmp_path / "paths"
    with mock.patch.dict(os.environ, {"GITHUB_PATH": str(path)}):
        with pytest.raises((TypeError, ValueError)):
            gha.add_system_path(value, strict=True)  # type: ignore[arg-type]  # Deliberately invalid runtime input.
        assert not path.exists()
        path.write_bytes(b"unchanged")
        with pytest.raises((TypeError, ValueError)):
            gha.add_system_path(value, strict=True)  # type: ignore[arg-type]  # Deliberately invalid runtime input.
    assert path.read_bytes() == b"unchanged"


@pytest.mark.parametrize(
    "markdown", ["", "%0A %0D %25 %250A", "# বাংলা\n```\r\n%0A\n```", "a\rb\r\n"]
)
def test_summary_bytes_are_raw_utf8(tmp_path: Path, markdown: str) -> None:
    path = tmp_path / "summary"
    expected = (markdown + "\n").encode("utf-8")
    with mock.patch.dict(os.environ, {"GITHUB_STEP_SUMMARY": str(path)}):
        gha.append_job_summary(markdown)
        gha.append_job_summary(markdown)
        assert path.read_bytes() == expected * 2
        gha.overwrite_job_summary(markdown)
        assert path.read_bytes() == expected
        gha.remove_job_summary()
        assert not path.exists()
        gha.append_job_summary(markdown)
        assert path.read_bytes() == expected


def test_encoding_failure_cannot_truncate_summary(tmp_path: Path) -> None:
    path = tmp_path / "summary"
    path.write_bytes(b"unchanged")
    with mock.patch.dict(os.environ, {"GITHUB_STEP_SUMMARY": str(path)}):
        with pytest.raises(UnicodeEncodeError):
            gha.overwrite_job_summary("\ud800")
    assert path.read_bytes() == b"unchanged"


@pytest.mark.parametrize("platform,newline", [("posix", "\n"), ("nt", "\r\n")])
@pytest.mark.parametrize("bom", [b"", b"\xef\xbb\xbf"])
def test_environment_bom_preserves_records_and_value_characters(
    tmp_path: Path, platform: str, newline: str, bom: bytes
) -> None:
    path = tmp_path / "env"
    records = newline.join(
        ["FIRST=value", "BLOCK<<EOF", "\ufeffinside", "EOF", "FIRST=last", ""]
    )
    path.write_bytes(bom + records.encode("utf-8"))
    with mock.patch.dict(os.environ, {"GITHUB_ENV": str(path), "FIRST": "process"}):
        with mock.patch("github_action_utils.os.name", platform):
            values = gha.get_workflow_environment_variables()
            preferred = gha.get_env("FIRST")
    assert values == {"FIRST": "last", "BLOCK": "\ufeffinside"}
    assert preferred == "process"


def test_bom_before_multiline_first_record_and_empty_file(tmp_path: Path) -> None:
    path = tmp_path / "env"
    path.write_bytes(b"\xef\xbb\xbfBLOCK<<EOF\nvalue\nEOF\n")
    with mock.patch.dict(os.environ, {"GITHUB_ENV": str(path)}):
        assert gha.get_workflow_environment_variables() == {"BLOCK": "value"}
        path.write_bytes(b"\xef\xbb\xbf")
        assert gha.get_workflow_environment_variables() == {}


def test_file_helpers_ignore_non_utf8_locale_defaults(tmp_path: Path) -> None:
    paths = {
        name: str(tmp_path / name)
        for name in [
            "GITHUB_PATH",
            "GITHUB_STEP_SUMMARY",
            "GITHUB_EVENT_PATH",
            "GITHUB_ARTIFACTS_LIST",
        ]
    }
    payload = {"message": "café বাংলা"}
    Path(paths["GITHUB_EVENT_PATH"]).write_bytes(
        json.dumps(payload, ensure_ascii=False).encode("utf-8")
    )
    Path(paths["GITHUB_ARTIFACTS_LIST"]).write_bytes(b'{"version":1,"subjects":[]}')

    original_open = io.open

    def locale_open(
        file: str | Path,
        mode: str = "r",
        *,
        encoding: str | None = None,
        newline: str | None = None,
    ) -> io.TextIOWrapper | io.BufferedWriter:
        if mode in ("ab", "wb"):
            return original_open(file, "ab" if mode == "ab" else "wb")
        return original_open(file, encoding=encoding or "cp1252", newline=newline)

    gha.event_payload.cache_clear()
    try:
        with (
            mock.patch.dict(os.environ, paths),
            mock.patch("builtins.open", locale_open),
        ):
            gha.add_system_path("বাংলা")
            gha.overwrite_job_summary("বাংলা")
            assert gha.event_payload() == payload
            assert gha.get_workflow_artifacts() == ()
    finally:
        gha.event_payload.cache_clear()
    assert Path(paths["GITHUB_PATH"]).read_bytes() == ("বাংলা" + os.linesep).encode(
        "utf-8"
    )
    assert Path(paths["GITHUB_STEP_SUMMARY"]).read_bytes() == "বাংলা\n".encode()


def test_event_payload_cache_contract_is_retained(tmp_path: Path) -> None:
    path = tmp_path / "event"
    path.write_text('{"message":"first"}', encoding="utf-8")
    gha.event_payload.cache_clear()
    try:
        with mock.patch.dict(os.environ, {"GITHUB_EVENT_PATH": str(path)}):
            first = gha.event_payload()
            first["message"] = "shared mutation"
            path.write_text('{"message":"second"}', encoding="utf-8")
            assert gha.event_payload()["message"] == "shared mutation"
            gha.event_payload.cache_clear()
            assert gha.event_payload()["message"] == "second"
    finally:
        gha.event_payload.cache_clear()


class BytesPath(os.PathLike[bytes]):
    def __fspath__(self) -> bytes:
        return b"binary-path"


@pytest.mark.parametrize("value", [BytesPath(), "bad\0path"])
def test_invalid_legacy_path_cannot_create_a_record(
    tmp_path: Path, value: BytesPath | str
) -> None:
    path = tmp_path / "path"
    with (
        mock.patch.dict(os.environ, {"GITHUB_PATH": str(path)}),
        pytest.raises((TypeError, ValueError)),
    ):
        gha.add_system_path(value)  # type: ignore[arg-type]  # Deliberately invalid text path.
    assert not path.exists()


def test_leading_bom_in_a_path_is_preserved(tmp_path: Path) -> None:
    path = tmp_path / "paths"
    entry = "\ufeffdirectory 世界"
    with mock.patch.dict(os.environ, {"GITHUB_PATH": str(path)}):
        gha.add_system_path(entry)
    assert path.read_text(encoding="utf-8-sig").splitlines() == ["", entry]
