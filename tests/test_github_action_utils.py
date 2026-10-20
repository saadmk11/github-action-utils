import os
from pathlib import Path
from unittest import mock

import pytest

import github_action_utils as gha_utils


@pytest.mark.parametrize(
    "test_input,expected",
    [
        (
            ["debug", "test debug", "test=1,test2=2"],
            "::debug test=1,test2=2::test debug\n",
        ),
        (["debug", "test debug", None], "::debug ::test debug\n"),
    ],
)
def test__print_command(
    capfd: pytest.CaptureFixture[str],
    test_input: tuple[gha_utils.CommandTypes, str, str | None],
    expected: str,
) -> None:
    gha_utils._print_command(*test_input)
    out, err = capfd.readouterr()
    assert out == expected


@pytest.mark.parametrize(
    "test_input,expected",
    [
        ("test_string", "testString"),
        ("String_New", "stringNew"),
        ("One_two_Three", "oneTwoThree"),
    ],
)
def test__to_camel_case(test_input: str, expected: str) -> None:
    assert gha_utils._to_camel_case(test_input) == expected


@pytest.mark.parametrize(
    "input_kwargs,expected",
    [
        (
            {
                "title": "test  \ntitle",
                "file": "abc.py",
                "col": 1,
                "end_column": 2,
                "line": 4,
                "end_line": 5,
            },
            "title=test  %0Atitle,file=abc.py,col=1,endColumn=2,line=4,endLine=5",
        ),
        ({"name": "test-name"}, "name=test-name"),
        ({}, ""),
    ],
)
def test__build_options_string(
    input_kwargs: dict[str, str | int], expected: str
) -> None:
    assert gha_utils._build_options_string(**input_kwargs) == expected


@pytest.mark.parametrize(
    "test_input,expected",
    [
        ("test", "test\n"),
        ("test\n", "test\n\n"),
        ("%test", "%test\n"),
        ("\rtest", "\rtest\n"),
    ],
)
def test_echo(
    capfd: pytest.CaptureFixture[str], test_input: str, expected: str
) -> None:
    gha_utils.echo(test_input)
    out, err = capfd.readouterr()
    assert out == expected


def test_set_output_deprecation_warning(tmp_path: Path) -> None:
    file = tmp_path.joinpath("output_file")

    with pytest.deprecated_call():
        with mock.patch.dict(os.environ, {"GITHUB_OUTPUT": str(file)}):
            gha_utils.set_output("test", "test", use_subprocess=True)


def test_save_state_deprecation_warning(tmp_path: Path) -> None:
    file = tmp_path.joinpath("state_file")

    with pytest.deprecated_call():
        with mock.patch.dict(os.environ, {"GITHUB_STATE": str(file)}):
            gha_utils.save_state("test", "test", use_subprocess=True)


@mock.patch.dict(os.environ, {"STATE_test_state": "test", "abc": "another test"})
def test_get_state() -> None:
    assert gha_utils.get_state("test_state") == "test"
    assert gha_utils.get_state("abc") is None


@pytest.mark.parametrize(
    "test_input,expected",
    [
        ("test", "::add-mask ::test\n"),
        (1, "::add-mask ::1\n"),
        (3.14, "::add-mask ::3.14\n"),
        (["test", "test"], '::add-mask ::["test", "test"]\n'),
        (
            (
                "test",
                "test",
            ),
            '::add-mask ::["test", "test"]\n',
        ),
        ({"test": 3.14, "key": True}, '::add-mask ::{"test": 3.14, "key": true}\n'),
    ],
)
def test_add_mask(
    capfd: pytest.CaptureFixture[str], test_input: str, expected: str
) -> None:
    gha_utils.add_mask(test_input)
    out, err = capfd.readouterr()
    assert out == expected


def test_remove_job_summary(tmp_path: Path) -> None:
    file = tmp_path.joinpath("summary")

    with mock.patch.dict(os.environ, {"GITHUB_STEP_SUMMARY": str(file)}):
        gha_utils.remove_job_summary()

    assert os.path.isfile(str(file)) is False
