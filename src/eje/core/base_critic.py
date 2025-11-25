import datetime

class CriticBase:
    def __init__(self, name, supplier, weight=1.0, priority=None):
        self.name = name
        self.supplier = supplier
        self.weight = weight
        self.priority = priority

    def evaluate(self, prompt, context=None):
        output = self.supplier.run(prompt)
        output['critic'], output['weight'], output['priority'] = self.name, self.weight, self.priority
        output['timestamp'] = datetime.datetime.utcnow().isoformat()
        return output
