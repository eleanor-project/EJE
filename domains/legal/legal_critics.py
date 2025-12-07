"""Legal and compliance domain critics for GDPR, EU AI Act, contract analysis, and regulatory tracking."""

from typing import Dict, Any


class GDPRComplianceCritic:
    """Assess GDPR (General Data Protection Regulation) compliance."""
    
    def __init__(self):
        self.name = "GDPRComplianceCritic"
    
    def evaluate(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate GDPR compliance across data processing activities."""
        violations = []
        
        # Lawful basis check (Article 6)
        if context.get("processing_personal_data"):
            if not context.get("lawful_basis"):
                violations.append("No lawful basis for processing personal data (Art. 6)")
        
        # Consent requirements (Article 7)
        if context.get("consent_basis"):
            if not context.get("freely_given") or not context.get("specific") or not context.get("informed"):
                violations.append("Consent not freely given, specific, and informed (Art. 7)")
        
        # Data minimization (Article 5(1)(c))
        if context.get("data_collection"):
            if context.get("excessive_data_collected"):
                violations.append("Data collection exceeds necessity principle (Art. 5(1)(c))")
        
        # Data subject rights
        if context.get("right_request"):
            if not context.get("responded_within_30_days"):
                violations.append("Failed to respond to data subject request within 30 days (Art. 12(3))")
        
        # DPO requirement (Article 37)
        if context.get("large_scale_processing") and not context.get("has_dpo"):
            violations.append("Data Protection Officer required for large-scale processing (Art. 37)")
        
        # Data breach notification (Article 33)
        if context.get("data_breach_occurred"):
            if not context.get("notified_within_72_hours"):
                violations.append("Data breach not reported to authority within 72 hours (Art. 33)")
        
        # International transfers (Article 44-50)
        if context.get("international_transfer"):
            if not context.get("adequacy_decision") and not context.get("appropriate_safeguards"):
                violations.append("International transfer without adequacy or safeguards (Art. 44-50)")
        
        if violations:
            return {
                "verdict": "DENY",
                "confidence": 0.95,
                "justification": f"GDPR violations detected: {'; '.join(violations)}",
                "metadata": {
                    "violations": violations,
                    "regulation": "GDPR (EU 2016/679)",
                    "max_fine": "€20M or 4% global turnover"
                }
            }
        
        return {
            "verdict": "ALLOW",
            "confidence": 0.9,
            "justification": "GDPR compliance requirements met",
            "metadata": {"gdpr_compliant": True}
        }


class EUAIActCritic:
    """Assess EU AI Act compliance for AI systems."""
    
    def __init__(self):
        self.name = "EUAIActCritic"
    
    def evaluate(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate EU AI Act compliance based on risk classification."""
        risks = []
        
        # Prohibited AI practices (Article 5)
        prohibited_practices = [
            "manipulative_techniques",
            "social_scoring",
            "real_time_biometric_identification",
            "emotion_recognition_workplace"
        ]
        for practice in prohibited_practices:
            if context.get(practice):
                risks.append(f"Prohibited AI practice: {practice} (Art. 5)")
        
        # High-risk AI system requirements
        if context.get("high_risk_classification"):
            # Risk management (Article 9)
            if not context.get("risk_management_system"):
                risks.append("High-risk AI requires risk management system (Art. 9)")
            
            # Data governance (Article 10)
            if not context.get("data_governance_measures"):
                risks.append("Inadequate data governance for high-risk AI (Art. 10)")
            
            # Technical documentation (Article 11)
            if not context.get("technical_documentation"):
                risks.append("Missing technical documentation (Art. 11)")
            
            # Human oversight (Article 14)
            if not context.get("human_oversight_measures"):
                risks.append("High-risk AI lacks human oversight (Art. 14)")
            
            # Accuracy, robustness, cybersecurity (Article 15)
            if context.get("insufficient_robustness_testing"):
                risks.append("Inadequate robustness and accuracy testing (Art. 15)")
        
        # Transparency obligations (Article 52)
        if context.get("interacts_with_humans"):
            if not context.get("disclosed_as_ai"):
                risks.append("AI system must disclose it's not human (Art. 52)")
        
        # Foundation model requirements (Article 53)
        if context.get("foundation_model"):
            if not context.get("technical_documentation") or not context.get("copyright_compliance"):
                risks.append("Foundation model missing required documentation (Art. 53)")
        
        if risks:
            return {
                "verdict": "DENY",
                "confidence": 0.9,
                "justification": f"EU AI Act violations: {'; '.join(risks)}",
                "metadata": {
                    "violations": risks,
                    "regulation": "EU AI Act (2024/1689)",
                    "risk_level": context.get("risk_classification", "unknown")
                }
            }
        
        return {
            "verdict": "ALLOW",
            "confidence": 0.85,
            "justification": "EU AI Act requirements met",
            "metadata": {"ai_act_compliant": True}
        }


class ContractClauseAnalysisCritic:
    """Analyze contract clauses for legal risks and fairness."""
    
    def __init__(self):
        self.name = "ContractClauseAnalysisCritic"
    
    def evaluate(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate contract clauses for legal compliance and fairness."""
        issues = []
        
        # Unconscionable terms
        if context.get("unconscionable_clause"):
            issues.append("Clause may be unconscionable and unenforceable")
        
        # Penalty clauses
        if context.get("liquidated_damages"):
            if context.get("damages_excessive"):
                issues.append("Liquidated damages may constitute unenforceable penalty")
        
        # Limitation of liability
        if context.get("liability_limitation"):
            if context.get("excludes_gross_negligence"):
                issues.append("Cannot exclude liability for gross negligence/fraud")
        
        # Indemnification clauses
        if context.get("broad_indemnification"):
            if not context.get("limited_to_party_fault"):
                issues.append("Overly broad indemnification clause creates unreasonable risk")
        
        # Unfair terms (consumer contracts)
        if context.get("consumer_contract"):
            unfair_terms = context.get("unfair_terms_list", [])
            for term in unfair_terms:
                issues.append(f"Unfair consumer term: {term}")
        
        # Ambiguous language
        if context.get("ambiguous_language"):
            issues.append("Ambiguous contract language may be construed against drafter")
        
        # Missing essential terms
        essential_terms = ["parties", "subject_matter", "consideration", "duration"]
        for term in essential_terms:
            if not context.get(term):
                issues.append(f"Missing essential contract term: {term}")
        
        if issues:
            return {
                "verdict": "DENY",
                "confidence": 0.8,
                "justification": f"Contract clause issues: {'; '.join(issues)}",
                "metadata": {
                    "issues": issues,
                    "contract_type": context.get("contract_type", "unknown")
                }
            }
        
        return {
            "verdict": "ALLOW",
            "confidence": 0.75,
            "justification": "Contract clauses appear reasonable and enforceable",
            "metadata": {"clauses_reviewed": context.get("clause_count", 0)}
        }


class RegulatoryChangeCritic:
    """Track and assess impact of regulatory changes."""
    
    def __init__(self):
        self.name = "RegulatoryChangeCritic"
    
    def evaluate(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate regulatory change impact on operations."""
        concerns = []
        
        # New regulation effective date
        if context.get("new_regulation"):
            if not context.get("compliance_plan"):
                concerns.append("No compliance plan for upcoming regulation")
            
            if context.get("effective_date_soon") and not context.get("ready_for_compliance"):
                concerns.append("Insufficient time to achieve compliance before effective date")
        
        # Regulatory interpretation changes
        if context.get("interpretation_change"):
            if not context.get("impact_assessment_completed"):
                concerns.append("Regulatory interpretation change requires impact assessment")
        
        # Enforcement action trends
        if context.get("increased_enforcement_activity"):
            if not context.get("compliance_audit_scheduled"):
                concerns.append("Increased enforcement warrants proactive compliance audit")
        
        # Cross-jurisdiction conflicts
        if context.get("multi_jurisdiction"):
            if context.get("conflicting_requirements"):
                concerns.append("Conflicting regulatory requirements across jurisdictions")
        
        if concerns:
            return {
                "verdict": "DENY",
                "confidence": 0.85,
                "justification": f"Regulatory change concerns: {'; '.join(concerns)}",
                "metadata": {
                    "concerns": concerns,
                    "regulation": context.get("regulation_name", "unknown")
                }
            }
        
        return {
            "verdict": "ALLOW",
            "confidence": 0.8,
            "justification": "Regulatory changes appropriately tracked and managed",
            "metadata": {"changes_monitored": True}
        }


class JurisdictionFrameworkCritic:
    """Assess multi-jurisdiction legal framework compliance."""
    
    def __init__(self):
        self.name = "JurisdictionFrameworkCritic"
    
    def evaluate(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate legal compliance across multiple jurisdictions."""
        issues = []
        
        # Jurisdiction determination
        if not context.get("applicable_jurisdictions"):
            issues.append("Applicable jurisdictions not identified")
        
        # Choice of law clauses
        if context.get("multi_party_contract"):
            if not context.get("choice_of_law_clause"):
                issues.append("Missing choice of law clause in multi-jurisdiction contract")
        
        # Conflict of laws
        if context.get("jurisdictional_conflicts"):
            if not context.get("conflict_resolution_strategy"):
                issues.append("No strategy for resolving jurisdictional conflicts")
        
        # Forum selection
        if context.get("dispute_potential"):
            if not context.get("forum_selection_clause"):
                issues.append("Consider forum selection clause for dispute resolution")
        
        # Local compliance requirements
        active_jurisdictions = context.get("active_jurisdictions", [])
        for jurisdiction in active_jurisdictions:
            if not context.get(f"{jurisdiction}_compliance_verified"):
                issues.append(f"Compliance not verified for {jurisdiction}")
        
        # International arbitration
        if context.get("international_scope"):
            if not context.get("arbitration_clause") and not context.get("litigation_strategy"):
                issues.append("International matters should address dispute resolution mechanism")
        
        if issues:
            return {
                "verdict": "DENY",
                "confidence": 0.8,
                "justification": f"Jurisdiction framework issues: {'; '.join(issues)}",
                "metadata": {
                    "issues": issues,
                    "jurisdictions": context.get("applicable_jurisdictions", [])
                }
            }
        
        return {
            "verdict": "ALLOW",
            "confidence": 0.75,
            "justification": "Multi-jurisdiction framework appropriately addressed",
            "metadata": {"jurisdictions_covered": len(active_jurisdictions)}
        }


__all__ = [
    "GDPRComplianceCritic",
    "EUAIActCritic",
    "ContractClauseAnalysisCritic",
    "RegulatoryChangeCritic",
    "JurisdictionFrameworkCritic",
]
