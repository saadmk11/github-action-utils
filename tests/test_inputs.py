"""Public input contracts: missing values, whitespace, and explicit parsing."""

import os
from unittest import mock

import pytest

import github_action_utils as gha

from ._types import InputReader


def test_raw_input_defaults_and_name_normalization() -> None:
    with mock.patch.dict(
        os.environ,
        {"INPUT_MY-NAME": "  value  ", "INPUT_OLD_NAME": "legacy", "INPUT_EMPTY": ""},
        clear=True,
    ):
        assert gha.get_user_input("my-name") == "  value  "
        assert gha.get_user_input("my-name", trim_whitespace=True) == "value"
        assert gha.get_user_input("old name") == "legacy"
        assert gha.get_user_input("empty") == ""
        assert gha.get_user_input("missing") is None


@pytest.mark.parametrize("value", [None, "", " \r\n "])
@pytest.mark.parametrize(
    "helper", [gha.get_user_input, gha.get_boolean_input, gha.get_multiline_input]
)
def test_required_inputs(value: str | None, helper: InputReader) -> None:
    environment = {} if value is None else {"INPUT_NAME": value}
    with mock.patch.dict(os.environ, environment, clear=True):
        with pytest.raises(ValueError, match="input"):
            helper("name", required=True, trim_whitespace=True)


@pytest.mark.parametrize(
    "value,expected",
    [
        ("true", True),
        ("True", True),
        ("TRUE", True),
        ("false", False),
        ("False", False),
        ("FALSE", False),
        (" \ttrue\n", True),
        (" false ", False),
    ],
)
def test_boolean_inputs(value: str, expected: bool) -> None:
    with mock.patch.dict(os.environ, {"INPUT_NAME": value}, clear=True):
        assert gha.get_boolean_input("name") is expected


@pytest.mark.parametrize(
    "value", ["", "0", "1", "yes", "no", "tRuE", "sensitive-value"]
)
def test_invalid_boolean_does_not_expose_value(value: str) -> None:
    with mock.patch.dict(os.environ, {"INPUT_NAME": value}, clear=True):
        with pytest.raises(ValueError, match="name") as error:
            gha.get_boolean_input("name")
    assert str(error.value) == "Input must be a YAML 1.2 boolean: name"


def test_boolean_whitespace_policy() -> None:
    with mock.patch.dict(os.environ, {"INPUT_NAME": " true "}, clear=True):
        with pytest.raises(ValueError):
            gha.get_boolean_input("name", trim_whitespace=False)


def test_optional_missing_typed_inputs() -> None:
    with mock.patch.dict(os.environ, {}, clear=True):
        assert gha.get_boolean_input("name") is None
        assert gha.get_multiline_input("name") == []


@pytest.mark.parametrize(
    "trim,keep,expected",
    [
        (True, False, ["first", "second"]),
        (True, True, ["", "first", "", "second", ""]),
        (False, False, [" first ", "  ", "second"]),
        (False, True, ["", " first ", "  ", "second", ""]),
    ],
)
def test_multiline_input_policies(trim: bool, keep: bool, expected: list[str]) -> None:
    with mock.patch.dict(
        os.environ, {"INPUT_NAME": "\r\n first \r\n  \r\nsecond\r\n"}, clear=True
    ):
        assert (
            gha.get_multiline_input("name", trim_whitespace=trim, keep_empty_lines=keep)
            == expected
        )


def test_empty_multiline_and_required_retained_lines() -> None:
    with mock.patch.dict(os.environ, {"INPUT_NAME": ""}, clear=True):
        assert gha.get_multiline_input("name") == []
        assert gha.get_multiline_input("name", keep_empty_lines=True) == [""]
    with mock.patch.dict(os.environ, {"INPUT_NAME": "\n \n"}, clear=True):
        with pytest.raises(ValueError):
            gha.get_multiline_input("name", required=True, keep_empty_lines=True)
        assert gha.get_user_input("name", required=True) == "\n \n"


@pytest.mark.parametrize("name", [123, None])
def test_invalid_input_names(name: int | None) -> None:
    with pytest.raises((TypeError, ValueError)):
        gha.get_user_input(name)  # type: ignore[arg-type]  # Deliberately invalid runtime input.
