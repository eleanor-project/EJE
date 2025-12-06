#!/bin/bash
# Import EJE Grafana dashboards
#
# Usage: ./import_dashboards.sh [GRAFANA_URL] [API_KEY]
# Example: ./import_dashboards.sh http://localhost:3000 eyJrIjoiYWJjMTIz...

set -e

GRAFANA_URL="${1:-http://localhost:3000}"
API_KEY="${2}"
DASHBOARD_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../monitoring/grafana/dashboards" && pwd)"

if [ -z "$API_KEY" ]; then
    echo "Error: Grafana API key required"
    echo "Usage: $0 [GRAFANA_URL] [API_KEY]"
    echo ""
    echo "To get an API key:"
    echo "1. Log into Grafana"
    echo "2. Go to Configuration -> API Keys"
    echo "3. Create a new key with Editor role"
    exit 1
fi

echo "Importing EJE dashboards to $GRAFANA_URL..."
echo ""

# Create EJE folder
echo "Creating EJE folder..."
FOLDER_RESPONSE=$(curl -s -X POST \
    -H "Authorization: Bearer $API_KEY" \
    -H "Content-Type: application/json" \
    -d '{"title":"EJE"}' \
    "$GRAFANA_URL/api/folders" 2>&1)

FOLDER_UID=$(echo "$FOLDER_RESPONSE" | grep -o '"uid":"[^"]*' | cut -d'"' -f4 || echo "")

if [ -z "$FOLDER_UID" ]; then
    echo "Warning: Could not create folder (may already exist)"
    # Try to get existing folder
    FOLDER_UID=$(curl -s -H "Authorization: Bearer $API_KEY" \
        "$GRAFANA_URL/api/folders" | grep -o '"uid":"[^"]*"title":"EJE"' | grep -o '"uid":"[^"]*' | cut -d'"' -f4 || echo "")
fi

echo "Folder UID: $FOLDER_UID"
echo ""

# Import each dashboard
for dashboard_file in "$DASHBOARD_DIR"/*.json; do
    dashboard_name=$(basename "$dashboard_file" .json)
    echo "Importing $dashboard_name..."

    # Read dashboard JSON and wrap it
    dashboard_json=$(cat "$dashboard_file")

    # Create import payload
    import_json=$(jq -n \
        --arg folderUid "$FOLDER_UID" \
        --argjson dashboard "$dashboard_json" \
        '{
            dashboard: $dashboard,
            folderUid: $folderUid,
            overwrite: true
        }')

    # Import dashboard
    response=$(curl -s -X POST \
        -H "Authorization: Bearer $API_KEY" \
        -H "Content-Type: application/json" \
        -d "$import_json" \
        "$GRAFANA_URL/api/dashboards/db")

    if echo "$response" | grep -q '"status":"success"'; then
        echo "✓ $dashboard_name imported successfully"
    else
        echo "✗ Failed to import $dashboard_name"
        echo "Response: $response"
    fi
    echo ""
done

echo "Dashboard import complete!"
echo "View dashboards at: $GRAFANA_URL/dashboards"
