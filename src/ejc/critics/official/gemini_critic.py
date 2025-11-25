import google.generativeai as genai

class Supplier:
    def __init__(self, config):
        self.model_name = config['llm']['security_model_name']
        self.api_key = config['llm']['api_keys']['gemini']
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel(self.model_name)

    def run(self, prompt, **kwargs):
        response = self.model.generate_content(
            f"You are a security-focused ethical judge. Evaluate the following case:\n\n{prompt}\n\nProvide your response as:\nVerdict: [ALLOW/DENY/REVIEW]\nConfidence: [0.0-1.0]\nJustification: [your reasoning]"
        )
        output = response.text
        verdict, confidence, justification = "REVIEW", 0.5, output[:80]
        try:
            for line in output.split("\n"):
                if "Verdict:" in line:
                    verdict = line.split(":", 1)[1].strip().upper()
                if "Confidence:" in line:
                    confidence = float(line.split(":", 1)[1].strip())
                if "Justification:" in line:
                    justification = line.split(":", 1)[1].strip()
        except Exception:
            pass
        return {'verdict': verdict, 'confidence': confidence, 'justification': justification}
