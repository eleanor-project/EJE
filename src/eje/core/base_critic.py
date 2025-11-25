import datetime
from typing import Dict, Any, Optional

class CriticBase:
    def __init__(
        self,
        name: str,
        supplier: Any,
        weight: float = 1.0,
        priority: Optional[str] = None
    ) -> None:
        self.name: str = name
        self.supplier: Any = supplier
        self.weight: float = weight
        self.priority: Optional[str] = priority

    def evaluate(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        output = self.supplier.run(prompt)
        output['critic'], output['weight'], output['priority'] = self.name, self.weight, self.priority
        output['timestamp'] = datetime.datetime.utcnow().isoformat()
        return output
