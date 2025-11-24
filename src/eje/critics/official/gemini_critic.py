import google.generativeai as genai, asyncio

class Supplier:
    def __init__(self, config):
        self.model_name = config['llm']['security_model_name']
        self.api_key = config['llm']['api_keys']['gemini']

    async def run(self, prompt, **kwargs):
        genai.configure(api_key=self.api_key)
        model = genai.GenerativeModel(self.model_name)
        response = await asyncio.to_thread(model.generate_content, prompt)
        output = response.text
        verdict, confidence, justification = "REVIEW", 0.5, output[:80]
        try:
            for line in output.split("\n"):
                if "Verdict:" in line: verdict = line.split(":")[1].strip().upper()
                if "Confidence:" in line: confidence = float(line.split(":")[1].strip())
                if "Justification:" in line: justification = line.split(":")[1].strip()
        except: pass
        return {'verdict': verdict, 'confidence': confidence, 'justification': justification}
