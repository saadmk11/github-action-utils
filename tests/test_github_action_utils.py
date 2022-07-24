import json
import os
from typing import Any
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
def test__print_command(capfd: Any, test_input: Any, expected: str) -> None:
    gha_utils._print_command(*test_input)
    out, err = capfd.readouterr()
    assert out == expected


@pytest.mark.parametrize(
    "test_input,expected",
    [
        ("test", "test"),
        (1, "1"),
        (3.14, "3.14"),
        (["test", "test"], '["test", "test"]'),
        (
            (
                "test",
                "test",
            ),
            '["test", "test"]',
        ),
        ({"test": 3.14, "key": True}, '{"test": 3.14, "key": true}'),
    ],
)
def test__make_string(test_input: Any, expected: str) -> None:
    assert gha_utils._make_string(test_input) == expected


@pytest.mark.parametrize(
    "test_input,expected",
    [
        ("test", "test"),
        ("test\n", "test%0A"),
        ("%test", "%25test"),
        ("\rtest", "%0Dtest"),
    ],
)
def test__escape_data(test_input: str, expected: str) -> None:
    assert gha_utils._escape_data(test_input) == expected


@pytest.mark.parametrize(
    "test_input,expected",
    [
        ("test", "test"),
        ("test:", "test%3A"),
        ("test,", "test%2C"),
    ],
)
def test__escape_property(test_input: str, expected: str) -> None:
    assert gha_utils._escape_property(test_input) == expected


@pytest.mark.parametrize(
    "test_input,expected",
    [
        ("# test", "# test"),
        ("# test%0A", "# test\n"),
        ("- %25test", "- %test"),
        ("**%0Dtest**", "**\rtest**"),
    ],
)
def test__clean_markdown_string(test_input: str, expected: str) -> None:
    assert gha_utils._clean_markdown_string(test_input) == expected


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
def test__build_options_string(input_kwargs: Any, expected: str) -> None:
    assert gha_utils._build_options_string(**input_kwargs) == expected


@pytest.mark.parametrize(
    "test_input,expected",
    [
        ("test", "test\n"),
        ("test\n", "test%0A\n"),
        ("%test", "%25test\n"),
        ("\rtest", "%0Dtest\n"),
    ],
)
def test_echo(capfd: Any, test_input: str, expected: str) -> None:
    gha_utils.echo(test_input)
    out, err = capfd.readouterr()
    assert out == expected


@pytest.mark.parametrize(
    "test_input,expected",
    [
        ("test", "::debug ::test\n"),
        ("test\n", "::debug ::test%0A\n"),
        ("%test", "::debug ::%25test\n"),
        ("\rtest", "::debug ::%0Dtest\n"),
    ],
)
def test_debug(capfd: Any, test_input: str, expected: str) -> None:
    gha_utils.debug(test_input)
    out, err = capfd.readouterr()
    assert out == expected


@pytest.mark.parametrize(
    "input_args,input_kwargs,expected",
    [
        (
            ["test notice"],
            {
                "title": "test  \ntitle",
                "file": "abc.py",
                "col": 1,
                "end_column": 2,
                "line": 4,
                "end_line": 5,
            },
            "::notice title=test  %0Atitle,file=abc.py,col=1,endColumn=2,line=4,endLine=5::test notice\n",
        ),
        (["test notice"], {}, "::notice ::test notice\n"),
    ],
)
def test_notice(
    capfd: Any,
    input_args: Any,
    input_kwargs: Any,
    expected: str,
) -> None:
    gha_utils.notice(*input_args, **input_kwargs)
    out, err = capfd.readouterr()
    assert out == expected


@pytest.mark.parametrize(
    "input_args,input_kwargs,expected",
    [
        (
            ["test warning"],
            {
                "title": "test  \ntitle",
                "file": "abc.py",
                "col": 1,
                "end_column": 2,
                "line": 4,
                "end_line": 5,
            },
            "::warning title=test  %0Atitle,file=abc.py,col=1,endColumn=2,line=4,endLine=5::test warning\n",
        ),
        (["test warning"], {}, "::warning ::test warning\n"),
    ],
)
def test_warning(
    capfd: Any,
    input_args: Any,
    input_kwargs: Any,
    expected: str,
) -> None:
    gha_utils.warning(*input_args, **input_kwargs)
    out, err = capfd.readouterr()
    assert out == expected


@pytest.mark.parametrize(
    "input_args,input_kwargs,expected",
    [
        (
            ["test error"],
            {
                "title": "test  \ntitle",
                "file": "abc.py",
                "col": 1,
                "end_column": 2,
                "line": 4,
                "end_line": 5,
            },
            "::error title=test  %0Atitle,file=abc.py,col=1,endColumn=2,line=4,endLine=5::test error\n",
        ),
        (["test error"], {}, "::error ::test error\n"),
    ],
)
def test_error(
    capfd: Any,
    input_args: Any,
    input_kwargs: Any,
    expected: str,
) -> None:
    gha_utils.error(*input_args, **input_kwargs)
    out, err = capfd.readouterr()
    print(out)
    assert out == expected


@pytest.mark.parametrize(
    "input_args,expected",
    [
        (["abc", 123], "::set-output name=abc::123\n"),
        (["abc", "test"], "::set-output name=abc::test\n"),
        (["abc", {"k": "v"}], '::set-output name=abc::{"k": "v"}\n'),
    ],
)
def test_set_output(
    capfd: Any,
    input_args: Any,
    expected: str,
) -> None:
    gha_utils.set_output(*input_args)
    out, err = capfd.readouterr()
    print(out)
    assert out == expected


@pytest.mark.parametrize(
    "input_args,expected",
    [
        (["abc", 123], "::save-state name=abc::123\n"),
        (["abc", "test"], "::save-state name=abc::test\n"),
        (["abc", {"k": "v"}], '::save-state name=abc::{"k": "v"}\n'),
    ],
)
def test_save_state(
    capfd: Any,
    input_args: Any,
    expected: str,
) -> None:
    gha_utils.save_state(*input_args)
    out, err = capfd.readouterr()
    print(out)
    assert out == expected


@mock.patch.dict(os.environ, {"STATE_test_state": "test", "abc": "another test"})
def test_get_state() -> None:
    assert gha_utils.get_state("test_state") == "test"
    assert gha_utils.get_state("abc") is None


@mock.patch.dict(os.environ, {"INPUT_USERNAME": "test", "ANOTHER": "another test"})
def test_get_user_input() -> None:
    assert gha_utils.get_user_input("username") == "test"
    assert gha_utils.get_user_input("another") is None


@pytest.mark.parametrize(
    "test_input,expected",
    [
        ("test", "::group ::test\n"),
        ("test\n", "::group ::test%0A\n"),
        ("%test", "::group ::%25test\n"),
        ("\rtest", "::group ::%0Dtest\n"),
    ],
)
def test_start_group(capfd: Any, test_input: str, expected: str) -> None:
    gha_utils.start_group(test_input)
    out, err = capfd.readouterr()
    assert out == expected


def test_end_group(capfd: Any) -> None:
    gha_utils.end_group()
    out, err = capfd.readouterr()
    assert out == "::endgroup::\n"


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
def test_add_mask(capfd: Any, test_input: str, expected: str) -> None:
    gha_utils.add_mask(test_input)
    out, err = capfd.readouterr()
    assert out == expected


def test_begin_stop_commands(capfd: Any) -> None:
    gha_utils.begin_stop_commands(token="test token")
    out, err = capfd.readouterr()
    assert out == "::stop-commands ::test token\n"


def test_end_stop_commands(capfd: Any) -> None:
    gha_utils.end_stop_commands("test token")
    out, err = capfd.readouterr()
    assert out == "::test token::\n"


def test_set_env(tmpdir: Any) -> None:
    file = tmpdir.join("envfile")

    with mock.patch.dict(os.environ, {"GITHUB_ENV": file.strpath}):
        gha_utils.set_env("test", "test")
        gha_utils.set_env("another", 2)

    assert file.read() == (
        "test<<__ENV_DELIMITER__\n"
        "test\n__ENV_DELIMITER__\n"
        "another<<__ENV_DELIMITER__\n2\n"
        "__ENV_DELIMITER__\n"
    )


def test_get_workflow_environment_variables(tmpdir: Any) -> None:
    file = tmpdir.join("envfile")

    with mock.patch.dict(os.environ, {"GITHUB_ENV": file.strpath}):
        gha_utils.set_env("test", "test")
        gha_utils.set_env("another", 2)
        data = gha_utils.get_workflow_environment_variables()

    assert data == {"test": "test", "another": "2"}


@mock.patch.dict(os.environ, {"GITHUB_ACTOR": "test", "ANOTHER": "another test"})
def test_get_env() -> None:
    assert gha_utils.get_env("GITHUB_ACTOR") == "test"
    assert gha_utils.get_env("ANOTHER") == "another test"


def test_append_job_summary(tmpdir: Any) -> None:
    file = tmpdir.join("summary")

    with mock.patch.dict(os.environ, {"GITHUB_STEP_SUMMARY": file.strpath}):
        gha_utils.append_job_summary("# TEST")
        gha_utils.append_job_summary("- point 1")

    assert file.read() == "# TEST\n- point 1\n"


def test_overwrite_job_summary(tmpdir: Any) -> None:
    file = tmpdir.join("summary")

    with mock.patch.dict(os.environ, {"GITHUB_STEP_SUMMARY": file.strpath}):
        gha_utils.append_job_summary("# TEST")
        gha_utils.overwrite_job_summary("- point 1")

    assert file.read() == "- point 1\n"


def test_remove_job_summary(tmpdir: Any) -> None:
    file = tmpdir.join("summary")

    with mock.patch.dict(os.environ, {"GITHUB_STEP_SUMMARY": file.strpath}):
        gha_utils.remove_job_summary()

    assert os.path.isfile(file.strpath) is False


def test_add_system_path(tmpdir: Any) -> None:
    file = tmpdir.join("summary")

    with mock.patch.dict(os.environ, {"GITHUB_PATH": file.strpath}):
        gha_utils.add_system_path("usr/a/b")

    assert file.read() == "usr/a/b"


def test_event_payload(tmpdir: Any) -> None:
    file = tmpdir.join("summary")
    payload = {"test": "test"}
    file.write(json.dumps(payload))

    with mock.patch.dict(os.environ, {"GITHUB_EVENT_PATH": file.strpath}):
        data = gha_utils.event_payload()

    assert data == payload
