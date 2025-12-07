"""
Financial Services Governance Domain Module

This module provides financial services-specific governance capabilities including:
- AML (Anti-Money Laundering) compliance
- KYC (Know Your Customer) verification
- Fair lending compliance (ECOA, FCRA)
- Fiduciary duty assessment
- Market manipulation detection
- Financial precedent templates

Part of the EJE Domains framework for domain-specific governance.
"""

from .financial_critics import (
    AMLComplianceCritic,
    KYCVerificationCritic,
    FairLendingCritic,
    FiduciaryDutyCritic,
    MarketManipulationCritic,
)

from .financial_config import FinancialConfig
from .precedent_templates import FinancialPrecedentTemplates

__all__ = [
    "AMLComplianceCritic",
    "KYCVerificationCritic",
    "FairLendingCritic",
    "FiduciaryDutyCritic",
    "MarketManipulationCritic",
    "FinancialConfig",
    "FinancialPrecedentTemplates",
]

__version__ = "1.0.0"
