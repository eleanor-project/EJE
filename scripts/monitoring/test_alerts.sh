#!/bin/bash
# Test EJE Alert Configuration
#
# Usage: ./test_alerts.sh [ALERTMANAGER_URL] [PROMETHEUS_URL]
# Example: ./test_alerts.sh http://localhost:9093 http://localhost:9090

set -e

ALERTMANAGER_URL="${1:-http://localhost:9093}"
PROMETHEUS_URL="${2:-http://localhost:9090}"

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "Testing EJE Alert Configuration"
echo "AlertManager: $ALERTMANAGER_URL"
echo "Prometheus: $PROMETHEUS_URL"
echo ""

# Function to print status
print_status() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✓${NC} $2"
    else
        echo -e "${RED}✗${NC} $2"
    fi
}

# Function to send test alert
send_test_alert() {
    local severity=$1
    local alertname=$2
    local summary=$3

    curl -s -X POST "${ALERTMANAGER_URL}/api/v1/alerts" \
        -H "Content-Type: application/json" \
        -d "[{
            \"labels\": {
                \"alertname\": \"${alertname}\",
                \"severity\": \"${severity}\",
                \"component\": \"test\",
                \"instance\": \"test-instance\"
            },
            \"annotations\": {
                \"summary\": \"${summary}\",
                \"description\": \"Test alert description\",
                \"impact\": \"No impact - this is a test\",
                \"action\": \"No action needed - this is a test alert\",
                \"runbook\": \"https://docs.eje.example.com/runbooks/test\",
                \"dashboard\": \"http://grafana:3000/d/test\"
            },
            \"startsAt\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",
            \"endsAt\": \"$(date -u -d '+5 minutes' +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -u -v +5M +%Y-%m-%dT%H:%M:%SZ)\"
        }]" > /dev/null 2>&1

    return $?
}

# Test 1: Check AlertManager is running
echo "Test 1: Check AlertManager availability"
if curl -s -f "${ALERTMANAGER_URL}/-/healthy" > /dev/null; then
    print_status 0 "AlertManager is healthy"
else
    print_status 1 "AlertManager is not responding"
    exit 1
fi

# Test 2: Check Prometheus is running
echo "Test 2: Check Prometheus availability"
if curl -s -f "${PROMETHEUS_URL}/-/healthy" > /dev/null; then
    print_status 0 "Prometheus is healthy"
else
    print_status 1 "Prometheus is not responding"
    exit 1
fi

# Test 3: Validate alert rule syntax
echo "Test 3: Validate alert rule syntax"
ALERT_RULES_FILE="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../monitoring/prometheus" && pwd)/alert_rules.yml"
if [ -f "$ALERT_RULES_FILE" ]; then
    if command -v promtool > /dev/null 2>&1; then
        if promtool check rules "$ALERT_RULES_FILE" > /dev/null 2>&1; then
            print_status 0 "Alert rules syntax valid"
        else
            print_status 1 "Alert rules syntax invalid"
            promtool check rules "$ALERT_RULES_FILE"
            exit 1
        fi
    else
        echo -e "${YELLOW}⚠${NC} promtool not found, skipping syntax validation"
    fi
else
    print_status 1 "Alert rules file not found at $ALERT_RULES_FILE"
    exit 1
fi

# Test 4: Check Prometheus has loaded alert rules
echo "Test 4: Check Prometheus alert rules loaded"
RULES_COUNT=$(curl -s "${PROMETHEUS_URL}/api/v1/rules" | grep -o '"type":"alerting"' | wc -l | tr -d ' ')
if [ "$RULES_COUNT" -gt 0 ]; then
    print_status 0 "Prometheus has loaded $RULES_COUNT alert rules"
else
    print_status 1 "No alert rules loaded in Prometheus"
    exit 1
fi

# Test 5: Check Prometheus-AlertManager connection
echo "Test 5: Check Prometheus-AlertManager connection"
AM_STATUS=$(curl -s "${PROMETHEUS_URL}/api/v1/alertmanagers" | grep -o '"health":"up"' | wc -l | tr -d ' ')
if [ "$AM_STATUS" -gt 0 ]; then
    print_status 0 "Prometheus connected to AlertManager"
else
    print_status 1 "Prometheus not connected to AlertManager"
    exit 1
fi

# Test 6: Send test critical alert
echo "Test 6: Send test critical alert"
if send_test_alert "critical" "TestCriticalAlert" "Testing critical alert routing"; then
    sleep 2
    ALERT_COUNT=$(curl -s "${ALERTMANAGER_URL}/api/v2/alerts?filter=alertname=TestCriticalAlert" | grep -o '"alertname"' | wc -l | tr -d ' ')
    if [ "$ALERT_COUNT" -gt 0 ]; then
        print_status 0 "Critical alert received by AlertManager"
    else
        print_status 1 "Critical alert not found in AlertManager"
    fi
else
    print_status 1 "Failed to send critical alert"
fi

# Test 7: Send test warning alert
echo "Test 7: Send test warning alert"
if send_test_alert "warning" "TestWarningAlert" "Testing warning alert routing"; then
    sleep 2
    ALERT_COUNT=$(curl -s "${ALERTMANAGER_URL}/api/v2/alerts?filter=alertname=TestWarningAlert" | grep -o '"alertname"' | wc -l | tr -d ' ')
    if [ "$ALERT_COUNT" -gt 0 ]; then
        print_status 0 "Warning alert received by AlertManager"
    else
        print_status 1 "Warning alert not found in AlertManager"
    fi
else
    print_status 1 "Failed to send warning alert"
fi

# Test 8: Send test info alert
echo "Test 8: Send test info alert"
if send_test_alert "info" "TestInfoAlert" "Testing info alert routing"; then
    sleep 2
    ALERT_COUNT=$(curl -s "${ALERTMANAGER_URL}/api/v2/alerts?filter=alertname=TestInfoAlert" | grep -o '"alertname"' | wc -l | tr -d ' ')
    if [ "$ALERT_COUNT" -gt 0 ]; then
        print_status 0 "Info alert received by AlertManager"
    else
        print_status 1 "Info alert not found in AlertManager"
    fi
else
    print_status 1 "Failed to send info alert"
fi

# Test 9: Test alert deduplication
echo "Test 9: Test alert deduplication"
for i in {1..3}; do
    send_test_alert "warning" "DuplicationTest" "Testing alert deduplication" > /dev/null 2>&1
done
sleep 3
DEDUPE_COUNT=$(curl -s "${ALERTMANAGER_URL}/api/v2/alerts?filter=alertname=DuplicationTest" | grep -o '"alertname"' | wc -l | tr -d ' ')
if [ "$DEDUPE_COUNT" -eq 1 ]; then
    print_status 0 "Alert deduplication working (3 alerts -> 1 group)"
elif [ "$DEDUPE_COUNT" -gt 1 ]; then
    print_status 1 "Alert deduplication not working ($DEDUPE_COUNT groups found)"
else
    print_status 1 "Deduplication test alerts not found"
fi

# Test 10: Test alert resolution
echo "Test 10: Test alert resolution"
# Send resolved alert
curl -s -X POST "${ALERTMANAGER_URL}/api/v1/alerts" \
    -H "Content-Type: application/json" \
    -d "[{
        \"labels\": {
            \"alertname\": \"TestResolvedAlert\",
            \"severity\": \"warning\"
        },
        \"annotations\": {
            \"summary\": \"Testing alert resolution\"
        },
        \"startsAt\": \"$(date -u -d '-10 minutes' +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -u -v -10M +%Y-%m-%dT%H:%M:%SZ)\",
        \"endsAt\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"
    }]" > /dev/null 2>&1

sleep 2
RESOLVED_STATUS=$(curl -s "${ALERTMANAGER_URL}/api/v2/alerts?filter=alertname=TestResolvedAlert" | grep -o '"status":"resolved"' | head -1)
if [ -n "$RESOLVED_STATUS" ]; then
    print_status 0 "Alert resolution working"
else
    print_status 1 "Alert resolution not working or alert not found"
fi

# Test 11: Check AlertManager configuration
echo "Test 11: Validate AlertManager configuration"
AM_CONFIG=$(curl -s "${ALERTMANAGER_URL}/api/v2/status" | grep -o '"configYAML"' | wc -l | tr -d ' ')
if [ "$AM_CONFIG" -gt 0 ]; then
    print_status 0 "AlertManager configuration valid"
else
    print_status 1 "AlertManager configuration invalid or not loaded"
fi

# Test 12: Verify runbook links in alert rules
echo "Test 12: Verify runbook links in alert rules"
RUNBOOK_COUNT=$(grep -c 'runbook:' "$ALERT_RULES_FILE" || true)
if [ "$RUNBOOK_COUNT" -gt 0 ]; then
    print_status 0 "Alert rules contain runbook links ($RUNBOOK_COUNT found)"
else
    print_status 1 "No runbook links found in alert rules"
fi

# Cleanup test alerts
echo ""
echo "Cleaning up test alerts..."
TEST_ALERT_NAMES=("TestCriticalAlert" "TestWarningAlert" "TestInfoAlert" "DuplicationTest" "TestResolvedAlert")

for alert in "${TEST_ALERT_NAMES[@]}"; do
    curl -s -X POST "${ALERTMANAGER_URL}/api/v1/alerts" \
        -H "Content-Type: application/json" \
        -d "[{
            \"labels\": {
                \"alertname\": \"${alert}\"
            },
            \"startsAt\": \"$(date -u -d '-1 hour' +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -u -v -1H +%Y-%m-%dT%H:%M:%SZ)\",
            \"endsAt\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"
        }]" > /dev/null 2>&1
done

echo -e "${GREEN}✓${NC} Test alerts cleaned up"

echo ""
echo "============================================"
echo "Alert Configuration Test Complete"
echo "============================================"
echo ""
echo "Manual verification steps:"
echo "1. Check email inbox for test notifications"
echo "2. Check Slack channels for test alerts"
echo "3. Check PagerDuty for test incidents (if configured)"
echo "4. Verify alert grouping in AlertManager UI: ${ALERTMANAGER_URL}"
echo "5. Review alert rules in Prometheus UI: ${PROMETHEUS_URL}/alerts"
echo ""
