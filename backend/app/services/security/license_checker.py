"""
Advanced license detection and compliance checking.
"""

import re
import logging
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


# =========================
# Enums
# =========================

class LicenseType(Enum):
    MIT = "MIT"
    APACHE_2 = "Apache-2.0"
    GPL_3 = "GPL-3.0"
    GPL_2 = "GPL-2.0"
    LGPL_3 = "LGPL-3.0"
    BSD_2 = "BSD-2-Clause"
    BSD_3 = "BSD-3-Clause"
    ISC = "ISC"
    UNLICENSE = "Unlicense"
    PROPRIETARY = "Proprietary"
    UNKNOWN = "Unknown"
    NO_LICENSE = "No License"


class LicenseCompatibility(Enum):
    COMPATIBLE = "compatible"
    CONDITIONAL = "conditional"
    INCOMPATIBLE = "incompatible"
    UNKNOWN = "unknown"


# =========================
# Dataclasses
# =========================

@dataclass
class LicenseInfo:
    type: LicenseType
    spdx_id: str
    file_path: str
    confidence: float
    text: Optional[str] = None
    detected_by: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DependencyLicense:
    name: str
    version: str
    license_type: LicenseType
    spdx_id: str
    file_path: Optional[str] = None
    source: str = "unknown"


# =========================
# Core Checker
# =========================

class LicenseChecker:
    """Advanced license checker with SPDX support."""

    LICENSE_PATTERNS = {
        LicenseType.MIT: [
            r"MIT\s+License",
            r"Permission is hereby granted, free of charge",
        ],
        LicenseType.APACHE_2: [
            r"Apache License\s+Version\s*2\.0",
            r"http://www.apache.org/licenses/LICENSE-2.0",
        ],
        LicenseType.GPL_3: [
            r"GNU GENERAL PUBLIC LICENSE\s+Version\s*3",
            r"GPLv3",
        ],
        LicenseType.GPL_2: [
            r"GNU GENERAL PUBLIC LICENSE\s+Version\s*2",
            r"GPLv2",
        ],
        LicenseType.BSD_3: [
            r"BSD 3-Clause License",
        ],
        LicenseType.BSD_2: [
            r"BSD 2-Clause License",
        ],
        LicenseType.ISC: [
            r"ISC License",
        ],
        LicenseType.UNLICENSE: [
            r"The Unlicense",
        ],
    }

    LICENSE_FILE_NAMES = {
        "LICENSE", "LICENSE.txt", "LICENSE.md",
        "COPYING", "NOTICE", "AUTHORS",
    }

    COMPATIBILITY_MATRIX = {
        LicenseType.MIT: {
            LicenseType.MIT: LicenseCompatibility.COMPATIBLE,
            LicenseType.APACHE_2: LicenseCompatibility.COMPATIBLE,
            LicenseType.GPL_3: LicenseCompatibility.INCOMPATIBLE,
        },
        LicenseType.APACHE_2: {
            LicenseType.MIT: LicenseCompatibility.COMPATIBLE,
            LicenseType.GPL_3: LicenseCompatibility.COMPATIBLE,
        },
        LicenseType.GPL_3: {
            LicenseType.APACHE_2: LicenseCompatibility.COMPATIBLE,
            LicenseType.MIT: LicenseCompatibility.INCOMPATIBLE,
        },
    }

    def __init__(self):
        self.license_cache: Dict[str, LicenseInfo] = {}

    # =========================
    # Public API
    # =========================

    def check_repository(self, repo_path: str) -> Dict[str, Any]:
        repo = Path(repo_path)

        detected = [
            info for lf in self._find_license_files(repo)
            if (info := self._analyze_license_file(lf))
        ]

        primary = self._determine_primary_license(detected)
        dependencies = self._check_dependencies(repo)
        compatibility = self._check_compatibility(primary, dependencies)

        return {
            "repository": str(repo),
            "primary_license": self._license_to_dict(primary),
            "detected_licenses": [self._license_to_dict(l) for l in detected],
            "dependency_licenses": [self._dependency_to_dict(d) for d in dependencies],
            "compatibility_issues": compatibility,
            "has_license_file": bool(detected),
            "has_proper_license": primary.type not in {LicenseType.NO_LICENSE, LicenseType.UNKNOWN},
            "recommendations": self._generate_recommendations(
                primary, detected, dependencies, compatibility
            ),
        }

    # =========================
    # Internal helpers
    # =========================

    def _find_license_files(self, repo: Path) -> List[Path]:
        files = []
        for name in self.LICENSE_FILE_NAMES:
            p = repo / name
            if p.exists():
                files.append(p)
        return files

    def _analyze_license_file(self, path: Path) -> Optional[LicenseInfo]:
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
            key = hashlib.sha256(content.encode()).hexdigest()

            if key in self.license_cache:
                return self.license_cache[key]

            matches = []
            for ltype, patterns in self.LICENSE_PATTERNS.items():
                for pat in patterns:
                    if re.search(pat, content, re.IGNORECASE):
                        matches.append(ltype)
                        break

            if matches:
                chosen = matches[0]
                info = LicenseInfo(
                    type=chosen,
                    spdx_id=chosen.value,
                    file_path=str(path),
                    confidence=min(1.0, len(matches) * 0.4),
                    text=content[:1000],
                    detected_by=["regex"],
                )
                self.license_cache[key] = info
                return info

            if "all rights reserved" in content.lower():
                return LicenseInfo(
                    type=LicenseType.PROPRIETARY,
                    spdx_id="LicenseRef-Proprietary",
                    file_path=str(path),
                    confidence=0.9,
                )

        except Exception as e:
            logger.error("License detection failed for %s: %s", path, e)

        return None

    def _check_dependencies(self, repo: Path) -> List[DependencyLicense]:
        deps = []
        req = repo / "requirements.txt"
        if req.exists():
            for line in req.read_text().splitlines():
                if line and not line.startswith("#"):
                    name = re.split(r"[<=>]", line)[0]
                    deps.append(
                        DependencyLicense(
                            name=name,
                            version="unknown",
                            license_type=LicenseType.UNKNOWN,
                            spdx_id="LicenseRef-Unknown",
                            source="pip",
                        )
                    )
        return deps

    def _determine_primary_license(self, licenses: List[LicenseInfo]) -> LicenseInfo:
        if not licenses:
            return LicenseInfo(
                type=LicenseType.NO_LICENSE,
                spdx_id="LicenseRef-NoLicense",
                file_path="",
                confidence=1.0,
                detected_by=["none"],
            )

        licenses.sort(
            key=lambda l: (l.confidence, l.type != LicenseType.UNKNOWN),
            reverse=True,
        )
        return licenses[0]

    def _check_compatibility(
        self,
        primary: LicenseInfo,
        deps: List[DependencyLicense],
    ) -> List[Dict[str, Any]]:
        issues = []
        for d in deps:
            comp = self.COMPATIBILITY_MATRIX.get(primary.type, {}).get(
                d.license_type, LicenseCompatibility.UNKNOWN
            )
            if comp == LicenseCompatibility.INCOMPATIBLE:
                issues.append({
                    "dependency": d.name,
                    "severity": "high",
                    "issue": "incompatible license",
                })
        return issues

    def _generate_recommendations(
        self,
        primary: LicenseInfo,
        detected: List[LicenseInfo],
        deps: List[DependencyLicense],
        issues: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        recs = []
        if not detected:
            recs.append({
                "priority": "high",
                "action": "Add LICENSE file",
            })
        if issues:
            recs.append({
                "priority": "critical",
                "action": "Resolve license conflicts",
            })
        return recs

    def _license_to_dict(self, lic: LicenseInfo) -> Dict[str, Any]:
        return {
            "type": lic.type.value,
            "spdx_id": lic.spdx_id,
            "file_path": lic.file_path,
            "confidence": lic.confidence,
        }

    def _dependency_to_dict(self, dep: DependencyLicense) -> Dict[str, Any]:
        return {
            "name": dep.name,
            "version": dep.version,
            "license_type": dep.license_type.value,
            "spdx_id": dep.spdx_id,
            "source": dep.source,
        }


# =========================
# Convenience API
# =========================

def check_license(repo_path: str) -> Dict[str, Any]:
    return LicenseChecker().check_repository(repo_path)


def get_license_type(repo_path: str) -> str:
    result = check_license(repo_path)
    primary = result.get("primary_license")
    return primary["type"] if primary else "No license found"


def check_license_compatibility(license_a: str, license_b: str) -> Dict[str, Any]:
    try:
        a = LicenseType(license_a)
        b = LicenseType(license_b)
    except ValueError:
        return {"compatibility": "unknown", "can_combine": False}

    checker = LicenseChecker()
    comp = checker.COMPATIBILITY_MATRIX.get(a, {}).get(b, LicenseCompatibility.UNKNOWN)

    return {
        "license_a": license_a,
        "license_b": license_b,
        "compatibility": comp.value,
        "can_combine": comp != LicenseCompatibility.INCOMPATIBLE,
    }
