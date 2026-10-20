"""Independent decoder for the documented delimited file-command format."""

import os


def parse_records(data: bytes) -> dict[str, str]:
    """Decode writer results without calling the library's environment reader."""
    newline = os.linesep.encode("ascii")
    records: dict[str, str] = {}
    position = 0
    while position < len(data):
        header_end = data.index(newline, position)
        name, delimiter = data[position:header_end].split(b"<<", 1)
        start = header_end + len(newline)
        end = data.index(newline + delimiter + newline, start)
        records[name.decode("utf-8")] = data[start:end].decode("utf-8")
        position = end + len(newline + delimiter + newline)
    return records
