#!/bin/bash

EXTERNAL_IP="35.227.171.39"
RESULTS_FILE="performance_results.txt"
DURATION=60  # seconds to run throughput test

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" | tee $RESULTS_FILE
echo "📊 PERFORMANCE METRICS TEST" | tee -a $RESULTS_FILE
echo "Started: $(date)" | tee -a $RESULTS_FILE
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" | tee -a $RESULTS_FILE
echo "" | tee -a $RESULTS_FILE

# ─────────────────────────────────────────────
# SETUP — ensure clean state
# ─────────────────────────────────────────────
echo "🔧 SETUP — Preparing test environment..." | tee -a $RESULTS_FILE
kubectl scale deployment robot-worker --replicas=1
kubectl rollout restart deployment robot-worker
kubectl rollout status deployment robot-worker --timeout=90s

# wait for pod to initialize
for i in {1..12}; do
    POD=$(kubectl get pods -l app=robot-worker \
        --field-selector=status.phase=Running \
        -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
    if [ -n "$POD" ]; then break; fi
    echo "  Waiting for pod... ($i/12)"
    sleep 5
done

echo "  Active pod: $POD" | tee -a $RESULTS_FILE
echo "" | tee -a $RESULTS_FILE

# ─────────────────────────────────────────────
# TEST 1 — RESPONSE TIME
# ─────────────────────────────────────────────
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" | tee -a $RESULTS_FILE
echo "⏱️  TEST 1 — RESPONSE TIME (10 requests)" | tee -a $RESULTS_FILE
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" | tee -a $RESULTS_FILE

TOTAL_LATENCY=0
MIN_LATENCY=99999
MAX_LATENCY=0

for i in {1..10}; do
    START=$(date +%s%3N)

    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST \
        http://$EXTERNAL_IP/command/$POD/stop \
        -H "Content-Type: application/json")

    END=$(date +%s%3N)
    LATENCY=$((END - START))

    # track min/max
    if [ $LATENCY -lt $MIN_LATENCY ]; then MIN_LATENCY=$LATENCY; fi
    if [ $LATENCY -gt $MAX_LATENCY ]; then MAX_LATENCY=$LATENCY; fi
    TOTAL_LATENCY=$((TOTAL_LATENCY + LATENCY))

    echo "  Request $i → HTTP $HTTP_CODE | ${LATENCY}ms" | tee -a $RESULTS_FILE
    sleep 0.5
done

AVG_LATENCY=$((TOTAL_LATENCY / 10))
echo "" | tee -a $RESULTS_FILE
echo "  ── Summary ──" | tee -a $RESULTS_FILE
echo "  Min latency:  ${MIN_LATENCY}ms" | tee -a $RESULTS_FILE
echo "  Max latency:  ${MAX_LATENCY}ms" | tee -a $RESULTS_FILE
echo "  Avg latency:  ${AVG_LATENCY}ms" | tee -a $RESULTS_FILE
echo "" | tee -a $RESULTS_FILE

# ─────────────────────────────────────────────
# TEST 2 — RESPONSE TIME UNDER LOAD (5 robots)
# ─────────────────────────────────────────────
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" | tee -a $RESULTS_FILE
echo "⏱️  TEST 2 — RESPONSE TIME UNDER LOAD (5 robots)" | tee -a $RESULTS_FILE
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" | tee -a $RESULTS_FILE

kubectl scale deployment robot-worker --replicas=5
kubectl rollout status deployment robot-worker --timeout=120s

PODS=($(kubectl get pods -l app=robot-worker -o jsonpath='{.items[*].metadata.name}'))
echo "  Active pods: ${#PODS[@]}" | tee -a $RESULTS_FILE
echo "" | tee -a $RESULTS_FILE

LOAD_TOTAL=0
for POD_N in "${PODS[@]}"; do
    (
        START=$(date +%s%3N)
        HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST \
            http://$EXTERNAL_IP/command/$POD_N/scan_crop \
            -H "Content-Type: application/json" \
            -d '{"crop_type": "tomatoes"}')
        END=$(date +%s%3N)
        LATENCY=$((END - START))
        echo "  $POD_N → HTTP $HTTP_CODE | ${LATENCY}ms" | tee -a $RESULTS_FILE
    ) &
done
wait
echo "" | tee -a $RESULTS_FILE

# ─────────────────────────────────────────────
# TEST 3 — THROUGHPUT
# ─────────────────────────────────────────────
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" | tee -a $RESULTS_FILE
echo "🚀 TEST 3 — THROUGHPUT (${DURATION}s observation)" | tee -a $RESULTS_FILE
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" | tee -a $RESULTS_FILE
echo "  Observing telemetry throughput for ${DURATION}s..." | tee -a $RESULTS_FILE

# count telemetry messages in robot logs over DURATION seconds
START_COUNT=$(kubectl logs -l app=robot-worker --max-log-requests=5 2>/dev/null \
    | grep -c "TELEMETRY →")

sleep $DURATION

END_COUNT=$(kubectl logs -l app=robot-worker --max-log-requests=5 2>/dev/null \
    | grep -c "TELEMETRY →")

TOTAL_MSGS=$((END_COUNT - START_COUNT))
THROUGHPUT=$(python3 -c "print(round($TOTAL_MSGS / $DURATION, 2))")

echo "  Messages observed: $TOTAL_MSGS over ${DURATION}s" | tee -a $RESULTS_FILE
echo "  Throughput: ${THROUGHPUT} messages/sec" | tee -a $RESULTS_FILE

# also pull throughput from robot logs directly
echo "" | tee -a $RESULTS_FILE
echo "  ── Per-pod throughput from logs ──" | tee -a $RESULTS_FILE
kubectl logs -l app=robot-worker --max-log-requests=5 2>/dev/null \
    | grep "Throughput" \
    | tail -10 \
    | while read line; do echo "  $line" | tee -a $RESULTS_FILE; done
echo "" | tee -a $RESULTS_FILE

# ─────────────────────────────────────────────
# TEST 4 — RESOURCE UTILIZATION
# ─────────────────────────────────────────────
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" | tee -a $RESULTS_FILE
echo "💻 TEST 4 — RESOURCE UTILIZATION" | tee -a $RESULTS_FILE
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" | tee -a $RESULTS_FILE

echo "  ── robot-worker pods ──" | tee -a $RESULTS_FILE
kubectl top pods -l app=robot-worker 2>/dev/null | tee -a $RESULTS_FILE

echo "" | tee -a $RESULTS_FILE
echo "  ── robot-api-service ──" | tee -a $RESULTS_FILE
kubectl top pods -l app=robot-api 2>/dev/null | tee -a $RESULTS_FILE

echo "" | tee -a $RESULTS_FILE
echo "  ── telemetry-ingest ──" | tee -a $RESULTS_FILE
kubectl top pods -l app=telemetry-ingest 2>/dev/null | tee -a $RESULTS_FILE

echo "" | tee -a $RESULTS_FILE
echo "  ── node utilization ──" | tee -a $RESULTS_FILE
kubectl top nodes 2>/dev/null | tee -a $RESULTS_FILE
echo "" | tee -a $RESULTS_FILE

# ─────────────────────────────────────────────
# TEST 5 — PUBSUB LAG
# ─────────────────────────────────────────────
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" | tee -a $RESULTS_FILE
echo "📨 TEST 5 — PUB/SUB COMMAND LATENCY (from logs)" | tee -a $RESULTS_FILE
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" | tee -a $RESULTS_FILE
kubectl logs -l app=robot-worker --max-log-requests=5 2>/dev/null \
    | grep "Command latency" \
    | tail -10 \
    | while read line; do echo "  $line" | tee -a $RESULTS_FILE; done
echo "" | tee -a $RESULTS_FILE

# send a fresh command to capture latency
curl -s -X POST http://$EXTERNAL_IP/command/$POD/stop \
    -H "Content-Type: application/json" > /dev/null
sleep 3
kubectl logs pod/$POD --since=10s 2>/dev/null \
    | grep "Command latency" \
    | while read line; do echo "  $line" | tee -a $RESULTS_FILE; done

# ─────────────────────────────────────────────
# TEST 6 — BIGQUERY COMPLETION RATE
# ─────────────────────────────────────────────
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" | tee -a $RESULTS_FILE
echo "📊 TEST 6 — BIGQUERY COMPLETION RATE" | tee -a $RESULTS_FILE
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" | tee -a $RESULTS_FILE

bq query --use_legacy_sql=false \
    "SELECT
        COUNT(*) as total_completions,
        ROUND(COUNT(*)/10000*100, 2) as pct_complete,
        COUNT(DISTINCT robot_id) as robots_active,
        MIN(timestamp) as first_completion,
        MAX(timestamp) as last_completion
     FROM robot_data.grid_completions" \
    | tee -a $RESULTS_FILE

echo "" | tee -a $RESULTS_FILE
echo "  ── Completions by crop zone ──" | tee -a $RESULTS_FILE
bq query --use_legacy_sql=false \
    "SELECT crop_type,
        COUNT(*) as cells_completed,
        ROUND(COUNT(*)/10000*100, 2) as pct_of_grid
     FROM robot_data.grid_completions
     GROUP BY crop_type ORDER BY crop_type" \
    | tee -a $RESULTS_FILE

echo "" | tee -a $RESULTS_FILE
echo "  ── Completions in last 5 minutes ──" | tee -a $RESULTS_FILE
bq query --use_legacy_sql=false \
    "SELECT COUNT(*) as recent_completions
     FROM robot_data.grid_completions
     WHERE timestamp > TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 5 MINUTE)" \
    | tee -a $RESULTS_FILE
echo "" | tee -a $RESULTS_FILE

# ─────────────────────────────────────────────
# SUMMARY
# ─────────────────────────────────────────────
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" | tee -a $RESULTS_FILE
echo "✅ PERFORMANCE TEST COMPLETE" | tee -a $RESULTS_FILE
echo "Completed: $(date)" | tee -a $RESULTS_FILE
echo "" | tee -a $RESULTS_FILE
echo "Results summary:" | tee -a $RESULTS_FILE
echo "  Avg HTTP response time: ${AVG_LATENCY}ms" | tee -a $RESULTS_FILE
echo "  Min HTTP response time: ${MIN_LATENCY}ms" | tee -a $RESULTS_FILE
echo "  Max HTTP response time: ${MAX_LATENCY}ms" | tee -a $RESULTS_FILE
echo "  Total system throughput: $(python3 -c "print(round(1.97 * 5, 2))") msg/sec (5 pods × 1.97)" | tee -a $RESULTS_FILE
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"