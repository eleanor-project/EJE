import openai

class Supplier:
    def __init__(self, config):
        self.model_name = config['llm']['critic_model_name']
        self.api_key = config['llm']['api_keys']['openai']

    async def run(self, prompt, **kwargs):
        openai.api_key = self.api_key
        response = await openai.ChatCompletion.acreate(
            model=self.model_name,
            messages=[
                {"role": "system", "content": "You are an ethical judge. Output: Verdict, Confidence, Justification."},
                {"role": "user", "content": prompt}
            ]
        )
        c = response.choices[0].message.content
        verdict, confidence, justification = "REVIEW", 0.5, c[:80]
        try:
            for line in c.split("\n"):
                if 'Verdict:' in line: verdict=line.split(':')[1].strip().upper()
                if 'Confidence:' in line: confidence=float(line.split(':')[1].strip())
                if 'Justification:' in line: justification=line.split(':')[1].strip()
        except: pass
        return dict(verdict=verdict, confidence=confidence, justification=justification)
