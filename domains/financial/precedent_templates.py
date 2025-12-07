"""Financial services precedent templates for case analysis and decision guidance."""

FINANCIAL_PRECEDENTS = {
    "aml": [
        {
            "case_id": "BSA_001",
            "title": "Structuring Detection and Reporting",
            "summary": "Bank failed to file SARs for customer making sequential deposits just under $10,000 reporting threshold",
            "jurisdiction": "US - Federal",
            "regulation": "Bank Secrecy Act, 31 USC 5324",
            "outcome": "$100M fine, enhanced monitoring required",
            "key_principle": "Financial institutions must detect and report structuring patterns regardless of threshold",
            "application": "Flag any pattern of transactions designed to evade reporting requirements",
        },
        {
            "case_id": "AML_FATF_002",
            "title": "High-Risk Jurisdiction Transaction Review",
            "summary": "Inadequate enhanced due diligence for wire transfers to FATF high-risk countries",
            "jurisdiction": "International - FATF",
            "regulation": "FATF Recommendation 10, 19",
            "outcome": "Consent order requiring enhanced CDD procedures",
            "key_principle": "Transactions involving high-risk jurisdictions require enhanced scrutiny and documentation",
            "application": "Apply additional verification for any transaction involving sanctioned or high-risk countries",
        },
    ],
    "kyc": [
        {
            "case_id": "KYC_CDD_001",
            "title": "Customer Due Diligence Requirements",
            "summary": "Financial institution failed to verify beneficial ownership of shell companies",
            "jurisdiction": "US - FinCEN",
            "regulation": "CDD Rule, 31 CFR 1010.230",
            "outcome": "$50M penalty, customer base review required",
            "key_principle": "Must identify and verify beneficial owners of legal entity customers",
            "application": "Always verify ultimate beneficial ownership for business accounts, especially shell entities",
        },
        {
            "case_id": "PEP_001",
            "title": "Politically Exposed Person Monitoring",
            "summary": "Bank accepted large deposits from PEP without enhanced due diligence",
            "jurisdiction": "EU - AMLD",
            "regulation": "4th Anti-Money Laundering Directive",
            "outcome": "€25M fine, account relationship terminated",
            "key_principle": "PEPs require ongoing enhanced due diligence and source of wealth verification",
            "application": "Screen for PEP status and apply continuous enhanced monitoring",
        },
    ],
    "fair_lending": [
        {
            "case_id": "ECOA_001",
            "title": "Disparate Impact in Credit Decisioning",
            "summary": "Lender's credit scoring model had disparate impact on protected class",
            "jurisdiction": "US - CFPB",
            "regulation": "Equal Credit Opportunity Act, 15 USC 1691",
            "outcome": "$33M settlement, $25M consumer redress",
            "key_principle": "Credit policies with disparate impact on protected classes violate ECOA even without intent",
            "application": "Regularly test models for disparate impact using 80% rule; document business necessity",
        },
        {
            "case_id": "REDLINING_002",
            "title": "Geographic Discrimination in Lending",
            "summary": "Mortgage lender avoided minority neighborhoods through branch placement and marketing",
            "jurisdiction": "US - DOJ",
            "regulation": "Fair Housing Act, 42 USC 3605",
            "outcome": "$21M settlement, loan subsidy program required",
            "key_principle": "Lenders cannot discriminate based on neighborhood racial composition",
            "application": "Ensure lending policies and marketing are geographically neutral regarding protected classes",
        },
    ],
    "fiduciary_duty": [
        {
            "case_id": "FIDUCIARY_001",
            "title": "Duty of Loyalty - Conflict of Interest",
            "summary": "Investment advisor recommended proprietary products without adequate disclosure of conflicts",
            "jurisdiction": "US - SEC",
            "regulation": "Investment Advisers Act of 1940, Section 206",
            "outcome": "$15M disgorgement, advisory license suspended",
            "key_principle": "Advisors must disclose all material conflicts and cannot prioritize own interests over clients",
            "application": "Fully disclose conflicts and compensation arrangements; prioritize client best interest",
        },
        {
            "case_id": "SUITABILITY_002",
            "title": "Unsuitable Investment Recommendations",
            "summary": "Broker recommended high-risk investments to elderly investors without considering suitability",
            "jurisdiction": "US - FINRA",
            "regulation": "FINRA Rule 2111 (Suitability)",
            "outcome": "$3M fine, $1M restitution, broker barred",
            "key_principle": "Recommendations must be suitable based on customer's profile, needs, and circumstances",
            "application": "Document customer risk tolerance, objectives, time horizon; ensure recommendations align",
        },
    ],
    "market_manipulation": [
        {
            "case_id": "MANIPULATION_001",
            "title": "Spoofing and Layering Detection",
            "summary": "Trader placed large orders to manipulate price, then cancelled before execution",
            "jurisdiction": "US - CFTC",
            "regulation": "Dodd-Frank Act Section 747, CEA Section 4c(a)(5)(C)",
            "outcome": "$5M fine, trading ban, criminal prosecution",
            "key_principle": "Placing orders with intent to cancel (spoofing) to manipulate market price is illegal",
            "application": "Monitor for rapid order placement/cancellation patterns; flag suspicious activity immediately",
        },
        {
            "case_id": "INSIDER_001",
            "title": "Insider Trading Prosecution",
            "summary": "Corporate executive traded on material non-public information ahead of merger announcement",
            "jurisdiction": "US - SEC",
            "regulation": "Securities Exchange Act Section 10(b), Rule 10b-5",
            "outcome": "$2M disgorgement, 5 years imprisonment",
            "key_principle": "Trading on material non-public information violates securities laws",
            "application": "Implement information barriers; monitor trading by insiders and tippees",
        },
    ],
}


def get_relevant_precedents(domain: str, context: dict) -> list:
    """Retrieve relevant precedents for a given domain and context.
    
    Args:
        domain: One of 'aml', 'kyc', 'fair_lending', 'fiduciary_duty', 'market_manipulation'
        context: Dictionary containing case details for matching
    
    Returns:
        List of relevant precedent templates
    """
    precedents = FINANCIAL_PRECEDENTS.get(domain, [])
    
    # Basic filtering - in production would use semantic similarity
    relevant = []
    for precedent in precedents:
        # Simple keyword matching - enhance with ML in production
        if any(keyword in str(context).lower() 
               for keyword in precedent.get("key_principle", "").lower().split()):
            relevant.append(precedent)
    
    return relevant if relevant else precedents  # Return all if no match
