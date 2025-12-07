"""Education domain configuration."""

EDUCATION_CONFIG = {
    "academic_integrity": {
        "plagiarism_similarity_threshold": 0.3,  # 30% similarity triggers review
        "citation_style_enforcement": True,
        "collaboration_tracking": True,
        "exam_proctoring_requirements": {
            "identity_verification": True,
            "environment_scan": True,
            "browser_lockdown": False,  # Optional for less critical exams
        },
        "ai_detection_enabled": True,
        "honor_code_acknowledgment_required": True,
    },
    "equity_allocation": {
        "funding_disparity_threshold": 1.3,  # Max acceptable ratio
        "opportunity_gap_threshold": 0.25,  # 25% max disparity in AP/honors access
        "teacher_quality_metrics": [
            "years_experience",
            "certification_status",
            "effectiveness_rating",
        ],
        "monitored_resources": [
            "technology_access",
            "library_materials",
            "counseling_services",
            "advanced_courses",
            "extracurricular_programs",
        ],
        "equity_audit_frequency": "annual",
    },
    "student_privacy": {
        "ferpa_compliance_required": True,
        "consent_requirements": {
            "under_18_parental_consent": True,
            "over_18_student_consent": True,
            "directory_info_opt_out": True,
        },
        "data_minimization": {
            "collect_only_essential": True,
            "retention_limits": {
                "grades": "permanent",
                "discipline_records": "7_years",
                "health_records": "varies_by_state",
            },
        },
        "security_requirements": {
            "encryption_at_rest": True,
            "encryption_in_transit": True,
            "access_control": "role_based",
            "audit_logging": True,
        },
        "third_party_sharing_restrictions": {
            "school_official_exception": True,
            "audit_study_exception": True,
            "accreditation_exception": True,
            "default_require_consent": True,
        },
    },
    "accessibility_compliance": {
        "ada_title_ii_compliance": True,
        "section_504_compliance": True,
        "wcag_level": "AA",  # Web Content Accessibility Guidelines
        "accommodation_types": [
            "extended_time",
            "alternate_formats",
            "assistive_technology",
            "quiet_testing_environment",
            "breaks",
            "scribe_services",
            "interpreter_services",
        ],
        "documentation_required": {
            "iep": True,  # Individualized Education Program
            "504_plan": True,
            "medical_documentation": "case_by_case",
        },
        "physical_access_requirements": [
            "wheelchair_ramps",
            "accessible_parking",
            "elevator_access",
            "accessible_restrooms",
            "wide_doorways",
        ],
        "response_time_for_requests": "reasonable_prompt",  # Typically 2-4 weeks
    },
    "bias_detection": {
        "admissions": {
            "disparate_impact_threshold": 0.8,  # 80% rule
            "monitored_criteria": [
                "test_scores",
                "gpa",
                "essays",
                "interviews",
                "extracurriculars",
            ],
            "holistic_review_required": True,
            "quota_prohibition": True,
            "legacy_preference_limit": 0.15,  # Max 15% weight
        },
        "grading": {
            "blind_grading_recommended": True,
            "rubric_required_for_subjective": True,
            "grade_gap_threshold": 0.5,  # Half grade point triggers review
            "inter_rater_reliability_checks": True,
        },
        "algorithmic_fairness": {
            "bias_audit_required": True,
            "protected_attribute_prohibition": True,
            "disparate_impact_testing": True,
            "explainability_required": True,
        },
        "demographic_monitoring": [
            "race_ethnicity",
            "gender",
            "socioeconomic_status",
            "english_learner_status",
            "disability_status",
        ],
    },
    "regulatory_frameworks": {
        "federal": [
            "FERPA",
            "ADA Title II",
            "Section 504",
            "Title VI Civil Rights Act",
            "Title IX",
            "IDEA",  # Individuals with Disabilities Education Act
        ],
        "accreditation": [
            "Regional accreditors",
            "Program-specific accreditors",
        ],
    },
}
