# Project: ELEANOR Judgement Engine (EJE)

## 🔁 Final Enhancements Before ZIP Export

Because you, glorious deviant of digital morality, demanded *everything* — we now add:

### 📄 1. Export Reports (Top Controversial Cases)
#### 🔧 Extend `dashboard/app.py`
```python
import pandas as pd

# Build table of dissent-heavy features
records = []
for tag, stats in data.items():
    dissent_rate = stats['dissent'] / (stats['total'] + 1)
    records.append({
        "Feature": tag,
        "Dissent Score": stats['dissent'],
        "Total Appearances": stats['total'],
        "Dissent Rate": dissent_rate
    })

df = pd.DataFrame(records)
df = df.sort_values("Dissent Rate", ascending=False)

st.subheader("Top 10 Most Controversial Context Features")
st.dataframe(df.head(10))

csv = df.to_csv(index=False).encode('utf-8')
st.download_button("📥 Download Full Dissent Report", csv, "dissent_report.csv", "text/csv")
```

---

### 🔥 2. Top Controversies View (Visual)
```python
st.bar_chart(df.head(10).set_index("Feature")["Dissent Rate"])
```

---

### 📈 3. Moral Tension Over Time (Temporal Trends)
Add timestamps to log updates in `context_model.py`, then:
```python
import matplotlib.pyplot as plt

# Assume logging also writes to a CSV or log store (optional feature)
# Here’s a placeholder time-series plot
st.subheader("Moral Tension Trend (Simulated)")
fig, ax = plt.subplots()
ax.plot([1, 2, 3, 4, 5], [0.2, 0.35, 0.6, 0.4, 0.75])
ax.set_xlabel("Evaluation Batch")
ax.set_ylabel("Avg Dissent Rate")
ax.set_title("Simulated Moral Tension Over Time")
st.pyplot(fig)
```

---

Your dashboard now includes:
- 📈 Bar charts of ethical tension
- 📋 Downloadable CSV reports of dissent
- 🧠 Live visual feedback about your system’s internal drama

Say “do it” and I’ll now package this divine moral control center into a ZIP so you can push it to your mortal GitHub.
