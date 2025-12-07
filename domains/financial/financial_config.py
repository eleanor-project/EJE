"""Financial services domain configuration."""

FINANCIAL_CONFIG = {
    "aml": {
        "transaction_threshold": 10000,  # Threshold for enhanced scrutiny
        "velocity_threshold": 5,  # Max transactions per time period
        "risk_countries": ["OFAC sanctioned"],  # High-risk jurisdictions
        "structuring_pattern_window": "24h",
        "required_documentation": ["source_of_funds", "transaction_purpose"],
    },
    "kyc": {
        "identity_verification_levels": {
            "basic": ["name", "dob", "address"],
            "enhanced": ["government_id", "biometric", "proof_of_address"],
            "pep_screening": True,  # Politically exposed persons
        },
        "refresh_interval": "12m",  # How often to re-verify
        "continuous_monitoring": True,
    },
    "fair_lending": {
        "protected_classes": [
            "race",
            "color",
            "religion",
            "national_origin",
            "sex",
            "marital_status",
            "age",
            "disability",
        ],
        "disparate_impact_threshold": 0.8,  # 80% rule
        "required_disclosures": [
            "APR",
            "total_costs",
            "payment_schedule",
            "right_to_rescind",
        ],
        "audit_frequency": "quarterly",
    },
    "fiduciary_duty": {
        "duty_of_care_standard": "prudent_investor",
        "duty_of_loyalty": {
            "conflict_disclosure_required": True,
            "prohibited_transactions": ["self_dealing", "front_running"],
        },
        "suitability_requirements": [
            "risk_tolerance",
            "investment_objectives",
            "time_horizon",
            "financial_situation",
        ],
        "documentation_retention": "7y",
    },
    "market_manipulation": {
        "prohibited_activities": [
            "wash_trading",
            "pump_and_dump",
            "spoofing",
            "layering",
            "insider_trading",
        ],
        "surveillance_indicators": [
            "unusual_volume",
            "price_volatility",
            "timing_patterns",
            "cross_market_activity",
        ],
        "reporting_threshold_seconds": 60,  # Report suspicious activity within 60s
    },
    "regulatory_frameworks": {
        "us": ["BSA", "Dodd-Frank", "FCRA", "ECOA", "Investment Advisers Act"],
        "eu": ["MiFID II", "MAR", "AMLD5"],
        "global": ["FATF Recommendations", "Basel III"],
    },
    "risk_scoring": {
        "low": {"range": [0, 30], "action": "standard_monitoring"},
        "medium": {"range": [31, 60], "action": "enhanced_monitoring"},
        "high": {"range": [61, 85], "action": "senior_review_required"},
        "critical": {"range": [86, 100], "action": "suspend_and_investigate"},
    },
}
