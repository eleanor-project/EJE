"""
Version Compatibility Checker for EJE

Checks compatibility between different versions of EJE components,
identifies upgrade paths, and validates migration requirements.
"""

from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from packaging import version
import json


@dataclass
class VersionRange:
    """Represents a range of compatible versions."""
    min_version: str
    max_version: Optional[str] = None

    def contains(self, ver: str) -> bool:
        """Check if version is in range."""
        v = version.parse(ver)
        min_v = version.parse(self.min_version)

        if v < min_v:
            return False

        if self.max_version:
            max_v = version.parse(self.max_version)
            if v > max_v:
                return False

        return True


@dataclass
class CompatibilityResult:
    """Result of compatibility check."""
    compatible: bool
    current_version: str
    target_version: str
    migration_path: List[str]
    breaking_changes: List[str]
    recommendations: List[str]
    risk_level: str


class VersionCompatibilityChecker:
    """
    Checks version compatibility and generates upgrade paths.
    """

    # Version compatibility matrix
    COMPATIBILITY_MATRIX = {
        "1.0.0": {
            "compatible_with": ["1.0.1", "1.1.0"],
            "breaking_in": ["2.0.0"]
        },
        "1.1.0": {
            "compatible_with": ["1.1.1", "1.2.0"],
            "breaking_in": ["2.0.0"]
        },
        "1.2.0": {
            "compatible_with": ["1.2.1", "1.3.0"],
            "breaking_in": ["2.0.0"]
        },
        "1.3.0": {
            "compatible_with": ["1.3.1", "1.4.0"],
            "breaking_in": ["2.0.0"]
        },
        "1.4.0": {
            "compatible_with": ["1.4.1", "1.5.0"],
            "breaking_in": ["2.0.0"]
        }
    }

    # Known breaking changes by version
    BREAKING_CHANGES = {
        "2.0.0": [
            "Precedent schema changed from v1 to v2",
            "API endpoints renamed (/evaluate → /v2/evaluate)",
            "Config format changed (YAML restructure)"
        ],
        "1.4.0": [
            "Encrypted audit logs added (new env vars required)"
        ]
    }

    def check_compatibility(
        self,
        current_ver: str,
        target_ver: str
    ) -> CompatibilityResult:
        """
        Check compatibility between two versions.

        Args:
            current_ver: Current version string
            target_ver: Target version string

        Returns:
            CompatibilityResult with upgrade path and recommendations
        """
        curr = version.parse(current_ver)
        targ = version.parse(target_ver)

        # Same version
        if curr == targ:
            return CompatibilityResult(
                compatible=True,
                current_version=current_ver,
                target_version=target_ver,
                migration_path=[],
                breaking_changes=[],
                recommendations=["Already at target version"],
                risk_level="NONE"
            )

        # Downgrade
        if curr > targ:
            return CompatibilityResult(
                compatible=False,
                current_version=current_ver,
                target_version=target_ver,
                migration_path=[],
                breaking_changes=["Downgrade not supported"],
                recommendations=["Cannot downgrade - data loss risk"],
                risk_level="CRITICAL"
            )

        # Check for direct compatibility
        if self._is_directly_compatible(current_ver, target_ver):
            return CompatibilityResult(
                compatible=True,
                current_version=current_ver,
                target_version=target_ver,
                migration_path=[current_ver, target_ver],
                breaking_changes=[],
                recommendations=["Direct upgrade possible"],
                risk_level="LOW"
            )

        # Find upgrade path
        path = self._find_upgrade_path(current_ver, target_ver)

        if not path:
            return CompatibilityResult(
                compatible=False,
                current_version=current_ver,
                target_version=target_ver,
                migration_path=[],
                breaking_changes=["No upgrade path found"],
                recommendations=["Manual migration required"],
                risk_level="CRITICAL"
            )

        # Collect breaking changes along path
        breaking = []
        for v in path[1:]:
            if v in self.BREAKING_CHANGES:
                breaking.extend(self.BREAKING_CHANGES[v])

        # Generate recommendations
        recommendations = self._generate_upgrade_recommendations(path, breaking)

        # Assess risk
        risk = self._assess_upgrade_risk(path, breaking)

        return CompatibilityResult(
            compatible=True,
            current_version=current_ver,
            target_version=target_ver,
            migration_path=path,
            breaking_changes=breaking,
            recommendations=recommendations,
            risk_level=risk
        )

    def _is_directly_compatible(self, from_ver: str, to_ver: str) -> bool:
        """Check if versions are directly compatible."""
        if from_ver in self.COMPATIBILITY_MATRIX:
            compat_list = self.COMPATIBILITY_MATRIX[from_ver].get("compatible_with", [])
            return to_ver in compat_list

        # Fallback: check semantic versioning
        from_v = version.parse(from_ver)
        to_v = version.parse(to_ver)

        # Same major version = compatible
        return from_v.major == to_v.major

    def _find_upgrade_path(
        self,
        from_ver: str,
        to_ver: str,
        max_steps: int = 10
    ) -> Optional[List[str]]:
        """Find shortest upgrade path using BFS."""
        from collections import deque

        queue = deque([(from_ver, [from_ver])])
        visited = {from_ver}

        while queue:
            current, path = queue.popleft()

            if len(path) > max_steps:
                continue

            if current == to_ver:
                return path

            # Get next compatible versions
            if current in self.COMPATIBILITY_MATRIX:
                next_versions = self.COMPATIBILITY_MATRIX[current].get("compatible_with", [])

                for next_ver in next_versions:
                    if next_ver not in visited:
                        visited.add(next_ver)
                        queue.append((next_ver, path + [next_ver]))

        return None

    def _assess_upgrade_risk(self, path: List[str], breaking: List[str]) -> str:
        """Assess risk level of upgrade."""
        if len(breaking) > 0:
            return "HIGH"
        if len(path) > 3:
            return "MEDIUM"
        return "LOW"

    def _generate_upgrade_recommendations(
        self,
        path: List[str],
        breaking: List[str]
    ) -> List[str]:
        """Generate upgrade recommendations."""
        recs = []

        if len(path) > 2:
            recs.append(f"Multi-step upgrade required ({len(path)-1} steps)")
            recs.append("Test each intermediate version")

        if breaking:
            recs.append("⚠️ Breaking changes detected")
            recs.append("Backup all data before upgrading")
            recs.append("Review migration guides for each version")

        recs.append("Run full test suite after upgrade")
        recs.append("Monitor for issues in first 24 hours")

        return recs

    def generate_upgrade_script(self, result: CompatibilityResult) -> str:
        """Generate bash script for upgrade."""
        script = f"""#!/bin/bash
# EJE Upgrade Script
# From: {result.current_version}
# To: {result.target_version}

set -e  # Exit on error

echo "🚀 Starting EJE upgrade..."
echo "Current version: {result.current_version}"
echo "Target version: {result.target_version}"
echo ""

# Backup
echo "📦 Creating backup..."
cp -r eleanor_data eleanor_data.backup.$(date +%Y%m%d_%H%M%S)

"""

        for i, ver in enumerate(result.migration_path[1:], 1):
            script += f"""
# Step {i}: Upgrade to {ver}
echo "⬆️  Upgrading to {ver}..."
git checkout v{ver}
pip install -r requirements.txt
python governance/migration_maps/migrate_{result.migration_path[i-1]}_to_{ver}.py
python -m pytest tests/ -v

"""

        script += """
echo ""
echo "✅ Upgrade complete!"
echo "Please verify system functionality"
"""

        return script


def main():
    """CLI entry point."""
    import sys

    if len(sys.argv) != 3:
        print("Usage: python version_compat.py <current_version> <target_version>")
        sys.exit(1)

    checker = VersionCompatibilityChecker()
    result = checker.check_compatibility(sys.argv[1], sys.argv[2])

    print(f"Compatibility Check: {sys.argv[1]} → {sys.argv[2]}")
    print(f"Compatible: {result.compatible}")
    print(f"Risk Level: {result.risk_level}")
    print(f"\nMigration Path: {' → '.join(result.migration_path)}")

    if result.breaking_changes:
        print(f"\n⚠️ Breaking Changes:")
        for change in result.breaking_changes:
            print(f"  - {change}")

    print(f"\n📋 Recommendations:")
    for rec in result.recommendations:
        print(f"  - {rec}")


if __name__ == "__main__":
    main()
