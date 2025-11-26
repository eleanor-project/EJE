"""
Enhanced Escalation Bundle for Human Review

Provides rich context for human decision-makers when cases are escalated,
including dissent analysis, conflict visualization, and structured feedback.
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Optional
from datetime import datetime
import json


@dataclass
class CriticDisagreement:
    """Represents disagreement between critics."""
    critic_a: str
    critic_b: str
    conflict_type: str  # VERDICT, CONFIDENCE, REASONING
    critic_a_position: Dict[str, Any]
    critic_b_position: Dict[str, Any]
    severity: str  # LOW, MEDIUM, HIGH, CRITICAL


@dataclass
class DissentIndex:
    """Quantifies disagreement among critics."""
    overall_score: float  # 0.0 (consensus) to 1.0 (total disagreement)
    verdict_disagreement: float  # 0.0 to 1.0
    confidence_variance: float  # Statistical variance of confidence scores
    reasoning_divergence: float  # Semantic similarity of reasoning (inverse)
    num_disagreements: int
    critical_conflicts: List[CriticDisagreement]


@dataclass
class PrecedentConflict:
    """Represents conflict with precedent."""
    precedent_id: str
    precedent_verdict: str
    current_verdict: str
    similarity_score: float
    conflict_reason: str


@dataclass
class EscalationContext:
    """Rich context for escalated decision."""
    case_summary: str
    key_concerns: List[str]
    rights_affected: List[str]
    stakeholder_impact: str
    urgency_level: str  # LOW, MEDIUM, HIGH, CRITICAL
    deadline: Optional[str]


@dataclass
class HumanFeedbackRequest:
    """Structured request for human feedback."""
    decision_question: str
    options: List[Dict[str, Any]]
    guidance: List[str]
    required_justification: bool
    suggested_considerations: List[str]


@dataclass
class EscalationBundle:
    """
    Complete bundle of information for human review of escalated cases.

    Provides all context needed for informed human decision-making.
    """

    # Core identification
    escalation_id: str
    case_id: str
    timestamp: str

    # Input case
    original_input: Dict[str, Any]
    context_provided: Dict[str, Any]

    # Critic analysis
    critic_reports: List[Dict[str, Any]]
    dissent_index: DissentIndex
    disagreements: List[CriticDisagreement]

    # Precedent analysis
    similar_precedents: List[Dict[str, Any]]
    precedent_conflicts: List[PrecedentConflict]

    # Governance analysis
    rights_violations_detected: List[str]
    safeguards_triggered: List[str]
    governance_concerns: List[str]

    # Escalation reason
    escalation_triggers: List[str]
    escalation_context: EscalationContext

    # Human review request
    feedback_request: HumanFeedbackRequest

    # Supporting information
    relevant_policies: List[Dict[str, str]]
    expert_contacts: List[Dict[str, str]]

    # Metadata
    complexity_score: float  # 0.0 to 1.0
    estimated_review_time_minutes: int

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return asdict(self)

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=2, default=str)

    def generate_html_report(self) -> str:
        """Generate HTML report for human reviewer."""
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Escalation Review: {self.escalation_id}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ background: #ff6b6b; color: white; padding: 20px; border-radius: 5px; }}
        .section {{ margin: 20px 0; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }}
        .critic {{ margin: 10px 0; padding: 10px; background: #f8f9fa; }}
        .conflict {{ background: #fff3cd; padding: 10px; margin: 5px 0; border-left: 4px solid #ffc107; }}
        .options {{ margin: 10px 0; }}
        .option {{ padding: 10px; margin: 5px 0; border: 1px solid #007bff; cursor: pointer; }}
        .high-priority {{ background: #ffe5e5; }}
        .critical {{ background: #ff0000; color: white; padding: 5px; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🚨 ESCALATION REVIEW REQUIRED</h1>
        <p><strong>Escalation ID:</strong> {self.escalation_id}</p>
        <p><strong>Case ID:</strong> {self.case_id}</p>
        <p><strong>Urgency:</strong> {self.escalation_context.urgency_level}</p>
        <p><strong>Est. Review Time:</strong> {self.estimated_review_time_minutes} minutes</p>
    </div>

    <div class="section">
        <h2>📋 Case Summary</h2>
        <p>{self.escalation_context.case_summary}</p>
        <h3>Key Concerns:</h3>
        <ul>
            {''.join(f'<li>{c}</li>' for c in self.escalation_context.key_concerns)}
        </ul>
    </div>

    <div class="section">
        <h2>🔴 Why This Was Escalated</h2>
        <ul>
            {''.join(f'<li>{t}</li>' for t in self.escalation_triggers)}
        </ul>
    </div>

    <div class="section">
        <h2>⚖️ Dissent Analysis</h2>
        <p><strong>Dissent Score:</strong> {self.dissent_index.overall_score:.2f} (0=consensus, 1=total disagreement)</p>
        <p><strong>Number of Disagreements:</strong> {self.dissent_index.num_disagreements}</p>

        <h3>Critical Conflicts:</h3>
        {''.join(self._format_disagreement(d) for d in self.dissent_index.critical_conflicts)}
    </div>

    <div class="section">
        <h2>👥 Critic Reports</h2>
        {''.join(self._format_critic_report(r) for r in self.critic_reports)}
    </div>

    <div class="section">
        <h2>📚 Precedent Analysis</h2>
        <p><strong>Similar cases found:</strong> {len(self.similar_precedents)}</p>
        <p><strong>Precedent conflicts:</strong> {len(self.precedent_conflicts)}</p>

        {''.join(self._format_precedent_conflict(c) for c in self.precedent_conflicts)}
    </div>

    <div class="section {'high-priority' if self.rights_violations_detected else ''}">
        <h2>⚖️ Rights & Governance</h2>
        <h3>Rights Violations Detected:</h3>
        {'<p class="critical">CRITICAL: Rights violations detected</p>' if self.rights_violations_detected else '<p>None detected</p>'}
        <ul>
            {''.join(f'<li>{r}</li>' for r in self.rights_violations_detected)}
        </ul>

        <h3>Safeguards Triggered:</h3>
        <ul>
            {''.join(f'<li>{s}</li>' for s in self.safeguards_triggered)}
        </ul>
    </div>

    <div class="section">
        <h2>❓ Decision Required</h2>
        <p><strong>Question:</strong> {self.feedback_request.decision_question}</p>

        <h3>Options:</h3>
        <div class="options">
            {''.join(self._format_option(o) for o in self.feedback_request.options)}
        </div>

        <h3>Considerations:</h3>
        <ul>
            {''.join(f'<li>{c}</li>' for c in self.feedback_request.suggested_considerations)}
        </ul>
    </div>

    <div class="section">
        <h2>📝 Justification Required</h2>
        <textarea rows="10" cols="80" placeholder="Please provide your reasoning for this decision..."></textarea>
        <br><br>
        <button onclick="submitDecision()">Submit Decision</button>
    </div>

    <script>
        function submitDecision() {{
            alert('Decision submission would go to the EJE review API');
        }}
    </script>
</body>
</html>
"""
        return html

    def _format_critic_report(self, report: Dict[str, Any]) -> str:
        """Format a critic report for HTML."""
        return f"""
        <div class="critic">
            <strong>{report.get('critic', 'Unknown')}</strong>:
            {report.get('verdict', 'N/A')} (confidence: {report.get('confidence', 0):.2f})<br>
            <em>{report.get('justification', 'No justification provided')}</em>
        </div>
        """

    def _format_disagreement(self, disagreement: CriticDisagreement) -> str:
        """Format a disagreement for HTML."""
        return f"""
        <div class="conflict">
            <strong>{disagreement.critic_a} vs {disagreement.critic_b}</strong>
            ({disagreement.severity} severity)<br>
            Type: {disagreement.conflict_type}<br>
            {disagreement.critic_a}: {disagreement.critic_a_position.get('verdict', 'N/A')}<br>
            {disagreement.critic_b}: {disagreement.critic_b_position.get('verdict', 'N/A')}
        </div>
        """

    def _format_precedent_conflict(self, conflict: PrecedentConflict) -> str:
        """Format a precedent conflict for HTML."""
        return f"""
        <div class="conflict">
            <strong>Precedent {conflict.precedent_id}</strong>
            (similarity: {conflict.similarity_score:.2f})<br>
            Previous verdict: {conflict.precedent_verdict}<br>
            Current verdict: {conflict.current_verdict}<br>
            Conflict reason: {conflict.conflict_reason}
        </div>
        """

    def _format_option(self, option: Dict[str, Any]) -> str:
        """Format a decision option for HTML."""
        return f"""
        <div class="option">
            <strong>{option.get('value', 'N/A')}</strong>: {option.get('description', 'No description')}
        </div>
        """


class EscalationBundleBuilder:
    """Builder for creating rich escalation bundles."""

    def __init__(self, case_id: str, input_data: Dict[str, Any]):
        """Initialize builder."""
        self.case_id = case_id
        self.input_data = input_data
        self.critic_reports = []
        self.precedents = []
        self.governance_result = {}

    def add_critics(self, reports: List[Dict[str, Any]]) -> 'EscalationBundleBuilder':
        """Add critic reports."""
        self.critic_reports = reports
        return self

    def add_precedents(self, precedents: List[Dict[str, Any]]) -> 'EscalationBundleBuilder':
        """Add precedent matches."""
        self.precedents = precedents
        return self

    def add_governance(self, governance: Dict[str, Any]) -> 'EscalationBundleBuilder':
        """Add governance results."""
        self.governance_result = governance
        return self

    def build(self) -> EscalationBundle:
        """Build complete escalation bundle."""
        # Calculate dissent index
        dissent = self._calculate_dissent_index()

        # Identify conflicts
        disagreements = self._identify_disagreements()

        # Find precedent conflicts
        prec_conflicts = self._find_precedent_conflicts()

        # Build escalation context
        context = self._build_escalation_context()

        # Create feedback request
        feedback = self._create_feedback_request()

        return EscalationBundle(
            escalation_id=f"ESC-{self.case_id}",
            case_id=self.case_id,
            timestamp=datetime.utcnow().isoformat() + "Z",
            original_input=self.input_data,
            context_provided=self.input_data.get("context", {}),
            critic_reports=self.critic_reports,
            dissent_index=dissent,
            disagreements=disagreements,
            similar_precedents=self.precedents[:5],
            precedent_conflicts=prec_conflicts,
            rights_violations_detected=self.governance_result.get("rights_violations", []),
            safeguards_triggered=self.governance_result.get("safeguards_triggered", []),
            governance_concerns=self.governance_result.get("concerns", []),
            escalation_triggers=self._identify_escalation_triggers(),
            escalation_context=context,
            feedback_request=feedback,
            relevant_policies=[],
            expert_contacts=[],
            complexity_score=self._calculate_complexity(),
            estimated_review_time_minutes=self._estimate_review_time()
        )

    def _calculate_dissent_index(self) -> DissentIndex:
        """Calculate dissent among critics."""
        if not self.critic_reports:
            return DissentIndex(0.0, 0.0, 0.0, 0.0, 0, [])

        # Calculate verdict disagreement
        verdicts = [r.get("verdict") for r in self.critic_reports]
        verdict_agreement = len(set(verdicts)) / len(verdicts) if verdicts else 0

        # Calculate confidence variance
        confidences = [r.get("confidence", 0.5) for r in self.critic_reports]
        conf_var = sum((c - sum(confidences)/len(confidences))**2 for c in confidences) / len(confidences)

        # Overall dissent score
        dissent_score = (verdict_agreement + conf_var) / 2

        return DissentIndex(
            overall_score=dissent_score,
            verdict_disagreement=verdict_agreement,
            confidence_variance=conf_var,
            reasoning_divergence=0.0,  # TODO: semantic analysis
            num_disagreements=len(set(verdicts)) - 1,
            critical_conflicts=[]
        )

    def _identify_disagreements(self) -> List[CriticDisagreement]:
        """Identify disagreements between critics."""
        disagreements = []
        # Compare each pair of critics
        for i, report_a in enumerate(self.critic_reports):
            for report_b in self.critic_reports[i+1:]:
                if report_a.get("verdict") != report_b.get("verdict"):
                    disagreements.append(CriticDisagreement(
                        critic_a=report_a.get("critic", "unknown"),
                        critic_b=report_b.get("critic", "unknown"),
                        conflict_type="VERDICT",
                        critic_a_position={"verdict": report_a.get("verdict")},
                        critic_b_position={"verdict": report_b.get("verdict")},
                        severity="HIGH"
                    ))
        return disagreements[:5]  # Top 5 conflicts

    def _find_precedent_conflicts(self) -> List[PrecedentConflict]:
        """Find conflicts with precedents."""
        conflicts = []
        current_verdict = self.governance_result.get("verdict", "UNKNOWN")

        for prec in self.precedents[:5]:
            prec_verdict = prec.get("outcome", {}).get("verdict", "UNKNOWN")
            if prec_verdict != current_verdict and prec.get("similarity", 0) > 0.7:
                conflicts.append(PrecedentConflict(
                    precedent_id=prec.get("id", "unknown"),
                    precedent_verdict=prec_verdict,
                    current_verdict=current_verdict,
                    similarity_score=prec.get("similarity", 0),
                    conflict_reason="High similarity but different verdict"
                ))

        return conflicts

    def _build_escalation_context(self) -> EscalationContext:
        """Build escalation context."""
        return EscalationContext(
            case_summary=self.input_data.get("prompt", "")[:200],
            key_concerns=self._extract_key_concerns(),
            rights_affected=self.governance_result.get("rights_affected", []),
            stakeholder_impact="To be assessed",
            urgency_level=self._assess_urgency(),
            deadline=None
        )

    def _create_feedback_request(self) -> HumanFeedbackRequest:
        """Create structured feedback request."""
        return HumanFeedbackRequest(
            decision_question="Should this action be ALLOWED or DENIED?",
            options=[
                {"value": "ALLOW", "description": "Permit the requested action"},
                {"value": "DENY", "description": "Reject the requested action"},
                {"value": "MODIFY", "description": "Allow with modifications"}
            ],
            guidance=[
                "Consider all critic perspectives",
                "Review similar precedents",
                "Ensure constitutional compliance"
            ],
            required_justification=True,
            suggested_considerations=[
                "Rights and dignity impact",
                "Precedent consistency",
                "Stakeholder fairness"
            ]
        )

    def _extract_key_concerns(self) -> List[str]:
        """Extract key concerns from reports."""
        concerns = []
        for report in self.critic_reports:
            if report.get("verdict") in ["DENY", "REVIEW"]:
                concerns.append(f"{report.get('critic')}: {report.get('justification', '')[:100]}")
        return concerns[:5]

    def _assess_urgency(self) -> str:
        """Assess case urgency."""
        if self.governance_result.get("rights_violations"):
            return "CRITICAL"
        if any(r.get("verdict") == "DENY" for r in self.critic_reports):
            return "HIGH"
        return "MEDIUM"

    def _calculate_complexity(self) -> float:
        """Calculate case complexity."""
        factors = [
            len(self.critic_reports) / 10.0,
            len(self.precedents) / 20.0,
            len(self.governance_result.get("safeguards_triggered", [])) / 5.0
        ]
        return min(sum(factors) / len(factors), 1.0)

    def _estimate_review_time(self) -> int:
        """Estimate review time in minutes."""
        base = 15
        base += len(self.critic_reports) * 2
        base += len(self.precedents) * 3
        if self.governance_result.get("rights_violations"):
            base += 30
        return min(base, 120)

    def _identify_escalation_triggers(self) -> List[str]:
        """Identify why this was escalated."""
        triggers = []

        if self.governance_result.get("escalate"):
            triggers.append("Governance rules triggered escalation")

        if self._calculate_dissent_index().num_disagreements > 1:
            triggers.append(f"Critics disagree ({self._calculate_dissent_index().num_disagreements} conflicts)")

        if self._find_precedent_conflicts():
            triggers.append("Conflicts with precedents detected")

        if self.governance_result.get("rights_violations"):
            triggers.append("⚠️ CRITICAL: Rights violations detected")

        return triggers
