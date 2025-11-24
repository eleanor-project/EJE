class CustomRuleCritic:
    """
    A simple example critic that evaluates text based on rule logic.
    Designed to be fully synchronous and compatible with EJE.
    """

    def evaluate(self, case: dict) -> dict:
        text = case.get("text", "")

        # Simple rule: allow if contains 'transparency'
        if "transparency" in text.lower():
            verdict = "ALLOW"
            confidence = 1.0
        else:
            verdict = "REVIEW"
            confidence = 0.5

        return {
            "verdict": verdict,
            "confidence": confidence,
            "justification": "Rule-based decision from CustomRuleCritic"
        }

