from flask import Flask, jsonify, request
import os
import json

app = Flask(__name__)
log_path = "./eleanor_data/log.jsonl"  # Or load from config

@app.route("/")
def index():
    try:
        with open(log_path) as f:
            rows = f.readlines()[-40:]
        return jsonify([json.loads(r) for r in rows])
    except Exception as e:
        return str(e), 500

@app.route("/feedback/<int:event_id>", methods=['POST'])
def feedback(event_id):
    feedback = request.json.get("feedback", "")
    # You would look this up in the audit DB and add feedback.
    return jsonify({"status":"ok", "event":event_id, "fb":feedback})

def serve_dashboard(port=8049):
    app.run(port=port, debug=True)
