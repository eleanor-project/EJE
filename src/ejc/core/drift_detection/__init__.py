"""
Drift detection system for monitoring system behavior over time.

Detects:
- Constitutional drift: Changes in rights protection
- Precedent inconsistencies: Similar cases with different outcomes
- Ethical consensus shifts: Changes in critic agreement patterns
"""

from .drift_monitor import DriftMonitor
from .constitutional_drift import ConstitutionalDriftDetector
from .precedent_consistency import PrecedentConsistencyChecker
from .consensus_tracker import ConsensusTracker

__all__ = [
    "DriftMonitor",
    "ConstitutionalDriftDetector",
    "PrecedentConsistencyChecker",
    "ConsensusTracker",
]
