#!/usr/bin/env python3
"""Reject commit messages that don't follow Conventional Commits.

Used as a pre-commit `commit-msg` hook. The hook framework passes the path to the
commit message file as the first argument.

Format:  <type>[optional scope][!]: <description>
Example: feat(db): add category budgets
"""

from __future__ import annotations

import re
import sys

TYPES = "feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert"
PATTERN = re.compile(rf"^(?:{TYPES})(?:\([\w./-]+\))?!?: .+")


def main() -> int:
    if len(sys.argv) < 2:
        return 0
    with open(sys.argv[1], encoding="utf-8") as f:
        subject = f.readline().strip()

    # Let git's own merge/revert/fixup subjects through.
    if subject.startswith(("Merge ", "Revert ", "fixup!", "squash!")):
        return 0

    if not PATTERN.match(subject):
        print("\n✗ Commit message must follow Conventional Commits:")
        print("    <type>[optional scope]: <description>")
        print("    e.g.  feat(db): add category budgets")
        print(f"    types: {TYPES.replace('|', ', ')}")
        print(f"    got:  {subject!r}\n")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
