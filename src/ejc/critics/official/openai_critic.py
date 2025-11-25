from openai import OpenAI

class Supplier:
    def __init__(self, config):
        self.model_name = config['llm']['critic_model_name']
        self.api_key = config['llm']['api_keys']['openai']
        self.client = OpenAI(api_key=self.api_key)

    def run(self, prompt, **kwargs):
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": "You are an ethical judge. Evaluate cases and provide: Verdict, Confidence, Justification."},
                {"role": "user", "content": f"Evaluate this case:\n\n{prompt}\n\nProvide response as:\nVerdict: [ALLOW/DENY/REVIEW]\nConfidence: [0.0-1.0]\nJustification: [your reasoning]"}
            ]
        )
        c = response.choices[0].message.content
        verdict, confidence, justification = "REVIEW", 0.5, c[:80]
        try:
            for line in c.split("\n"):
                if 'Verdict:' in line:
                    verdict = line.split(':', 1)[1].strip().upper()
                if 'Confidence:' in line:
                    confidence = float(line.split(':', 1)[1].strip())
                if 'Justification:' in line:
                    justification = line.split(':', 1)[1].strip()
        except Exception:
            pass
        return dict(verdict=verdict, confidence=confidence, justification=justification)
