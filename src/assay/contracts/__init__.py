# SPDX-FileCopyrightText: 2024-2026 Shaznay Sison
# SPDX-License-Identifier: AGPL-3.0-only

"""Machine-readable agent contracts for Assay."""

from assay.contracts.manifest import (
    CONTRACT_VERSION,
    ENDPOINTS,
    TOOLS,
    build_manifest,
)

__all__ = ["CONTRACT_VERSION", "ENDPOINTS", "TOOLS", "build_manifest"]
