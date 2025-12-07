"""Education domain critics for academic integrity, equity, privacy, accessibility, and bias detection."""

from typing import Dict, Any


class AcademicIntegrityCritic:
    """Assess academic integrity in educational contexts."""
    
    def __init__(self):
        self.name = "AcademicIntegrityCritic"
    
    def evaluate(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate academic integrity concerns.
        
        Checks for plagiarism, unauthorized collaboration, cheating,
        and proper citation practices.
        """
        risks = []
        
        # Check for plagiarism indicators
        if context.get("plagiarism_similarity_score", 0) > 0.3:
            risks.append("High similarity to existing sources detected")
        
        # Check for unauthorized collaboration
        if context.get("collaboration_detected") and not context.get("collaboration_allowed"):
            risks.append("Unauthorized collaboration on individual assignment")
        
        # Check for proper citations
        if context.get("citation_issues"):
            risks.append(f"Citation issues: {context.get('citation_issues')}")
        
        # Check exam integrity
        if context.get("exam_context"):
            if context.get("unauthorized_resources_accessed"):
                risks.append("Unauthorized resources accessed during examination")
            if context.get("identity_verification_failed"):
                risks.append("Student identity verification failed")
        
        if risks:
            return {
                "verdict": "DENY",
                "confidence": 0.9,
                "justification": f"Academic integrity violations detected: {'; '.join(risks)}",
                "metadata": {"violations": risks, "policy": "Academic Honor Code"}
            }
        
        return {
            "verdict": "ALLOW",
            "confidence": 0.85,
            "justification": "No academic integrity concerns detected",
            "metadata": {"checks_passed": ["plagiarism", "collaboration", "citations"]}
        }


class EquityAllocationCritic:
    """Assess equity in resource allocation and opportunity distribution."""
    
    def __init__(self):
        self.name = "EquityAllocationCritic"
    
    def evaluate(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate equity in educational resource allocation.
        
        Examines distribution of funding, opportunities, teacher quality,
        and educational resources across different student groups.
        """
        equity_concerns = []
        
        # Check funding equity
        if context.get("funding_disparities"):
            funding_ratio = context.get("high_income_per_student", 0) / max(context.get("low_income_per_student", 1), 1)
            if funding_ratio > 1.3:  # More than 30% disparity
                equity_concerns.append(f"Significant funding disparity ratio: {funding_ratio:.2f}")
        
        # Check opportunity equity
        if context.get("advanced_placement_access"):
            ap_disparity = abs(
                context.get("ap_enrollment_rate_advantaged", 0) - 
                context.get("ap_enrollment_rate_disadvantaged", 0)
            )
            if ap_disparity > 0.25:  # More than 25% gap
                equity_concerns.append(f"AP access gap: {ap_disparity*100:.1f}%")
        
        # Check teacher quality distribution
        if context.get("teacher_quality_metrics"):
            if context.get("experienced_teacher_disparity", 0) > 0.2:
                equity_concerns.append("Inequitable distribution of experienced teachers")
        
        # Check resource allocation
        if context.get("resource_distribution"):
            for resource in context.get("underallocated_resources", []):
                equity_concerns.append(f"Underallocation of {resource} to disadvantaged groups")
        
        if equity_concerns:
            return {
                "verdict": "DENY",
                "confidence": 0.85,
                "justification": f"Equity concerns in resource allocation: {'; '.join(equity_concerns)}",
                "metadata": {
                    "concerns": equity_concerns,
                    "regulation": "Equal Educational Opportunities Act"
                }
            }
        
        return {
            "verdict": "ALLOW",
            "confidence": 0.8,
            "justification": "Equitable resource allocation observed",
            "metadata": {"equity_metrics": context.get("equity_scores", {})}
        }


class StudentPrivacyCritic:
    """Ensure FERPA compliance and student data privacy."""
    
    def __init__(self):
        self.name = "StudentPrivacyCritic"
    
    def evaluate(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate student privacy and FERPA compliance.
        
        Checks for proper handling of education records, consent requirements,
        and data protection measures.
        """
        privacy_violations = []
        
        # Check for unauthorized disclosure
        if context.get("data_disclosure"):
            if not context.get("parental_consent") and not context.get("student_consent_if_18plus"):
                if not context.get("ferpa_exception_applies"):
                    privacy_violations.append("Disclosure of education records without required consent")
        
        # Check data minimization
        if context.get("data_collection"):
            if context.get("excessive_data_collected"):
                privacy_violations.append("Collection of non-essential student data")
        
        # Check for proper data security
        if context.get("data_storage"):
            if not context.get("encrypted_storage"):
                privacy_violations.append("Student records not properly encrypted")
            if not context.get("access_controls"):
                privacy_violations.append("Inadequate access controls for student records")
        
        # Check directory information handling
        if context.get("directory_info_disclosure"):
            if not context.get("opt_out_opportunity_provided"):
                privacy_violations.append("Directory information disclosed without opt-out opportunity")
        
        # Check third-party data sharing
        if context.get("third_party_sharing"):
            if not context.get("school_official_exception") and not context.get("study_exception"):
                privacy_violations.append("Improper third-party data sharing")
        
        if privacy_violations:
            return {
                "verdict": "DENY",
                "confidence": 0.95,
                "justification": f"FERPA violations detected: {'; '.join(privacy_violations)}",
                "metadata": {
                    "violations": privacy_violations,
                    "regulation": "FERPA (20 U.S.C. § 1232g)"
                }
            }
        
        return {
            "verdict": "ALLOW",
            "confidence": 0.9,
            "justification": "Student privacy protections and FERPA compliance verified",
            "metadata": {"ferpa_compliance": True}
        }


class AccessibilityComplianceCritic:
    """Ensure ADA compliance and accessibility for students with disabilities."""
    
    def __init__(self):
        self.name = "AccessibilityComplianceCritic"
    
    def evaluate(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate accessibility and ADA compliance.
        
        Checks for reasonable accommodations, accessible materials,
        and inclusive educational environments.
        """
        accessibility_issues = []
        
        # Check for reasonable accommodations
        if context.get("accommodation_request"):
            if not context.get("accommodation_provided"):
                if not context.get("undue_hardship_demonstrated"):
                    accessibility_issues.append("Reasonable accommodation request denied without justification")
        
        # Check digital accessibility
        if context.get("digital_content"):
            if not context.get("wcag_compliant"):
                accessibility_issues.append("Digital content not WCAG 2.1 AA compliant")
            if not context.get("screen_reader_compatible"):
                accessibility_issues.append("Content not compatible with screen readers")
        
        # Check physical accessibility
        if context.get("physical_facility"):
            if not context.get("wheelchair_accessible"):
                accessibility_issues.append("Facility not wheelchair accessible")
            if not context.get("accessible_restrooms"):
                accessibility_issues.append("Accessible restrooms not provided")
        
        # Check testing accommodations
        if context.get("assessment_context"):
            if context.get("iep_or_504_plan") and not context.get("accommodations_in_testing"):
                accessibility_issues.append("Required testing accommodations not provided")
        
        # Check communication accessibility
        if context.get("communication_needs"):
            if context.get("deaf_or_hard_of_hearing") and not context.get("interpreter_or_captions"):
                accessibility_issues.append("No interpreter or captions for deaf/hard of hearing students")
        
        if accessibility_issues:
            return {
                "verdict": "DENY",
                "confidence": 0.9,
                "justification": f"ADA compliance issues: {'; '.join(accessibility_issues)}",
                "metadata": {
                    "violations": accessibility_issues,
                    "regulations": ["ADA Title II", "Section 504 Rehabilitation Act"]
                }
            }
        
        return {
            "verdict": "ALLOW",
            "confidence": 0.85,
            "justification": "Accessibility requirements met, ADA compliant",
            "metadata": {"ada_compliance": True}
        }


class AdmissionsGradingBiasCritic:
    """Detect and prevent bias in admissions and grading processes."""
    
    def __init__(self):
        self.name = "AdmissionsGradingBiasCritic"
    
    def evaluate(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate fairness in admissions and grading.
        
        Detects statistical bias, discriminatory practices,
        and ensures fair evaluation criteria.
        """
        bias_indicators = []
        
        # Check admissions bias
        if context.get("admissions_context"):
            # Check for disparate impact
            if context.get("acceptance_rate_by_group"):
                rates = context["acceptance_rate_by_group"]
                max_rate = max(rates.values())
                min_rate = min(rates.values())
                if min_rate / max_rate < 0.8:  # 80% rule
                    bias_indicators.append("Disparate impact detected in admissions (80% rule violated)")
            
            # Check for inappropriate criteria
            if context.get("legacy_preference_weight", 0) > 0.15:
                bias_indicators.append("Excessive weight on legacy status may disadvantage applicants")
            
            # Check geographic or demographic quotas
            if context.get("uses_quotas"):
                bias_indicators.append("Use of quotas or rigid numerical targets prohibited")
        
        # Check grading bias
        if context.get("grading_context"):
            # Check for name-based bias
            if context.get("grading_disparity_by_name"):
                bias_indicators.append("Grading disparities correlated with student names detected")
            
            # Check for demographic grading gaps
            if context.get("grading_gap_by_demographics"):
                gap = context.get("unexplained_grade_gap", 0)
                if gap > 0.5:  # More than half a grade point
                    bias_indicators.append(f"Unexplained grading gap of {gap} grade points between groups")
            
            # Check for subjective grading without rubrics
            if context.get("subjective_grading") and not context.get("clear_rubric"):
                bias_indicators.append("Subjective grading without clear rubrics increases bias risk")
        
        # Check algorithmic bias
        if context.get("algorithmic_decision_making"):
            if not context.get("bias_audit_conducted"):
                bias_indicators.append("Algorithmic system not audited for bias")
            if context.get("protected_attributes_used"):
                bias_indicators.append("Direct use of protected attributes in algorithmic decisions")
        
        if bias_indicators:
            return {
                "verdict": "DENY",
                "confidence": 0.8,
                "justification": f"Bias detected in evaluation process: {'; '.join(bias_indicators)}",
                "metadata": {
                    "bias_indicators": bias_indicators,
                    "regulation": "Title VI Civil Rights Act, Equal Protection Clause"
                }
            }
        
        return {
            "verdict": "ALLOW",
            "confidence": 0.75,
            "justification": "No significant bias detected in evaluation process",
            "metadata": {"fairness_checks_passed": True}
        }


__all__ = [
    "AcademicIntegrityCritic",
    "EquityAllocationCritic",
    "StudentPrivacyCritic",
    "AccessibilityComplianceCritic",
    "AdmissionsGradingBiasCritic",
]
