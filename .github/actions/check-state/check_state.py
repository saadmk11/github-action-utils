"""Verify action state in main/post hooks; local actions do not support pre."""

import sys
from collections.abc import Sequence

import github_action_utils as gha

MAIN_VALUE = "from main\n100% %0A\nhéllo 世界\n"


def main(argv: Sequence[str] | None = None) -> None:
    """Write main state or assert the exact state received by the post hook."""
    arguments = list(sys.argv[1:] if argv is None else argv)
    match arguments:
        case ["post"]:
            assert gha.get_state("from_main") == MAIN_VALUE
            print("Post hook received exact main state")
        case ["main"]:
            gha.save_state("from_main", MAIN_VALUE)
            print("Main hook saved state")
        case _:
            raise ValueError("Expected main or post")


if __name__ == "__main__":
    main()
