# Project: ELEANOR Judgement Engine (EJE)

## 📊 Streamlit Moral Dashboard + Toggle Module

You now get a full visual command deck for observing moral friction in real time.

---

### 📁 Additions
```
eje/
├── dashboard/
│   ├── __init__.py
│   └── app.py              # Streamlit interface
├── config/
│   ├── __init__.py
│   └── settings.py         # Toggle features
```

---

### 🔧 `config/settings.py`
```python
USE_DYNAMIC_WEIGHTS = True
SHOW_DEBUG_OUTPUT = False
```

Use anywhere:
```python
from eje.config.settings import USE_DYNAMIC_WEIGHTS
```

---

### 🎛️ `dashboard/app.py`
```python
import streamlit as st
import pickle
from eje.learning.context_model import MODEL_PATH

st.set_page_config(page_title="ELEANOR: Moral Context Tracker", layout="wide")
st.title("📊 ELEANOR Ethical Friction Dashboard")

try:
    with open(MODEL_PATH, "rb") as f:
        data = pickle.load(f)

    if not data:
        st.info("No moral tension data yet. Run some evaluations.")
    else:
        for tag, stats in data.items():
            dissent_rate = stats['dissent'] / (stats['total'] + 1)
            st.markdown(f"**{tag}**")
            st.text(f"Dissent: {stats['dissent']}  |  Total: {stats['total']}  |  Rate: {dissent_rate:.2f}")
            st.progress(min(dissent_rate, 1.0))
except FileNotFoundError:
    st.warning("No data found. Have you run the engine yet?")
```
Run with:
```bash
streamlit run eje/dashboard/app.py
```

---

### 🔥 Bonus: Dashboard Enhancements (Optional)
- Add filtering by top dissent scores
- Display critic weight stats (if weights are adaptive)
- Plot temporal trends in moral stress levels

---

You now have:
- A **toggle system** for dev/ops switches
- A **dashboard** to monitor moral stress in your engine
- A foundation to treat this system like an evolving organism

Would you like me to add support for exporting reports or visualizing the top 10 most controversial inputs?
