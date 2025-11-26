"""
GCR (Governance Change Request) Impact Analyzer

Automated tool for analyzing governance changes and their impact on the EJE system.

Features:
- Automatic component impact analysis
- Breaking change detection
- Migration requirement assessment
- Version compatibility checking
- Rollback safety verification
- Affected tests identification
"""

import json
import ast
import re
from pathlib import Path
from typing import Dict, Any, List, Set, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
import hashlib


@dataclass
class ComponentImpact:
    """Impact analysis for a specific component."""
    component_name: str
    files_affected: List[str]
    breaking_changes: bool
    migration_required: bool
    risk_level: str  # LOW, MEDIUM, HIGH, CRITICAL
    affected_tests: List[str]
    recommendations: List[str]


@dataclass
class GCRImpactReport:
    """Complete GCR impact analysis report."""
    gcr_id: str
    title: str
    analysis_date: str
    components_affected: List[ComponentImpact]
    overall_risk: str
    breaking_changes_detected: bool
    migration_required: bool
    rollback_safe: bool
    estimated_effort_hours: int
    version_bump_recommendation: str  # MAJOR, MINOR, PATCH
    dependencies_affected: List[str]
    test_coverage_required: List[str]


class GCRAnalyzer:
    """
    Automated analyzer for Governance Change Requests.

    Analyzes proposed changes and generates comprehensive impact reports.
    """

    # Core component patterns
    COMPONENTS = {
        "ethical_reasoning": ["ethical_reasoning_engine", "core/reasoning"],
        "critics": ["critics/", "critic_"],
        "aggregation": ["aggregator", "aggregation"],
        "governance": ["governance/rules", "governance/audit"],
        "precedent": ["precedent/", "precedent_"],
        "audit": ["audit_log", "signed_audit", "encrypted_audit"],
        "config": ["config_loader", "config/"],
        "api": ["server/api", "sdk/client"],
        "security": ["security", "encryption", "signing"]
    }

    # Breaking change indicators
    BREAKING_PATTERNS = [
        r"def.*\(.*\).*->.*:",  # Function signature changes
        r"class.*\(.*\):",       # Class inheritance changes
        r"return\s+\w+",         # Return type changes
        r"@property",            # Property changes
        r"raise\s+\w+Exception", # Exception changes
    ]

    # Migration indicators
    MIGRATION_PATTERNS = [
        r"schema",
        r"database",
        r"precedent.*format",
        r"config.*version",
        r"api.*version"
    ]

    def __init__(self, repo_root: Optional[Path] = None):
        """
        Initialize GCR Analyzer.

        Args:
            repo_root: Root directory of the repository
        """
        self.repo_root = repo_root or Path(__file__).parent.parent
        self.ledger_path = self.repo_root / "governance" / "gcr_ledger.json"

    def analyze_changes(
        self,
        changed_files: List[str],
        description: str,
        title: str
    ) -> GCRImpactReport:
        """
        Analyze the impact of proposed changes.

        Args:
            changed_files: List of file paths that will be changed
            description: Description of the changes
            title: GCR title

        Returns:
            Complete impact analysis report
        """
        gcr_id = self._generate_gcr_id()

        # Analyze each component
        components_affected = []
        for component_name, patterns in self.COMPONENTS.items():
            impact = self._analyze_component(component_name, patterns, changed_files, description)
            if impact.files_affected:
                components_affected.append(impact)

        # Determine overall risk
        overall_risk = self._calculate_overall_risk(components_affected)

        # Check for breaking changes
        breaking_changes = any(c.breaking_changes for c in components_affected)

        # Check if migration required
        migration_required = any(c.migration_required for c in components_affected)

        # Assess rollback safety
        rollback_safe = self._assess_rollback_safety(components_affected, changed_files)

        # Estimate effort
        effort = self._estimate_effort(components_affected)

        # Recommend version bump
        version_bump = self._recommend_version_bump(breaking_changes, migration_required)

        # Identify affected dependencies
        dependencies = self._identify_dependencies(changed_files)

        # Required test coverage
        test_coverage = self._identify_test_requirements(components_affected)

        return GCRImpactReport(
            gcr_id=gcr_id,
            title=title,
            analysis_date=datetime.utcnow().isoformat() + "Z",
            components_affected=components_affected,
            overall_risk=overall_risk,
            breaking_changes_detected=breaking_changes,
            migration_required=migration_required,
            rollback_safe=rollback_safe,
            estimated_effort_hours=effort,
            version_bump_recommendation=version_bump,
            dependencies_affected=dependencies,
            test_coverage_required=test_coverage
        )

    def _analyze_component(
        self,
        component_name: str,
        patterns: List[str],
        changed_files: List[str],
        description: str
    ) -> ComponentImpact:
        """Analyze impact on a specific component."""
        files_affected = []

        # Check which files match this component
        for file_path in changed_files:
            if any(pattern in file_path for pattern in patterns):
                files_affected.append(file_path)

        if not files_affected:
            return ComponentImpact(
                component_name=component_name,
                files_affected=[],
                breaking_changes=False,
                migration_required=False,
                risk_level="NONE",
                affected_tests=[],
                recommendations=[]
            )

        # Detect breaking changes
        breaking_changes = self._detect_breaking_changes(files_affected, description)

        # Check migration requirement
        migration_required = self._check_migration_needed(files_affected, description)

        # Assess risk level
        risk_level = self._assess_risk(component_name, breaking_changes, migration_required)

        # Find affected tests
        affected_tests = self._find_affected_tests(component_name, files_affected)

        # Generate recommendations
        recommendations = self._generate_recommendations(
            component_name, breaking_changes, migration_required
        )

        return ComponentImpact(
            component_name=component_name,
            files_affected=files_affected,
            breaking_changes=breaking_changes,
            migration_required=migration_required,
            risk_level=risk_level,
            affected_tests=affected_tests,
            recommendations=recommendations
        )

    def _detect_breaking_changes(self, files: List[str], description: str) -> bool:
        """Detect if changes are breaking."""
        # Check file contents for breaking patterns
        for file_path in files:
            full_path = self.repo_root / file_path
            if full_path.exists() and full_path.suffix == '.py':
                try:
                    content = full_path.read_text()
                    for pattern in self.BREAKING_PATTERNS:
                        if re.search(pattern, content):
                            return True
                except:
                    pass

        # Check description for breaking keywords
        breaking_keywords = ["breaking", "incompatible", "removes", "replaces", "changes API"]
        return any(keyword in description.lower() for keyword in breaking_keywords)

    def _check_migration_needed(self, files: List[str], description: str) -> bool:
        """Check if migration is needed."""
        # Check for migration patterns
        migration_keywords = ["schema", "format", "database", "storage", "version"]
        if any(keyword in description.lower() for keyword in migration_keywords):
            return True

        # Check if config or data files affected
        data_patterns = ["config/", ".yaml", ".json", "precedent", "audit"]
        return any(any(pattern in f for pattern in data_patterns) for f in files)

    def _assess_risk(
        self,
        component: str,
        breaking: bool,
        migration: bool
    ) -> str:
        """Assess risk level for component changes."""
        # Critical components
        critical = ["governance", "audit", "security"]
        high = ["ethical_reasoning", "precedent", "critics"]
        medium = ["aggregation", "config"]

        if component in critical:
            if breaking or migration:
                return "CRITICAL"
            return "HIGH"
        elif component in high:
            if breaking:
                return "HIGH"
            if migration:
                return "MEDIUM"
            return "LOW"
        elif component in medium:
            if breaking:
                return "MEDIUM"
            return "LOW"
        else:
            return "LOW"

    def _find_affected_tests(self, component: str, files: List[str]) -> List[str]:
        """Find tests affected by changes."""
        tests = []
        test_dir = self.repo_root / "tests"

        if test_dir.exists():
            # Look for test files matching component
            for test_file in test_dir.glob(f"test_*{component}*.py"):
                tests.append(str(test_file.relative_to(self.repo_root)))

            # Look for test files matching changed file names
            for file_path in files:
                file_name = Path(file_path).stem
                for test_file in test_dir.glob(f"test_*{file_name}*.py"):
                    test_path = str(test_file.relative_to(self.repo_root))
                    if test_path not in tests:
                        tests.append(test_path)

        return tests

    def _generate_recommendations(
        self,
        component: str,
        breaking: bool,
        migration: bool
    ) -> List[str]:
        """Generate recommendations for the change."""
        recs = []

        if breaking:
            recs.append(f"⚠️ Breaking changes detected in {component}")
            recs.append("Create migration guide for users")
            recs.append("Add deprecation warnings before removing old APIs")
            recs.append("Update CHANGELOG with BREAKING CHANGE notice")

        if migration:
            recs.append(f"Migration required for {component}")
            recs.append("Create migration map in governance/migration_maps/")
            recs.append("Write migration tests")
            recs.append("Test both forward and backward migration")

        if component in ["governance", "audit", "security"]:
            recs.append("Requires security review")
            recs.append("Update security documentation")

        if component in ["critics", "governance"]:
            recs.append("Requires constitutional compliance review")
            recs.append("Run governance test suite")

        return recs

    def _calculate_overall_risk(self, components: List[ComponentImpact]) -> str:
        """Calculate overall risk level."""
        if not components:
            return "NONE"

        risk_scores = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1, "NONE": 0}
        max_risk = max((risk_scores.get(c.risk_level, 0) for c in components), default=0)

        for score, level in sorted(risk_scores.items(), key=lambda x: x[1], reverse=True):
            if max_risk >= score:
                return level

        return "LOW"

    def _assess_rollback_safety(
        self,
        components: List[ComponentImpact],
        files: List[str]
    ) -> bool:
        """Assess if changes can be safely rolled back."""
        # Not safe if migration required without backward compat
        if any(c.migration_required for c in components):
            return False

        # Not safe if modifying audit logs or precedent storage
        critical_files = ["audit_log", "precedent/store", "governance/rules"]
        if any(any(cf in f for cf in critical_files) for f in files):
            return False

        return True

    def _estimate_effort(self, components: List[ComponentImpact]) -> int:
        """Estimate effort in hours."""
        base_hours = len(components) * 2  # 2 hours per component

        # Add for breaking changes
        breaking_count = sum(1 for c in components if c.breaking_changes)
        base_hours += breaking_count * 4

        # Add for migrations
        migration_count = sum(1 for c in components if c.migration_required)
        base_hours += migration_count * 8

        # Add for high-risk components
        high_risk_count = sum(1 for c in components if c.risk_level in ["HIGH", "CRITICAL"])
        base_hours += high_risk_count * 4

        return base_hours

    def _recommend_version_bump(self, breaking: bool, migration: bool) -> str:
        """Recommend semantic version bump."""
        if breaking:
            return "MAJOR"
        elif migration:
            return "MINOR"
        else:
            return "PATCH"

    def _identify_dependencies(self, files: List[str]) -> List[str]:
        """Identify external dependencies affected."""
        deps = set()

        for file_path in files:
            full_path = self.repo_root / file_path
            if full_path.exists() and full_path.suffix == '.py':
                try:
                    content = full_path.read_text()
                    # Find imports
                    imports = re.findall(r'(?:from|import)\s+([\w.]+)', content)
                    deps.update(imports)
                except:
                    pass

        # Filter to external packages only
        external = [d for d in deps if not d.startswith('ejc') and not d.startswith('test')]
        return sorted(set(external))[:10]  # Top 10

    def _identify_test_requirements(self, components: List[ComponentImpact]) -> List[str]:
        """Identify required test coverage."""
        tests = []

        for component in components:
            if component.breaking_changes:
                tests.append(f"test_{component.component_name}_breaking_changes.py")
            if component.migration_required:
                tests.append(f"test_migration_{component.component_name}.py")
            if component.risk_level in ["HIGH", "CRITICAL"]:
                tests.append(f"test_{component.component_name}_integration.py")

        return tests

    def _generate_gcr_id(self) -> str:
        """Generate next GCR ID."""
        try:
            with open(self.ledger_path, 'r') as f:
                ledger = json.load(f)

            # Find highest number
            max_num = 0
            for entry in ledger.get("gcr_ledger", []):
                match = re.search(r'GCR-(\d+)-(\d+)', entry.get("gcr_id", ""))
                if match:
                    max_num = max(max_num, int(match.group(2)))

            year = datetime.utcnow().year
            return f"GCR-{year}-{max_num + 1:03d}"
        except:
            year = datetime.utcnow().year
            return f"GCR-{year}-001"

    def generate_report_markdown(self, report: GCRImpactReport) -> str:
        """Generate markdown report."""
        md = f"""# GCR Impact Analysis Report

**GCR ID**: {report.gcr_id}
**Title**: {report.title}
**Analysis Date**: {report.analysis_date}
**Overall Risk**: {report.overall_risk}

## Summary

- **Breaking Changes**: {'⚠️ YES' if report.breaking_changes_detected else '✅ NO'}
- **Migration Required**: {'⚠️ YES' if report.migration_required else '✅ NO'}
- **Rollback Safe**: {'✅ YES' if report.rollback_safe else '⚠️ NO'}
- **Estimated Effort**: {report.estimated_effort_hours} hours
- **Version Bump**: {report.version_bump_recommendation}

## Components Affected

"""
        for comp in report.components_affected:
            md += f"""
### {comp.component_name.title()} ({comp.risk_level})

- **Files Affected**: {len(comp.files_affected)}
- **Breaking Changes**: {'YES' if comp.breaking_changes else 'NO'}
- **Migration Required**: {'YES' if comp.migration_required else 'NO'}
- **Tests Affected**: {len(comp.affected_tests)}

#### Recommendations:
"""
            for rec in comp.recommendations:
                md += f"- {rec}\n"

        md += f"""

## Dependencies Affected

{', '.join(report.dependencies_affected) if report.dependencies_affected else 'None'}

## Required Test Coverage

"""
        for test in report.test_coverage_required:
            md += f"- [ ] {test}\n"

        md += """

## Next Steps

1. Review impact analysis
2. Create required tests
3. Implement migration maps if needed
4. Update documentation
5. Submit for approval

"""
        return md

    def save_report(self, report: GCRImpactReport, output_path: Optional[Path] = None):
        """Save report to file."""
        if output_path is None:
            output_path = self.repo_root / "governance" / f"{report.gcr_id}_impact_analysis.json"

        with open(output_path, 'w') as f:
            json.dump(asdict(report), f, indent=2, default=str)

        # Also save markdown
        md_path = output_path.with_suffix('.md')
        with open(md_path, 'w') as f:
            f.write(self.generate_report_markdown(report))

        return output_path, md_path


def main():
    """CLI entry point."""
    import sys

    if len(sys.argv) < 3:
        print("Usage: python gcr_analyzer.py <title> <file1> [file2] [file3]...")
        sys.exit(1)

    title = sys.argv[1]
    files = sys.argv[2:]

    analyzer = GCRAnalyzer()
    report = analyzer.analyze_changes(
        changed_files=files,
        description="",
        title=title
    )

    print(analyzer.generate_report_markdown(report))


if __name__ == "__main__":
    main()
