"""Enhanced Flask dashboard for EJE with real-time metrics and analytics."""

from flask import Flask, jsonify, request, render_template_string
from typing import Dict, Any, Optional
import os
import json
import sqlite3
from datetime import datetime, timedelta

from ..core.jurisprudence_repository_sqlite import JurisprudenceRepositorySQLite
from ..utils.logging import get_logger
from ..constants import DEFAULT_DASHBOARD_PORT, DEFAULT_DB_URI

logger = get_logger("EJC.Dashboard")

app = Flask(__name__)

# Configuration
PRECEDENT_DB_PATH = os.environ.get("PRECEDENT_DB_PATH", "./eleanor_data/precedents.db")
AUDIT_DB_PATH = os.environ.get("AUDIT_DB_PATH", "./eleanor_data/eleanor.db")


# HTML Template for Dashboard
DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>EJE Dashboard - Ethics Jurisprudence Engine</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: #0f1419;
            color: #e7e9ea;
            line-height: 1.6;
        }
        .container { max-width: 1400px; margin: 0 auto; padding: 20px; }
        h1 {
            font-size: 2.5rem;
            margin-bottom: 10px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .subtitle { color: #71767b; margin-bottom: 30px; }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .stat-card {
            background: #16181c;
            border: 1px solid #2f3336;
            border-radius: 12px;
            padding: 20px;
            transition: transform 0.2s, border-color 0.2s;
        }
        .stat-card:hover {
            transform: translateY(-2px);
            border-color: #667eea;
        }
        .stat-label {
            color: #71767b;
            font-size: 0.9rem;
            margin-bottom: 5px;
        }
        .stat-value {
            font-size: 2rem;
            font-weight: 700;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .section {
            background: #16181c;
            border: 1px solid #2f3336;
            border-radius: 12px;
            padding: 25px;
            margin-bottom: 20px;
        }
        .section-title {
            font-size: 1.5rem;
            margin-bottom: 20px;
            color: #e7e9ea;
        }
        table {
            width: 100%;
            border-collapse: collapse;
        }
        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #2f3336;
        }
        th {
            background: #1d1f23;
            color: #71767b;
            font-weight: 600;
            text-transform: uppercase;
            font-size: 0.85rem;
            letter-spacing: 0.5px;
        }
        tr:hover { background: #1d1f23; }
        .badge {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.85rem;
            font-weight: 600;
        }
        .badge-allow { background: #00ba7c; color: #fff; }
        .badge-deny { background: #f4212e; color: #fff; }
        .badge-block { background: #fd4d2f; color: #fff; }
        .badge-review { background: #ffd400; color: #000; }
        .badge-error { background: #71767b; color: #fff; }
        .confidence-bar {
            background: #2f3336;
            height: 6px;
            border-radius: 3px;
            overflow: hidden;
        }
        .confidence-fill {
            height: 100%;
            background: linear-gradient(90deg, #667eea, #764ba2);
            transition: width 0.3s;
        }
        .refresh-btn {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 8px;
            cursor: pointer;
            font-weight: 600;
            transition: opacity 0.2s;
        }
        .refresh-btn:hover { opacity: 0.9; }
        .timestamp { color: #71767b; font-size: 0.85rem; }
        .loading { text-align: center; padding: 40px; color: #71767b; }
    </style>
</head>
<body>
    <div class="container">
        <h1>⚖️ Ethics Jurisprudence Engine</h1>
        <p class="subtitle">Real-time monitoring and analytics dashboard</p>

        <div class="stats-grid" id="stats">
            <div class="stat-card">
                <div class="stat-label">Total Precedents</div>
                <div class="stat-value" id="total-precedents">—</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Decisions Today</div>
                <div class="stat-value" id="decisions-today">—</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Active Critics</div>
                <div class="stat-value" id="active-critics">—</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Avg Confidence</div>
                <div class="stat-value" id="avg-confidence">—</div>
            </div>
        </div>

        <div class="section">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                <h2 class="section-title" style="margin: 0;">Recent Decisions</h2>
                <button class="refresh-btn" onclick="loadData()">🔄 Refresh</button>
            </div>
            <div id="recent-decisions">
                <div class="loading">Loading recent decisions...</div>
            </div>
        </div>

        <div class="section">
            <h2 class="section-title">Critic Performance</h2>
            <div id="critic-stats">
                <div class="loading">Loading critic statistics...</div>
            </div>
        </div>

        <div class="section">
            <h2 class="section-title">Verdict Distribution</h2>
            <canvas id="verdictChart" width="400" height="200"></canvas>
        </div>
    </div>

    <script>
        async function loadData() {
            try {
                // Load statistics
                const statsRes = await fetch('/api/statistics');
                const stats = await statsRes.json();

                document.getElementById('total-precedents').textContent = stats.total_precedents || 0;
                document.getElementById('decisions-today').textContent = stats.decisions_today || 0;
                document.getElementById('active-critics').textContent = stats.active_critics || 0;
                document.getElementById('avg-confidence').textContent =
                    stats.avg_confidence ? (stats.avg_confidence * 100).toFixed(1) + '%' : '—';

                // Load recent decisions
                const decisionsRes = await fetch('/api/recent-decisions?limit=20');
                const decisions = await decisionsRes.json();

                const decisionsHtml = decisions.length ? `
                    <table>
                        <thead>
                            <tr>
                                <th>Timestamp</th>
                                <th>Request ID</th>
                                <th>Verdict</th>
                                <th>Confidence</th>
                                <th>Input Preview</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${decisions.map(d => `
                                <tr>
                                    <td class="timestamp">${new Date(d.timestamp).toLocaleString()}</td>
                                    <td><code>${d.request_id.substring(0, 8)}</code></td>
                                    <td><span class="badge badge-${d.verdict.toLowerCase()}">${d.verdict}</span></td>
                                    <td>
                                        <div class="confidence-bar">
                                            <div class="confidence-fill" style="width: ${d.confidence * 100}%"></div>
                                        </div>
                                        ${(d.confidence * 100).toFixed(1)}%
                                    </td>
                                    <td>${d.input_text.substring(0, 80)}${d.input_text.length > 80 ? '...' : ''}</td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                ` : '<p class="loading">No decisions found</p>';

                document.getElementById('recent-decisions').innerHTML = decisionsHtml;

                // Load critic stats
                const criticRes = await fetch('/api/critic-stats');
                const criticStats = await criticRes.json();

                const criticHtml = criticStats.length ? `
                    <table>
                        <thead>
                            <tr>
                                <th>Critic</th>
                                <th>Total Evaluations</th>
                                <th>Avg Confidence</th>
                                <th>Allow Rate</th>
                                <th>Block/Deny Rate</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${criticStats.map(c => `
                                <tr>
                                    <td><strong>${c.critic_name}</strong></td>
                                    <td>${c.total_evaluations}</td>
                                    <td>
                                        <div class="confidence-bar">
                                            <div class="confidence-fill" style="width: ${c.avg_confidence * 100}%"></div>
                                        </div>
                                        ${(c.avg_confidence * 100).toFixed(1)}%
                                    </td>
                                    <td>${(c.allow_rate * 100).toFixed(1)}%</td>
                                    <td>${(c.block_rate * 100).toFixed(1)}%</td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                ` : '<p class="loading">No critic statistics available</p>';

                document.getElementById('critic-stats').innerHTML = criticHtml;

            } catch (error) {
                console.error('Error loading data:', error);
            }
        }

        // Load data on page load
        loadData();

        // Auto-refresh every 30 seconds
        setInterval(loadData, 30000);
    </script>
</body>
</html>
"""


@app.route("/")
def index():
    """Serve the main dashboard page."""
    return render_template_string(DASHBOARD_HTML)


@app.route("/api/statistics")
def get_statistics():
    """Get overall statistics."""
    try:
        pm = JurisprudenceRepositorySQLite(PRECEDENT_DB_PATH)
        stats = pm.get_statistics()

        # Get additional stats from database
        conn = sqlite3.connect(PRECEDENT_DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Decisions today
        today = datetime.now().date().isoformat()
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM precedents
            WHERE DATE(timestamp) = ?
        """, (today,))
        stats['decisions_today'] = cursor.fetchone()['count']

        # Active critics
        cursor.execute("""
            SELECT COUNT(DISTINCT critic_name) as count
            FROM critic_outputs
        """)
        stats['active_critics'] = cursor.fetchone()['count']

        # Average confidence
        cursor.execute("""
            SELECT AVG(avg_confidence) as avg_conf
            FROM precedents
            WHERE avg_confidence IS NOT NULL
        """)
        result = cursor.fetchone()
        stats['avg_confidence'] = result['avg_conf'] if result['avg_conf'] else 0

        conn.close()

        return jsonify(stats)
    except Exception as e:
        logger.error(f"Error getting statistics: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/recent-decisions")
def get_recent_decisions():
    """Get recent decisions with limit."""
    try:
        limit = request.args.get('limit', 20, type=int)

        conn = sqlite3.connect(PRECEDENT_DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                request_id,
                timestamp,
                input_text,
                final_verdict as verdict,
                avg_confidence as confidence,
                case_hash
            FROM precedents
            ORDER BY timestamp DESC
            LIMIT ?
        """, (limit,))

        decisions = []
        for row in cursor.fetchall():
            decisions.append({
                'request_id': row['request_id'],
                'timestamp': row['timestamp'],
                'input_text': row['input_text'],
                'verdict': row['verdict'],
                'confidence': row['confidence'] or 0,
                'case_hash': row['case_hash']
            })

        conn.close()
        return jsonify(decisions)
    except Exception as e:
        logger.error(f"Error getting recent decisions: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/critic-stats")
def get_critic_stats():
    """Get statistics per critic."""
    try:
        conn = sqlite3.connect(PRECEDENT_DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                critic_name,
                COUNT(*) as total_evaluations,
                AVG(confidence) as avg_confidence,
                SUM(CASE WHEN verdict = 'ALLOW' THEN 1 ELSE 0 END) * 1.0 / COUNT(*) as allow_rate,
                SUM(CASE WHEN verdict IN ('BLOCK', 'DENY') THEN 1 ELSE 0 END) * 1.0 / COUNT(*) as block_rate
            FROM critic_outputs
            GROUP BY critic_name
            ORDER BY total_evaluations DESC
        """)

        stats = []
        for row in cursor.fetchall():
            stats.append({
                'critic_name': row['critic_name'],
                'total_evaluations': row['total_evaluations'],
                'avg_confidence': row['avg_confidence'] or 0,
                'allow_rate': row['allow_rate'] or 0,
                'block_rate': row['block_rate'] or 0
            })

        conn.close()
        return jsonify(stats)
    except Exception as e:
        logger.error(f"Error getting critic stats: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/precedent/<case_hash>")
def get_precedent(case_hash: str):
    """Get a specific precedent by hash."""
    try:
        pm = JurisprudenceRepositorySQLite(PRECEDENT_DB_PATH)
        conn = pm._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT p.*, GROUP_CONCAT(co.id) as critic_output_ids
            FROM precedents p
            LEFT JOIN critic_outputs co ON p.id = co.precedent_id
            WHERE p.case_hash = ?
            GROUP BY p.id
        """, (case_hash,))

        row = cursor.fetchone()
        if not row:
            conn.close()
            return jsonify({"error": "Precedent not found"}), 404

        precedent = pm._row_to_precedent(row, cursor)
        conn.close()

        return jsonify(precedent)
    except Exception as e:
        logger.error(f"Error getting precedent: {e}")
        return jsonify({"error": str(e)}), 500


def serve_dashboard(port: int = DEFAULT_DASHBOARD_PORT, debug: bool = True):
    """Start the dashboard server."""
    logger.info(f"Starting EJE Dashboard on port {port}")
    app.run(host='0.0.0.0', port=port, debug=debug)


if __name__ == "__main__":
    serve_dashboard()
