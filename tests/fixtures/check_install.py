"""Check a clean installed distribution without importing the source checkout."""

import sys
from importlib.metadata import version
from pathlib import Path

import github_action_utils as gha

location = Path(gha.__file__).resolve()
if not location.is_relative_to(Path("venv").resolve()):
    raise RuntimeError("Imported the checkout instead of the installed distribution")
if not location.with_name("py.typed").is_file():
    raise RuntimeError("Installed package is missing its typing marker")
if version("github-action-utils") != sys.argv[1]:
    raise RuntimeError("Installed version differs from the project metadata")
