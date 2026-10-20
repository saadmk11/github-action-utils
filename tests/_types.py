"""Callback types shared by parameterized tests."""

from typing import Protocol, TypedDict

from github_action_utils._serialization import JSONValue

LegacyValue = JSONValue | tuple[str, ...]


class FileWriter(Protocol):
    def __call__(
        self, name: str, value: LegacyValue, use_subprocess: bool | None = None
    ) -> None: ...


class InputReader(Protocol):
    def __call__(
        self, name: str, *, required: bool = False, trim_whitespace: bool = False
    ) -> str | bool | list[str] | None: ...


class MatcherOptions(TypedDict, total=False):
    owner: str
    path: str
