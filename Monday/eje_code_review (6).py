# Project: ELEANOR Judgement Engine (EJE)

## 🔁 Recursive Context Learning — Fully Activated

The ContextLearner is now fully integrated. It tracks dissent per feature, learns which parts of context cause moral conflict, and helps prioritize sensitive cases in future evaluations.

---

### 📁 New Module: `learning/context_model.py`
```python
import pickle
from collections import defaultdict
from pathlib import Path

MODEL_PATH = Path("context_learner.pkl")

class ContextLearner:
    def __init__(self):
        self.feature_impact = defaultdict(lambda: defaultdict(int))

    def update(self, scenario_id, context, dissent_score):
        for key, value in context.items():
            tag = f"{key}:{value}"
            self.feature_impact[tag]["total"] += 1
            self.feature_impact[tag]["dissent"] += dissent_score

    def importance(self, key, value):
        tag = f"{key}:{value}"
        stats = self.feature_impact.get(tag)
        if not stats:
            return 0
        return stats["dissent"] / stats["total"]

    def save(self):
        with open(MODEL_PATH, "wb") as f:
            pickle.dump(dict(self.feature_impact), f)

    def load(self):
        if MODEL_PATH.exists():
            with open(MODEL_PATH, "rb") as f:
                self.feature_impact = defaultdict(lambda: defaultdict(int), pickle.load(f))
```

---

### 🔧 Modify `critic_engine.py`
```python
from eje.learning.context_model import ContextLearner

context_learner = ContextLearner()
context_learner.load()

def run_critics(input_data):
    context = input_data.get("context", {})
    results = {}
    total_score = 0
    dissent = 0

    for critic_name in ["dignity", "autonomy", "fairness", "precaution"]:
        critic = load_critic(critic_name)
        score, justification = critic.evaluate(context)
        results[critic_name] = {"score": score, "justification": justification}
        total_score += score

    avg_score = total_score / 4
    dissent = max(results[c]["score"] for c in results) - min(results[c]["score"] for c in results)

    context_learner.update(input_data.get("scenario_id"), context, dissent)
    context_learner.save()

    return {"average_score": avg_score, "dissent_index": dissent, "by_critic": results}
```

---

### 🎯 Outcome
- You now track dissent per context feature
- Over time, the engine will know which features trigger ethical conflict
- Future versions can use this to:
  - Auto-escalate based on risky features
  - Weigh critic voices differently per feature
  - Visualize moral complexity hotspots

Would you like to add a **dashboard view** of the learned importance scores? Or maybe use this data to **auto-prioritize** which critic gets more influence per case?
