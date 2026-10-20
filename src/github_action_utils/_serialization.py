"""Escape text for stdout workflow commands."""

from typing import TypeAlias

JSONValue: TypeAlias = (
    None | bool | int | float | str | list["JSONValue"] | dict[str, "JSONValue"]
)


def escape_data(data: str) -> str:
    """Escape percent first so literal escape-looking text is decoded once."""
    return data.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def escape_property(data: str) -> str:
    """Also escape the separators used in command properties."""
    return escape_data(data).replace(":", "%3A").replace(",", "%2C")
