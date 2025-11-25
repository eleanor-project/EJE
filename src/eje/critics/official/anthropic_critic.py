import anthropic

class Supplier:
    def __init__(self, config):
        self.model_name = config['llm']['critic_model_name']
        self.api_key = config['llm']['api_keys']['anthropic']
        self.client = anthropic.Anthropic(api_key=self.api_key)

    def run(self, prompt, **kwargs):
        response = self.client.messages.create(
            model=self.model_name,
            max_tokens=512,
            messages=[
                {"role": "user", "content": f"You are an ethical decision judge. Evaluate the following case and provide your assessment.\n\nCase: {prompt}\n\nProvide your response in this format:\nVerdict: [ALLOW/DENY/REVIEW]\nConfidence: [0.0-1.0]\nJustification: [your reasoning]"}
            ]
        )
        content = response.content[0].text
        verdict, confidence, justification = "REVIEW", 0.5, content[:80]
        try:
            for line in content.split("\n"):
                if "Verdict:" in line:
                    verdict = line.split(":")[1].strip().upper()
                if "Confidence:" in line:
                    confidence = float(line.split(":")[1].strip())
                if "Justification:" in line:
                    justification = line.split(":", 1)[1].strip()
        except Exception:
            pass
        return {'verdict': verdict, 'confidence': confidence, 'justification': justification}
