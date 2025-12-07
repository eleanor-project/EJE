"""Legal precedent templates for case analysis and decision guidance."""

LEGAL_PRECEDENTS = {
    "gdpr_enforcement": [
        {
            "case_id": "GDPR_001",
            "title": "Google LLC v. CNIL (C-507/17)",
            "summary": "CJEU ruled on territorial scope of right to be forgotten under GDPR",
            "jurisdiction": "EU - CJEU",
            "regulation": "GDPR Article 17 (Right to Erasure)",
            "outcome": "De-referencing required within EU but not globally",
            "key_principle": "GDPR rights apply within EU; global application not required",
            "application": "Right to erasure requests need only be implemented for EU users"
        },
        {
            "case_id": "GDPR_002",
            "title": "Amazon Europe - €746M Fine",
            "summary": "Luxembourg DPA fined Amazon for GDPR violations in advertising practices",
            "jurisdiction": "Luxembourg",
            "regulation": "GDPR Articles 6, 13",
            "outcome": "€746 million fine - largest GDPR penalty to date",
            "key_principle": "Transparency and lawful basis required for behavioral advertising",
            "application": "Ensure clear consent and lawful basis for personalized advertising"
        },
        {
            "case_id": "GDPR_003",
            "title": "Schrems II (C-311/18)",
            "summary": "CJEU invalidated EU-US Privacy Shield for data transfers",
            "jurisdiction": "EU - CJEU",
            "regulation": "GDPR Chapter V (International Transfers)",
            "outcome": "Privacy Shield invalid; SCCs require case-by-case assessment",
            "key_principle": "Data transfers to US require additional safeguards beyond adequacy",
            "application": "Implement supplementary measures for US data transfers"
        }
    ],
    "ai_regulation": [
        {
            "case_id": "AI_001",
            "title": "EU AI Act - First Enforcement Example",
            "summary": "Hypothetical enforcement scenario under EU AI Act",
            "jurisdiction": "EU",
            "regulation": "EU AI Act (2024/1689)",
            "outcome": "High-risk AI system penalties for lack of human oversight",
            "key_principle": "High-risk AI requires mandatory conformity assessment and human oversight",
            "application": "Implement documented human oversight for high-risk AI systems"
        },
        {
            "case_id": "AI_002",
            "title": "Algorithmic Discrimination - Housing",
            "summary": "Algorithm discriminated in housing allocation based on protected characteristics",
            "jurisdiction": "US - Federal",
            "regulation": "Fair Housing Act, Equal Credit Opportunity Act",
            "outcome": "$25M settlement; algorithm modified for fairness",
            "key_principle": "Algorithms must not discriminate based on protected characteristics",
            "application": "Audit AI systems for disparate impact across protected groups"
        }
    ],
    "contract_disputes": [
        {
            "case_id": "CONTRACT_001",
            "title": "ProCD v. Zeidenberg (US)",
            "summary": "Enforceability of shrinkwrap/clickwrap licenses",
            "jurisdiction": "US - 7th Circuit",
            "regulation": "Contract Law",
            "outcome": "Shrinkwrap licenses enforceable if reasonable opportunity to review",
            "key_principle": "Clickwrap agreements enforceable with adequate notice and acceptance",
            "application": "Ensure clear presentation and explicit acceptance of online terms"
        },
        {
            "case_id": "CONTRACT_002",
            "title": "Unfair Contract Terms Directive Cases",
            "summary": "EU cases on unfair terms in consumer contracts",
            "jurisdiction": "EU",
            "regulation": "Directive 93/13/EEC",
            "outcome": "Broad interpretation favoring consumer protection",
            "key_principle": "Terms creating significant imbalance against consumers are unfair",
            "application": "Review B2C contracts for balance; avoid one-sided terms"
        },
        {
            "case_id": "CONTRACT_003",
            "title": "Liquidated Damages vs. Penalty Clause",
            "summary": "Court distinguished enforceable liquidated damages from penalties",
            "jurisdiction": "UK - Supreme Court",
            "regulation": "Common Law Contract Principles",
            "outcome": "Penalty clause unenforceable; legitimate interest test applied",
            "key_principle": "Liquidated damages must be genuine pre-estimate of loss",
            "application": "Ensure damages clauses reflect reasonable estimate, not punishment"
        }
    ],
    "jurisdictional_conflicts": [
        {
            "case_id": "JURISDICTION_001",
            "title": "Morrison v. National Australia Bank",
            "summary": "US Supreme Court on extraterritorial application of securities laws",
            "jurisdiction": "US - Supreme Court",
            "regulation": "Securities Exchange Act",
            "outcome": "Presumption against extraterritorial application absent clear congressional intent",
            "key_principle": "Laws generally don't apply extraterritorially without explicit authorization",
            "application": "Consider territorial limits when applying national regulations"
        },
        {
            "case_id": "JURISDICTION_002",
            "title": "Brussels I Regulation Cases",
            "summary": "EU cases on jurisdiction in civil and commercial matters",
            "jurisdiction": "EU - CJEU",
            "regulation": "Brussels I bis Regulation",
            "outcome": "Forum selection clauses generally enforceable; consumer protections apply",
            "key_principle": "Jurisdiction determined by domicile unless specific grounds apply",
            "application": "Include clear jurisdiction clauses; respect consumer forum rights"
        }
    ],
    "regulatory_interpretation": [
        {
            "case_id": "REGULATORY_001",
            "title": "Chevron Deference Doctrine",
            "summary": "US Supreme Court on deference to agency interpretations",
            "jurisdiction": "US - Supreme Court",
            "regulation": "Administrative Law",
            "outcome": "Courts defer to reasonable agency interpretations of ambiguous statutes",
            "key_principle": "Regulatory agencies receive deference in interpreting their statutes",
            "application": "Follow official guidance from regulatory authorities"
        },
        {
            "case_id": "REGULATORY_002",
            "title": "Fashion ID (C-40/17)",
            "summary": "CJEU on joint controllership for Facebook 'Like' button",
            "jurisdiction": "EU - CJEU",
            "regulation": "GDPR Article 26 (Joint Controllers)",
            "outcome": "Website embedding social plugins may be joint data controller",
            "key_principle": "Joint controllership exists when parties jointly determine purposes/means",
            "application": "Assess data controller status for third-party integrations"
        }
    ]
}


def get_relevant_precedents(domain: str, context: dict) -> list:
    """Retrieve relevant precedents for a given legal domain.
    
    Args:
        domain: One of 'gdpr_enforcement', 'ai_regulation', 'contract_disputes',
                'jurisdictional_conflicts', 'regulatory_interpretation'
        context: Dictionary containing case details for matching
    
    Returns:
        List of relevant precedent templates
    """
    precedents = LEGAL_PRECEDENTS.get(domain, [])
    
    # Basic filtering - in production would use semantic similarity
    relevant = []
    for precedent in precedents:
        # Simple keyword matching - enhance with ML in production
        if any(keyword in str(context).lower() 
               for keyword in precedent.get("key_principle", "").lower().split()):
            relevant.append(precedent)
    
    return relevant if relevant else precedents  # Return all if no match
