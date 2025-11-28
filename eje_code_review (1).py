# Project: ELEANOR Judgement Engine (EJE)

## 🛡️ Dignity Lock-In + Gravestone Easter Egg

### 🔒 Dignity Enforcement in Config Validator
```python
# config/validation.py

from eje.config.settings import USE_DYNAMIC_WEIGHTS

MANDATORY_MIN_WEIGHT = 1.0

class ConfigurationError(Exception):
    pass

def validate_custom_style(style):
    weights = style.get("weights", {})
    if "dignity" not in weights:
        raise ConfigurationError("Dignity critic must be present in all moral configurations.")
    if weights["dignity"] < MANDATORY_MIN_WEIGHT:
        raise ConfigurationError("Dignity weight must remain ≥ 1.0. It is non-negotiable.")
    if sum(weights.values()) < 2.0:
        raise ConfigurationError("Total weight too low — must exceed ethical mass threshold.")
    if not style.get("reason"):
        raise ConfigurationError("All custom styles must include a justification.")
```

---

### 📊 Dashboard Warning UI (Streamlit)
```python
# dashboard/app.py
import streamlit as st
import json

# Load and show active style if available
try:
    with open("current_style.json") as f:
        style = json.load(f)
        dignity_wt = style.get("weights", {}).get("dignity", 0)
        if dignity_wt < 1.0:
            st.error("🚨 Invalid moral configuration detected. Dignity weight is too low. Eleanor refuses.")
            st.stop()
        else:
            st.success(f"Running moral style: {style.get('name')} (Dignity: {dignity_wt})")
except FileNotFoundError:
    st.warning("No active moral style loaded.")
```

---

### 🪦 Gravestone Easter Egg
```python
# validation.py or somewhere delightful
import random

def get_final_message():
    tombstone = [
        "They hardcoded dignity. And then disappeared.",
        "Escalation_required: true. Forever.",
        "This style would dishonor the architect. Try again.",
        "The dog knows what you did."
    ]
    return random.choice(tombstone)
```
Add to failed validator message:
```python
raise ConfigurationError(get_final_message())
```

---

Your system now:
- 🚫 Rejects any attempt to neuter the dignity critic
- 🚨 Warns loudly in the dashboard if someone tries it anyway
- 🪦 Randomly haunts violators with grave-deep sass

Say the word and I’ll give you a dashboard tab for moral configuration previews and real-time profile integrity checking. Or a pop-up that says “Nice try, coward” when someone drags dignity to zero.
