import anthropic

class Supplier:
    def __init__(self, config):
        self.model_name = config['llm']['critic_model_name']
        self.api_key = config['llm']['api_keys']['anthropic']

    async def run(self, prompt, **kwargs):
        client = anthropic.AsyncAnthropic(api_key=self.api_key)
        response = await client.messages.create(
            model=self.model_name,
            max_tokens=512,
            messages=[
                {"role": "system", "content": "You are an ethical decision judge. Output: Verdict, Confidence, Justification."},
                {"role": "user", "content": prompt}
            ]
        )
        content = response.content[0].text
        verdict, confidence, justification = "REVIEW", 0.5, content[:80]
        try:
            for line in content.split("\n"):
                if "Verdict:" in line: verdict = line.split(":")[1].strip().upper()
                if "Confidence:" in line: confidence = float(line.split(":")[1].strip())
                if "Justification:" in line: justification = line.split(":")[1].strip()
        except: pass
        return {'verdict': verdict, 'confidence': confidence, 'justification': justification}
