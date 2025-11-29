# Project: ELEANOR Judgement Engine (EJE)

## 🔁 Recursive Learning for Contextual Memory

To fully weaponize the concept of **recursive ethical learning**, we’re now adding a system that:
- Updates itself after each decision
- Refines context understanding from usage patterns
- Stores new ethical precedents, tagged and searchable

---

### 🧠 Concept: Recursive Moral Memory
Instead of just logging decisions, the engine will:
- Analyze the *outcome and dissent* of every decision
- Learn which context features most affect critic disagreement
- Use this to weight future critic input, based on precedent clusters

---

### 🧩 Suggested Implementation: Learning from Decisions

#### 🔧 `learning/context_model.py`
```python
from collections import defaultdict

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
```

---

### 🔄 Hook into Evaluation Pipeline
After a decision:
- Compute the dissent index from critic results
- Pass context and dissent to `ContextLearner.update()`
- Store to disk (pickle or lightweight DB)
- In next run, use `importance()` to adjust weights or flags

---

### 🔬 Use Case: Context Bias Prioritization
If the system sees that, say, `"intent:unknown"` causes high dissent, it can:
- Flag such cases for immediate human review
- Increase critic weight for transparency or uncertainty

---

Do you want me to actually implement this module and connect it to the critic engine’s output pipeline?
Because I can make this thing *learn its own blind spots* — and whisper about them like a morally self-aware Roomba.
