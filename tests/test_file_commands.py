"""Behavioral regressions for GitHub Actions file commands and local lookup."""

import json
import os
import uuid
from collections.abc import Callable
from pathlib import Path
from unittest import mock

import pytest

import github_action_utils as gha
from github_action_utils._files import _build_file_input

from ._types import FileWriter, LegacyValue
from .file_command_helpers import parse_records


@pytest.mark.parametrize(
    "value",
    [
        "hello\nworld",
        "100%",
        "%0A %0D %25",
        "héllo 世界",
        "",
        "  padded value  ",
        "\nfirst\n\nlast\n",
        "carriage\rreturn\r",
        "windows\r\nlines\r\n",
        "vertical\vtab\u2028separator",
        "__ENV_DELIMITER__\nOTHER=value",
        42,
        3.14,
        None,
        True,
        ["first", "second"],
        ("first", "second"),
        {"enabled": True, "count": 2},
    ],
)
def test_file_values_round_trip(
    tmp_path: Path,
    value: LegacyValue,
) -> None:
    path = tmp_path / "commands"
    with mock.patch.dict(os.environ, {"GITHUB_OUTPUT": str(path)}):
        gha.set_output("result", value)
    expected = (
        json.dumps(value) if isinstance(value, (list, tuple, dict)) else str(value)
    )
    assert parse_records(path.read_bytes()) == {"result": expected}


def test_delimiter_collision_does_not_inject_records(tmp_path: Path) -> None:
    collision = uuid.UUID(int=0)
    replacement = uuid.UUID(int=1)
    value = f"first\nghadelimiter_{collision.hex}\nINJECTED=value"
    with mock.patch(
        "github_action_utils.uuid.uuid4", side_effect=[collision, replacement]
    ):
        data = _build_file_input("result", value)
    assert parse_records(data) == {"result": value}
    path = tmp_path / "commands"
    path.write_bytes(data)
    with mock.patch.dict(os.environ, {"GITHUB_ENV": str(path)}):
        assert gha.get_workflow_environment_variables() == {"result": value}


def test_delimiter_collision_with_name_is_regenerated() -> None:
    collision = uuid.UUID(int=0)
    replacement = uuid.UUID(int=1)
    name = f"ghadelimiter_{collision.hex}"
    with mock.patch(
        "github_action_utils.uuid.uuid4", side_effect=[collision, replacement]
    ):
        data = _build_file_input(name, "value")
    assert parse_records(data) == {name: "value"}
    assert data.split(os.linesep.encode(), 1)[0].endswith(replacement.hex.encode())


def test_file_names_are_not_stdout_properties() -> None:
    assert parse_records(_build_file_input("result:part,100%", "value")) == {
        "result:part,100%": "value"
    }


@pytest.mark.parametrize(
    "name", ["", "bad=name", "bad<<name", "bad\rname", "bad\nname", "bad\0name"]
)
@pytest.mark.parametrize(
    "writer,variable",
    [
        (gha.set_output, "GITHUB_OUTPUT"),
        (gha.save_state, "GITHUB_STATE"),
        (gha.set_env, "GITHUB_ENV"),
    ],
)
def test_invalid_names_do_not_touch_the_file(
    tmp_path: Path, name: str, writer: Callable[[str, LegacyValue], None], variable: str
) -> None:
    path = tmp_path / "commands"
    with mock.patch.dict(os.environ, {variable: str(path)}):
        with pytest.raises(ValueError, match="names"):
            writer(name, "value")
        assert not path.exists()
        path.write_bytes(b"unchanged")
        with pytest.raises(ValueError, match="names"):
            writer(name, "value")
    assert path.read_bytes() == b"unchanged"


def test_non_string_name_keeps_legacy_conversion(tmp_path: Path) -> None:
    path = tmp_path / "commands"
    with mock.patch.dict(os.environ, {"GITHUB_OUTPUT": str(path)}):
        gha.set_output(123, "value")  # type: ignore[arg-type]  # Check legacy name conversion.
    assert parse_records(path.read_bytes()) == {"123": "value"}


def test_each_record_has_its_own_delimiter() -> None:
    first = _build_file_input("result", "first")
    second = _build_file_input("result", "second")
    assert first.splitlines()[0] != second.splitlines()[0]
    assert parse_records(first + second) == {"result": "second"}


@pytest.mark.parametrize(
    "value",
    ["hello\nworld", "  padded  \n\n", "", "100% %0A", "héllo\r\nworld\r"],
)
def test_environment_reader_preserves_written_values(
    tmp_path: Path, value: str
) -> None:
    path = tmp_path / "commands"
    with mock.patch.dict(os.environ, {"GITHUB_ENV": str(path)}):
        gha.set_env("EXAMPLE", value)
        assert gha.get_workflow_environment_variables() == {"EXAMPLE": value}


def test_reader_accepts_mixed_records_and_legacy_delimiters(tmp_path: Path) -> None:
    path = tmp_path / "commands"
    path.write_bytes(
        b"\nSIMPLE=first=second<<literal\n"
        b"LEGACY<<__ENV_DELIMITER__\n  first\nsecond  \n__ENV_DELIMITER__\n"
        b"EMPTY=\nSIMPLE=last\nRAW=%0A %25\n"
        b"BLOCK<<arbitrary-delimiter\nvalue\narbitrary-delimiter"
    )
    with mock.patch.dict(os.environ, {"GITHUB_ENV": str(path)}):
        assert gha.get_workflow_environment_variables() == {
            "SIMPLE": "last",
            "LEGACY": "  first\nsecond  ",
            "EMPTY": "",
            "RAW": "%0A %25",
            "BLOCK": "value",
        }


def test_empty_environment_file(tmp_path: Path) -> None:
    path = tmp_path / "commands"
    path.touch()
    with mock.patch.dict(os.environ, {"GITHUB_ENV": str(path)}):
        assert gha.get_workflow_environment_variables() == {}


@pytest.mark.parametrize(
    "data",
    [
        "not-a-record\n",
        "=sensitive-value\n",
        "<<EOF\nsensitive-value\nEOF\n",
        "NAME<<\n",
        "NAME<<EOF\nsensitive-value\n",
        "NAME<<EOF\nsensitive-value",
    ],
)
def test_malformed_records_raise_without_exposing_values(
    tmp_path: Path, data: str
) -> None:
    path = tmp_path / "commands"
    path.write_bytes(data.encode("utf-8"))
    with mock.patch.dict(os.environ, {"GITHUB_ENV": str(path)}):
        with pytest.raises(ValueError, match="Invalid environment record") as error:
            gha.get_workflow_environment_variables()
    assert "sensitive-value" not in str(error.value)


@pytest.mark.parametrize("environment", [{}, {"GITHUB_ENV": ""}])
def test_missing_local_environment(environment: dict[str, str]) -> None:
    with mock.patch.dict(os.environ, environment, clear=True):
        assert gha.get_workflow_environment_variables() == {}
        assert gha.get_env("MISSING") is None


def test_missing_configured_file_is_not_silenced(tmp_path: Path) -> None:
    with mock.patch.dict(os.environ, {"GITHUB_ENV": str(tmp_path / "missing")}):
        with pytest.raises(FileNotFoundError):
            gha.get_workflow_environment_variables()


def test_process_environment_precedes_pending_values(tmp_path: Path) -> None:
    path = tmp_path / "commands"
    path.write_bytes(b"EMPTY=pending\nEXAMPLE=pending\nONLY_FILE=pending\n")
    with mock.patch.dict(
        os.environ,
        {"GITHUB_ENV": str(path), "EMPTY": "", "EXAMPLE": "process"},
        clear=True,
    ):
        assert gha.get_env("EMPTY") == ""
        assert gha.get_env("EXAMPLE") == "process"
        assert gha.get_env("ONLY_FILE") == "pending"
        assert gha.get_env("MISSING") is None


@pytest.mark.parametrize(
    "writer,variable",
    [(gha.set_output, "GITHUB_OUTPUT"), (gha.save_state, "GITHUB_STATE")],
)
def test_false_subprocess_argument_still_warns(
    tmp_path: Path, writer: FileWriter, variable: str
) -> None:
    with mock.patch.dict(os.environ, {variable: str(tmp_path / "commands")}):
        with pytest.deprecated_call():
            writer("name", "value", use_subprocess=False)


@pytest.mark.parametrize("use_subprocess", [False, True])
def test_context_managers_clean_up_after_errors(
    capfd: pytest.CaptureFixture[str], use_subprocess: bool
) -> None:
    with pytest.raises(RuntimeError, match="failure"):
        with gha.group("example", use_subprocess=use_subprocess):
            raise RuntimeError("failure")
    assert capfd.readouterr().out.endswith("::endgroup::\n")
    with pytest.raises(RuntimeError, match="failure"):
        with gha.stop_commands("example-token", use_subprocess=use_subprocess):
            raise RuntimeError("failure")
    assert capfd.readouterr().out.endswith("::example-token::\n")


@pytest.mark.parametrize("platform,newline", [("posix", "\n"), ("nt", "\r\n")])
def test_native_framing_preserves_carriage_returns(
    tmp_path: Path, platform: str, newline: str
) -> None:
    path = str(tmp_path / "commands")
    expected = "first\r\nsecond\r\n\r"
    with mock.patch.dict(os.environ, {"GITHUB_ENV": path}):
        with (
            mock.patch("github_action_utils.os.name", platform),
            mock.patch("github_action_utils.os.linesep", newline),
        ):
            gha.set_env("EXAMPLE", expected)
            actual = gha.get_workflow_environment_variables()
    assert actual == {"EXAMPLE": expected}


@pytest.mark.parametrize(
    "message", ["-n", "backslash\\n", "héllo 世界", "quotes ' \" $() `literal`"]
)
def test_subprocess_console_output_is_literal(
    capfd: pytest.CaptureFixture[str], message: str
) -> None:
    gha.echo(message, use_subprocess=True)
    assert capfd.readouterr().out == message + "\n"


def test_leading_bom_in_a_record_name_is_not_a_file_signature(tmp_path: Path) -> None:
    path = tmp_path / "commands"
    with mock.patch.dict(os.environ, {"GITHUB_ENV": str(path)}):
        gha.set_env("\ufeffNAME", "世界")
        assert gha.get_workflow_environment_variables() == {"\ufeffNAME": "世界"}
        assert gha.get_env("\ufeffNAME") == "世界"
    assert not path.read_bytes().startswith(b"\xef\xbb\xbf")


@pytest.mark.parametrize(
    "variable,writer",
    [
        ("GITHUB_OUTPUT", gha.set_output),
        ("GITHUB_STATE", gha.save_state),
        ("GITHUB_ENV", gha.set_env),
    ],
)
def test_file_writer_destinations(
    tmp_path: Path, variable: str, writer: Callable[[str, LegacyValue], None]
) -> None:
    path = tmp_path / "commands"
    value = "first\n%0A\n世界"
    with mock.patch.dict(os.environ, {variable: str(path)}):
        writer("result", value)
    assert parse_records(path.read_bytes()) == {"result": value}
