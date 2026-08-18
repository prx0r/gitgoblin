from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LicenseDecision:
    spdx: str | None
    category: str
    recommendation: str


PERMISSIVE = {"MIT", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause", "ISC", "MPL-2.0"}
COPYLEFT = {"GPL-2.0", "GPL-3.0", "LGPL-2.1", "LGPL-3.0", "AGPL-3.0"}


def classify_license(spdx: str | None) -> LicenseDecision:
    if not spdx or spdx in {"NOASSERTION", "Other"}:
        return LicenseDecision(spdx, "unknown", "Do not copy code until the license is resolved; architecture ideas may be studied independently.")
    if spdx in PERMISSIVE:
        return LicenseDecision(spdx, "permissive", "Reusable subject to the license, notices, attribution, and dependency obligations.")
    if spdx in COPYLEFT:
        return LicenseDecision(spdx, "copyleft", "Prefer API/data consumption or clean-room reimplementation for a proprietary product; obtain legal review before incorporating code.")
    return LicenseDecision(spdx, "review", "Review the exact license terms before code reuse.")
