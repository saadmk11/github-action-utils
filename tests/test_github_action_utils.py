from typing import Any

import pytest

import github_action_utils as autils


@pytest.mark.parametrize(
    "test_input,expected",
    [
        (["endgroup", ""], "::endgroup::\n"),
        (
            ["debug", "test debug", "test=1,test2=2"],
            "::debug test=1,test2=2::test debug\n",
        ),
        (["debug", "test debug", None], "::debug ::test debug\n"),
    ],
)
def test__print_command(capfd: Any, test_input: Any, expected: str) -> None:
    autils._print_command(*test_input)
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
    assert autils._make_string(test_input) == expected


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
    assert autils._escape_data(test_input) == expected


@pytest.mark.parametrize(
    "test_input,expected",
    [
        ("test", "test"),
        ("test:", "test%3A"),
        ("test,", "test%2C"),
    ],
)
def test__escape_property(test_input: str, expected: str) -> None:
    assert autils._escape_property(test_input) == expected


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
    assert autils._clean_markdown_string(test_input) == expected


@pytest.mark.parametrize(
    "test_input,expected",
    [
        ("test_string", "testString"),
        ("String_New", "stringNew"),
        ("One_two_Three", "oneTwoThree"),
    ],
)
def test__to_camel_case(test_input: str, expected: str) -> None:
    assert autils._to_camel_case(test_input) == expected


@pytest.mark.parametrize(
    "input_args,input_kwargs,expected",
    [
        (
            ["error", "test debug"],
            {
                "title": "test  \ntitle",
                "file": "abc.py",
                "col": 1,
                "end_column": 2,
                "line": 4,
                "end_line": 5,
            },
            "::error title=test  %0Atitle,file=abc.py,col=1,endColumn=2,line=4,endLine=5::test debug\n",
        ),
        (["error", "test debug"], {}, "::error ::test debug\n"),
        (["debug", "test debug"], {}, "::debug ::test debug\n"),
    ],
)
def test__print_log_message(
    capfd: Any,
    input_args: Any,
    input_kwargs: Any,
    expected: str,
) -> None:
    autils._print_log_message(*input_args, **input_kwargs)
    out, err = capfd.readouterr()
    assert out == expected
