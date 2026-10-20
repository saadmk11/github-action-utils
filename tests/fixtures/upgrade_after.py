"""Verify the published 1.1.0 contract in an isolated installation."""

import inspect
import json
import pickle
from pathlib import Path

import github_action_utils as g

if Path(g.__file__).name != "__init__.py":
    raise AssertionError("The upgrade must import the new package")
if Path(Path("old-module-path.txt").read_text(encoding="utf-8")).exists():
    raise AssertionError("The upgrade left the old single module installed")
signatures = json.loads(Path("old-signatures.json").read_text(encoding="utf-8"))
for name, original in signatures.items():
    parameters = list(inspect.signature(getattr(g, name)).parameters.values())
    current = [
        (p.name, p.kind.name, repr(p.default)) for p in parameters[: len(original)]
    ]
    if current != [tuple(p) for p in original]:
        raise AssertionError(name)
    if any(p.default is inspect.Parameter.empty for p in parameters[len(original) :]):
        raise AssertionError(name)
for name, function in pickle.loads(Path("old-functions.pickle").read_bytes()).items():
    if function is not getattr(g, name):
        raise AssertionError(name)
namespace: dict[str, object] = {}
exec("from github_action_utils import *", namespace)
for name in signatures:
    if name not in namespace or not hasattr(g, name):
        raise AssertionError(name)
if "vars" in namespace:
    raise AssertionError("Wildcard imports must preserve the built-in vars function")
print(
    f"Published 1.1.0 upgrade passed: {len(signatures)} public call signatures, old pickles, and module cleanup."
)
