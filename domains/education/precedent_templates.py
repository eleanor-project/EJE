"""Education precedent templates for case analysis and decision guidance."""

EDUCATION_PRECEDENTS = {
    "academic_integrity": [
        {
            "case_id": "AI_001",
            "title": "University Plagiarism Case - Proper Process Required",
            "summary": "University found student plagiarized term paper but failed to provide adequate due process",
            "jurisdiction": "US - Federal Circuit",
            "regulation": "Due Process Clause, University Honor Code",
            "outcome": "Disciplinary action overturned; university required to provide hearing with representation",
            "key_principle": "Students facing serious academic discipline have right to notice, hearing, and representation",
            "application": "Ensure proper due process procedures before imposing academic penalties for integrity violations",
        },
        {
            "case_id": "AI_002",
            "title": "Contract Cheating Detection and Penalties",
            "summary": "Student purchased essay from online service; caught through plagiarism detection software",
            "jurisdiction": "US - State Court",
            "regulation": "Academic Honor Code",
            "outcome": "Expulsion upheld; university demonstrated clear policy and multiple warnings",
            "key_principle": "Contract cheating is serious violation; penalties must be proportionate and clearly communicated",
            "application": "Maintain clear policies on unauthorized assistance and use detection tools consistently",
        },
    ],
    "equity_allocation": [
        {
            "case_id": "EQUITY_001",
            "title": "School Funding Inequity - Constitutional Violation",
            "summary": "State funding formula resulted in significantly lower per-pupil spending in poor districts",
            "jurisdiction": "US - State Supreme Court",
            "regulation": "State Constitution Education Clause, Equal Protection",
            "outcome": "Funding system declared unconstitutional; state ordered to equalize resources",
            "key_principle": "Students have right to substantially equal educational opportunities regardless of district wealth",
            "application": "Monitor and remedy significant funding disparities between advantaged and disadvantaged students",
        },
        {
            "case_id": "EQUITY_002",
            "title": "Advanced Placement Access Discrimination",
            "summary": "School district offered AP courses only in affluent schools, not in majority-minority schools",
            "jurisdiction": "US - DOJ Settlement",
            "regulation": "Title VI Civil Rights Act",
            "outcome": "$2M settlement; district required to offer AP courses at all high schools",
            "key_principle": "Educational opportunities must be distributed equitably across all student demographics",
            "application": "Ensure advanced coursework, quality teachers, and resources available to all student groups",
        },
    ],
    "student_privacy": [
        {
            "case_id": "FERPA_001",
            "title": "Gonzaga University v. Doe (2002)",
            "summary": "University disclosed student disciplinary records without consent; student sued",
            "jurisdiction": "US Supreme Court",
            "regulation": "FERPA (20 U.S.C. § 1232g)",
            "outcome": "No private right of action under FERPA, but institution lost federal funding",
            "key_principle": "FERPA prohibits unauthorized disclosure of education records; enforcement through funding withdrawal",
            "application": "Obtain proper consent before disclosing any education records; limited exceptions apply",
        },
        {
            "case_id": "FERPA_002",
            "title": "Third-Party Ed Tech Data Sharing Violation",
            "summary": "School district shared student data with ed tech company without adequate safeguards",
            "jurisdiction": "US - ED Office Investigation",
            "regulation": "FERPA, State Student Privacy Laws",
            "outcome": "District found in violation; required to implement data privacy training and audits",
            "key_principle": "Schools must ensure third-party vendors protect student data as \"school officials\"",
            "application": "Vet ed tech vendors for FERPA compliance; include data protection clauses in contracts",
        },
    ],
    "accessibility_compliance": [
        {
            "case_id": "ADA_001",
            "title": "Southeastern Community College v. Davis (1979)",
            "summary": "Nursing program denied admission to deaf student; claimed inability to accommodate",
            "jurisdiction": "US Supreme Court",
            "regulation": "Section 504 Rehabilitation Act",
            "outcome": "School not required to make \"fundamental alterations\" or accommodations creating undue hardship",
            "key_principle": "Reasonable accommodations required unless they fundamentally alter program or create undue burden",
            "application": "Provide accommodations unless demonstrable fundamental alteration or undue hardship",
        },
        {
            "case_id": "ADA_002",
            "title": "Digital Accessibility - OCR Resolution",
            "summary": "University's online courses not accessible to blind students using screen readers",
            "jurisdiction": "US - OCR Investigation",
            "regulation": "ADA Title II, Section 504",
            "outcome": "Resolution agreement requiring WCAG 2.1 AA compliance for all digital content",
            "key_principle": "Digital educational content must be accessible to students with disabilities",
            "application": "Ensure all online materials, videos, and platforms meet WCAG 2.1 AA accessibility standards",
        },
        {
            "case_id": "ADA_003",
            "title": "Testing Accommodations - Extended Time",
            "summary": "Student with ADHD denied extended time on standardized test despite IEP",
            "jurisdiction": "US - District Court",
            "regulation": "IDEA, Section 504, ADA",
            "outcome": "School ordered to provide accommodation; damages awarded for emotional distress",
            "key_principle": "Accommodations specified in IEP or 504 plan must be provided for all assessments",
            "application": "Honor all accommodations in IEPs and 504 plans; train staff on implementation",
        },
    ],
    "admissions_grading_bias": [
        {
            "case_id": "BIAS_001",
            "title": "Grutter v. Bollinger (2003)",
            "summary": "Law school used race as factor in holistic admissions review",
            "jurisdiction": "US Supreme Court",
            "regulation": "Equal Protection Clause, Title VI",
            "outcome": "Narrowly tailored race-conscious admissions upheld to achieve diversity",
            "key_principle": "Race may be one factor in holistic review; quotas and mechanical approaches prohibited",
            "application": "If considering race, use narrow holistic review; avoid quotas or point systems",
        },
        {
            "case_id": "BIAS_002",
            "title": "Disparate Impact in Standardized Testing",
            "summary": "School district used single test score for gifted program placement; significant racial disparity",
            "jurisdiction": "US - OCR Investigation",
            "regulation": "Title VI Civil Rights Act",
            "outcome": "District required to implement multiple criteria for identification; reduce test weight",
            "key_principle": "Practices with disparate impact require educational necessity justification",
            "application": "Use multiple measures for high-stakes decisions; monitor for demographic disparities",
        },
        {
            "case_id": "BIAS_003",
            "title": "Subjective Grading Bias - Name Experiment",
            "summary": "Study showed identical work graded higher when attributed to stereotypically white names",
            "jurisdiction": "Research Study / Best Practice",
            "regulation": "Professional Ethics, Title VI",
            "outcome": "Institutions adopting blind grading practices show reduced bias",
            "key_principle": "Implicit bias affects grading; procedural safeguards reduce discriminatory outcomes",
            "application": "Implement blind grading where feasible; use clear rubrics to reduce subjectivity",
        },
    ],
}


def get_relevant_precedents(domain: str, context: dict) -> list:
    """Retrieve relevant precedents for a given domain and context.
    
    Args:
        domain: One of 'academic_integrity', 'equity_allocation', 'student_privacy',
                'accessibility_compliance', 'admissions_grading_bias'
        context: Dictionary containing case details for matching
    
    Returns:
        List of relevant precedent templates
    """
    precedents = EDUCATION_PRECEDENTS.get(domain, [])
    
    # Basic filtering - in production would use semantic similarity
    relevant = []
    for precedent in precedents:
        # Simple keyword matching - enhance with ML in production
        if any(keyword in str(context).lower() 
               for keyword in precedent.get("key_principle", "").lower().split()):
            relevant.append(precedent)
    
    return relevant if relevant else precedents  # Return all if no match
