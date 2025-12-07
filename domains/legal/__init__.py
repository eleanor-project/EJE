"""Legal and compliance domain governance module.

Provides domain-specific oversight for legal applications with multi-jurisdiction
support, regulatory compliance, and contract analysis capabilities.
"""

from .legal_critics import (
    GDPRComplianceCritic,
    EUAIActCritic,
    ContractClauseAnalysisCritic,
    RegulatoryChangeCritic,
    JurisdictionFrameworkCritic,
)

__all__ = [
    "GDPRComplianceCritic",
    "EUAIActCritic",
    "ContractClauseAnalysisCritic",
    "RegulatoryChangeCritic",
    "JurisdictionFrameworkCritic",
]
