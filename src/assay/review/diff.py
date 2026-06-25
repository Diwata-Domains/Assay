# SPDX-FileCopyrightText: 2024-2026 Shaznay Sison
# SPDX-License-Identifier: AGPL-3.0-only

"""Diff gathering for the code-review runner.

Two input modes:
  - git refs: `git -C <repo> diff <base>..<head>` (optionally scoped to changed files).
  - explicit changed-file list: `git -C <repo> diff <base>..<head> -- <files>`, or, when no
    refs are given, a worktree diff of those paths (`git diff -- <files>`).

`gather_diff` returns the unified diff text. A non-zero git exit, missing repo, or missing git
binary raises `DiffGatherError` with the captured stderr so the caller can surface it.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Optional, Sequence


class DiffGatherError(Exception):
    """Raised when the diff cannot be gathered (bad refs, missing repo, git failure)."""


def _git_binary() -> str:
    found = shutil.which("git")
    if not found:
        raise DiffGatherError("git binary not found on PATH; cannot gather a diff for review.")
    return found


def _run_git(repo: Path, args: Sequence[str]) -> str:
    cmd = [_git_binary(), "-C", str(repo), *args]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
    except OSError as exc:
        raise DiffGatherError(f"failed to run git: {exc}") from exc
    if result.returncode != 0:
        raise DiffGatherError(
            f"git {' '.join(args)} failed (exit {result.returncode}): "
            f"{result.stderr.strip() or '<no stderr>'}"
        )
    return result.stdout


def gather_diff(
    repo: str | Path,
    base: Optional[str] = None,  # noqa: UP007
    head: Optional[str] = None,  # noqa: UP007
    changed_files: Optional[Sequence[str]] = None,  # noqa: UP007
) -> str:
    """Return the unified diff for the review.

    - With `base` and `head`: diff `base..head`, optionally scoped to `changed_files`.
    - With only `changed_files` (no refs): diff those paths in the worktree against HEAD.
    Raises DiffGatherError if the repo is missing or git fails. Returns "" for an empty diff.
    """
    repo_path = Path(repo)
    if not repo_path.exists():
        raise DiffGatherError(f"repo path does not exist: {repo_path}")

    args: list[str] = ["diff"]
    if base and head:
        args.append(f"{base}..{head}")
    elif base or head:
        raise DiffGatherError("both base and head refs must be provided together (or neither).")

    files = list(changed_files) if changed_files else []
    if files:
        args.append("--")
        args.extend(files)

    return _run_git(repo_path, args)
