# Project: ELEANOR Judgement Engine (EJE)

## 📘 README.md
```markdown
# ELEANOR: Ethical Learning and Navigation with Autonomous Operational Reasoning

ELEANOR is an AI-powered judgment engine that:
- Evaluates ethical decisions via modular critics (dignity, autonomy, fairness, precaution)
- Learns from moral friction via recursive context modeling
- Supports dynamic critic weighting and human-in-the-loop review
- Logs precedent cases and monitors tension in a Streamlit dashboard

## 🧱 Project Structure
```
EJE-main/
├── eje/
│   ├── api/              → FastAPI app + endpoints
│   ├── config/           → Feature toggles (dynamic weights, debug)
│   ├── dashboard/        → Streamlit visualizations
│   ├── db/               → SQLite escalation/precedent logger
│   └── learning/         → Recursive context learner
```

## 🚀 Getting Started
1. Clone this repo.
2. Create a virtual environment:
```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
```
3. Run the API:
```bash
uvicorn eje.api.app:create_app --factory --reload
```
4. Run the dashboard:
```bash
streamlit run eje/dashboard/app.py
```

## ⚙️ Configurable Features
Edit `eje/config/settings.py`:
```python
USE_DYNAMIC_WEIGHTS = True  # Toggle adaptive critic influence
SHOW_DEBUG_OUTPUT = False   # Enable verbose logging
```

## 🧪 Testing
```bash
pytest tests/
```

## 📊 Features
- Moral tension detection
- Precedent-based evaluation shortcuts
- Controversy dashboards
- Report downloads
```

---

## 🛠 deploy.sh — Deployment Script
```bash
#!/bin/bash

# Activate virtual env and start everything
source venv/bin/activate

# Start API
echo "Launching ELEANOR API on http://127.0.0.1:8000 ..."
uvicorn eje.api.app:create_app --factory --host 0.0.0.0 --port 8000 &

# Start dashboard
echo "Launching Streamlit dashboard on http://localhost:8501 ..."
streamlit run eje/dashboard/app.py
```

chmod +x deploy.sh
./deploy.sh
```

Let me know if you want a Dockerfile to containerize this little ethical oracle or push instructions for GitHub.
