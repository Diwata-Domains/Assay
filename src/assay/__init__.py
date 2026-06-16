# SPDX-FileCopyrightText: 2024-2026 Shaznay Sison
# SPDX-License-Identifier: AGPL-3.0-only

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("assay-kit")
except PackageNotFoundError:
    __version__ = "0.0.0+dev"
