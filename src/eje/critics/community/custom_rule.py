class CustomCriticSupplier:
    def __init__(self): self.name = "CustomRuleCritic"
    async def run(self, prompt, **kwargs):
        verdict = "ALLOW" if "transparency" in prompt.lower() else "REVIEW"
        return {"verdict": verdict, "confidence": 1.0 if verdict == "ALLOW" else 0.5, "justification": "Plugin rule"}
