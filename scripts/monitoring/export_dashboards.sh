#!/bin/bash
# Export EJE Grafana dashboards
#
# Usage: ./export_dashboards.sh [GRAFANA_URL] [API_KEY]
# Example: ./export_dashboards.sh http://localhost:3000 eyJrIjoiYWJjMTIz...

set -e

GRAFANA_URL="${1:-http://localhost:3000}"
API_KEY="${2}"
OUTPUT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../monitoring/grafana/dashboards" && pwd)"

if [ -z "$API_KEY" ]; then
    echo "Error: Grafana API key required"
    echo "Usage: $0 [GRAFANA_URL] [API_KEY]"
    exit 1
fi

echo "Exporting EJE dashboards from $GRAFANA_URL..."
echo "Output directory: $OUTPUT_DIR"
echo ""

# Create output directory if it doesn't exist
mkdir -p "$OUTPUT_DIR"

# Get all dashboards in EJE folder
DASHBOARDS=$(curl -s -H "Authorization: Bearer $API_KEY" \
    "$GRAFANA_URL/api/search?type=dash-db&folderIds=0" | \
    jq -r '.[] | select(.folderTitle == "EJE") | .uid')

if [ -z "$DASHBOARDS" ]; then
    echo "No dashboards found in EJE folder"
    exit 0
fi

# Export each dashboard
for uid in $DASHBOARDS; do
    echo "Exporting dashboard: $uid"

    # Get dashboard JSON
    dashboard_json=$(curl -s -H "Authorization: Bearer $API_KEY" \
        "$GRAFANA_URL/api/dashboards/uid/$uid")

    # Extract dashboard title and create filename
    title=$(echo "$dashboard_json" | jq -r '.dashboard.title' | \
        tr '[:upper:]' '[:lower:]' | tr ' ' '_')

    # Remove metadata and save clean dashboard
    echo "$dashboard_json" | jq '.dashboard |
        del(.id) |
        .id = null |
        del(.uid) |
        del(.version)' > "$OUTPUT_DIR/${title}.json"

    echo "✓ Exported to ${title}.json"
done

echo ""
echo "Export complete! Dashboards saved to: $OUTPUT_DIR"
