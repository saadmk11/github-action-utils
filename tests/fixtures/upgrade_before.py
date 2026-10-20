"""Capture the published 1.1.0 contract in an isolated installation."""

import inspect
import json
import pickle
from pathlib import Path

import github_action_utils as g

if Path(g.__file__).name != "github_action_utils.py":
    raise AssertionError("The baseline must import the published single module")
Path("old-module-path.txt").write_text(g.__file__, encoding="utf-8")
signatures = {}
for name, value in vars(g).items():
    if (
        not name.startswith("_")
        and callable(value)
        and getattr(value, "__module__", None) == g.__name__
    ):
        signatures[name] = [
            (p.name, p.kind.name, repr(p.default))
            for p in inspect.signature(value).parameters.values()
        ]
Path("old-signatures.json").write_text(json.dumps(signatures), encoding="utf-8")
Path("old-functions.pickle").write_bytes(
    pickle.dumps(
        {name: getattr(g, name) for name in ("get_user_input", "event_payload")}
    )
)
