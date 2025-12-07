"""Legal and compliance domain configuration."""

LEGAL_CONFIG = {
    "gdpr": {
        "lawful_bases": [
            "consent",
            "contract",
            "legal_obligation",
            "vital_interests",
            "public_task",
            "legitimate_interests"
        ],
        "data_subject_rights": [
            "access",
            "rectification",
            "erasure",
            "restrict_processing",
            "data_portability",
            "object",
            "automated_decision_making"
        ],
        "response_deadline_days": 30,
        "breach_notification_hours": 72,
        "dpo_required_conditions": [
            "public_authority",
            "large_scale_monitoring",
            "large_scale_sensitive_data"
        ],
        "adequacy_countries": [
            "Andorra", "Argentina", "Canada", "Faroe Islands", "Guernsey",
            "Israel", "Isle of Man", "Japan", "Jersey", "New Zealand",
            "South Korea", "Switzerland", "United Kingdom", "Uruguay"
        ],
        "max_fine_tier_1": "€10M or 2% global turnover",
        "max_fine_tier_2": "€20M or 4% global turnover"
    },
    "eu_ai_act": {
        "risk_levels": ["unacceptable", "high", "limited", "minimal"],
        "prohibited_practices": [
            "subliminal_manipulation",
            "exploitation_of_vulnerabilities",
            "social_scoring_by_authorities",
            "real_time_biometric_public",
            "emotion_recognition_workplace_education"
        ],
        "high_risk_categories": [
            "critical_infrastructure",
            "education_vocational_training",
            "employment_management",
            "essential_services_benefits",
            "law_enforcement",
            "migration_asylum_border",
            "justice_democratic_processes"
        ],
        "conformity_assessment_required": True,
        "ce_marking_required": True,
        "registration_in_eu_database": True,
        "post_market_monitoring": True
    },
    "contract_law": {
        "essential_terms": [
            "parties",
            "subject_matter",
            "consideration",
            "duration",
            "payment_terms"
        ],
        "unfair_terms_indicators": [
            "grossly_unbalanced_rights",
            "disproportionate_penalties",
            "no_liability_for_party_actions",
            "unilateral_modification_rights",
            "automatic_renewal_without_notice"
        ],
        "contract_types": [
            "service_agreement",
            "sales_contract",
            "license_agreement",
            "nda",
            "employment",
            "partnership"
        ],
        "ambiguity_rule": "contra_proferentem"
    },
    "multi_jurisdiction": {
        "supported_jurisdictions": {
            "eu": {
                "regulations": ["GDPR", "EU AI Act", "ePrivacy Directive", "NIS2 Directive"],
                "member_states": 27,
                "legal_system": "civil_law"
            },
            "us": {
                "regulations": ["CCPA/CPRA", "HIPAA", "COPPA", "FCRA", "State AI Laws"],
                "states": 50,
                "legal_system": "common_law"
            },
            "uk": {
                "regulations": ["UK GDPR", "Data Protection Act 2018", "Online Safety Act"],
                "legal_system": "common_law"
            },
            "canada": {
                "regulations": ["PIPEDA", "AIDA (proposed)"],
                "provinces": 13,
                "legal_system": "bijural"
            },
            "china": {
                "regulations": ["PIPL", "Cybersecurity Law", "AI Regulations"],
                "legal_system": "socialist_law"
            },
            "india": {
                "regulations": ["DPDPA 2023", "IT Act 2000"],
                "legal_system": "common_law"
            },
            "australia": {
                "regulations": ["Privacy Act 1988", "Australian AI Ethics Framework"],
                "legal_system": "common_law"
            }
        },
        "conflict_resolution_methods": [
            "choice_of_law_clause",
            "forum_selection_clause",
            "arbitration",
            "most_protective_standard"
        ]
    },
    "regulatory_monitoring": {
        "update_frequency": "continuous",
        "sources": [
            "official_gazettes",
            "regulatory_agency_websites",
            "legal_databases",
            "industry_associations"
        ],
        "alert_triggers": [
            "new_legislation",
            "regulatory_guidance",
            "enforcement_actions",
            "court_decisions",
            "consultation_periods"
        ],
        "impact_assessment_required": True
    },
    "compliance_documentation": {
        "required_policies": [
            "privacy_policy",
            "terms_of_service",
            "cookie_policy",
            "data_retention_policy",
            "security_policy",
            "incident_response_plan"
        ],
        "record_retention_periods": {
            "contracts": "7_years_post_expiration",
            "compliance_audits": "5_years",
            "data_processing_records": "3_years",
            "breach_notifications": "5_years"
        }
    }
}
