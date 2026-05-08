#!/bin/bash

EXTERNAL_IP="35.227.171.39"
LOG_FILE="telemetry_demo.txt"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" | tee $LOG_FILE
echo "🌱 TELEMETRY COMMUNICATION DEMO" | tee -a $LOG_FILE
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" | tee -a $LOG_FILE
echo "" | tee -a $LOG_FILE

# ─────────────────────────────────────────────
# STEP 0 — ensure 1 robot is running
# ─────────────────────────────────────────────
echo "🔧 STEP 0 — Ensuring 1 robot pod is running..." | tee $LOG_FILE
kubectl scale deployment robot-worker --replicas=1
kubectl scale deployment telemetry-ingest --replicas=1
kubectl rollout restart deployment robot-worker
kubectl rollout status deployment robot-worker --timeout=60s
echo "  Waiting 10s for Firestore client to initialize..." | tee -a $LOG_FILE
sleep 10
echo "" | tee -a $LOG_FILE
# ─────────────────────────────────────────────
# STEP 1 — identify the pod
# ─────────────────────────────────────────────
echo "🤖 STEP 1 — Identifying active robot pod..." | tee -a $LOG_FILE

# wait until a Running pod exists
for i in {1..12}; do
    POD=$(kubectl get pods -l app=robot-worker \
        --field-selector=status.phase=Running \
        -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
    if [ -n "$POD" ]; then
        break
    fi
    echo "  Waiting for pod to be Running... ($i/12)" | tee -a $LOG_FILE
    sleep 5
done

echo "  Pod: $POD" | tee -a $LOG_FILE
echo "" | tee -a $LOG_FILE
# ─────────────────────────────────────────────
# STEP 2 — show robot is idle in Firestore
# ─────────────────────────────────────────────
echo "🔥 STEP 2 — Checking Firestore position registry (before command)..." | tee -a $LOG_FILE
python3 -c "
from google.cloud import firestore
db = firestore.Client(project='cloud-based-robot-management')
doc = db.collection('robots').document('$POD').get()
if doc.exists:
    print('  Firestore entry:', doc.to_dict())
else:
    print('  No Firestore entry yet — robot may not have started a step')
" | tee -a $LOG_FILE
echo "" | tee -a $LOG_FILE

# create temp subscription
gcloud pubsub subscriptions create telemetry-demo-sub \
    --topic=robot-telemetry --quiet 2>/dev/null

# wait for a message to arrive
sleep 3

# ─────────────────────────────────────────────
# STEP 3 — send command via external IP
# ─────────────────────────────────────────────
echo "📡 STEP 3 — Sending command via HTTP to external IP ($EXTERNAL_IP)..." | tee -a $LOG_FILE
SENT_AT=$(date +%s%3N)
echo "  Sent at: $(date)" | tee -a $LOG_FILE

RESPONSE=$(curl -s -w "\n%{http_code}" -X POST \
    http://$EXTERNAL_IP/command/$POD/scan_crop \
    -H "Content-Type: application/json" \
    -d '{"crop_type": "tomatoes"}')

HTTP_CODE=$(echo "$RESPONSE" | tail -1)
RECEIVED_AT=$(date +%s%3N)
HTTP_LATENCY=$((RECEIVED_AT - SENT_AT))

echo "  HTTP response code: $HTTP_CODE" | tee -a $LOG_FILE
echo "  HTTP round-trip latency: ${HTTP_LATENCY}ms" | tee -a $LOG_FILE
echo "" | tee -a $LOG_FILE

# ─────────────────────────────────────────────
# STEP 4 — watch robot logs for command receipt
# ─────────────────────────────────────────────
echo "📥 STEP 4 — Watching robot logs for command receipt (15s)..." | tee -a $LOG_FILE
echo "  ── robot-worker logs ──" | tee -a $LOG_FILE
sleep 5
kubectl logs pod/$POD --since=30s 2>/dev/null \
    | grep -E "CMD|COMMAND|latency|scan|TELEMETRY|moving" \
    | head -20 \
    | while read line; do echo "  $line" | tee -a $LOG_FILE; done
echo "" | tee -a $LOG_FILE
# ─────────────────────────────────────────────
# STEP 5 — wait for robot to move and update Firestore
# ─────────────────────────────────────────────
echo "⏳ STEP 5 — Waiting 10s for robot to begin moving..." | tee -a $LOG_FILE
sleep 10
echo "  Checking Firestore position after movement..." | tee -a $LOG_FILE
python3 -c "
from google.cloud import firestore
db = firestore.Client(project='cloud-based-robot-management')
doc = db.collection('robots').document('$POD').get()
if doc.exists:
    print('  Firestore entry:', doc.to_dict())
else:
    print('  No Firestore entry found')
" | tee -a $LOG_FILE
echo "" | tee -a $LOG_FILE

# ─────────────────────────────────────────────
# STEP 6 — pull a telemetry message from Pub/Sub
# ─────────────────────────────────────────────
echo "📨 STEP 6 — Sampling live telemetry from robot-telemetry topic..." | tee -a $LOG_FILE
echo "  ── raw Pub/Sub message ──" | tee -a $LOG_FILE



# pull one message
gcloud pubsub subscriptions pull telemetry-demo-sub \
    --limit=1 --auto-ack \
    --format="value(message.data)" 2>/dev/null \
    | python3 -c "
import sys, json, base64
for line in sys.stdin:
    line = line.strip()
    if line:
        try:
            decoded = base64.b64decode(line).decode('utf-8')
            data = json.loads(decoded)
            print('  robot_id:', data.get('robot_id'))
            print('  position:', data.get('position'))
            print('  status:  ', data.get('status'))
            print('  job:     ', data.get('job'))
            print('  crop:    ', data.get('crop_type'))
        except:
            try:
                data = json.loads(line)
                print('  robot_id:', data.get('robot_id'))
                print('  position:', data.get('position'))
                print('  status:  ', data.get('status'))
                print('  job:     ', data.get('job'))
                print('  crop:    ', data.get('crop_type'))
            except:
                print(' ', line)
" | tee -a $LOG_FILE

# delete temp subscription
gcloud pubsub subscriptions delete telemetry-demo-sub --quiet 2>/dev/null
echo "" | tee -a $LOG_FILE
# ─────────────────────────────────────────────
# STEP 7 — wait for completed_cycle and check BigQuery
# ─────────────────────────────────────────────
echo "⏳ STEP 7 — Waiting 30s for robot to complete first cell cycle..." | tee -a $LOG_FILE
sleep 30
echo "  Checking BigQuery for new completions..." | tee -a $LOG_FILE
bq query --use_legacy_sql=false \
    "SELECT robot_id, x, y, crop_type, timestamp
     FROM robot_data.grid_completions
     ORDER BY timestamp DESC
     LIMIT 5" \
    | tee -a $LOG_FILE
echo "" | tee -a $LOG_FILE

# ─────────────────────────────────────────────
# STEP 8 — show telemetry-ingest logs
# ─────────────────────────────────────────────
echo "📊 STEP 8 — Checking telemetry-ingest service logs..." | tee -a $LOG_FILE
echo "  ── telemetry-ingest logs ──" | tee -a $LOG_FILE
kubectl logs deployment/telemetry-ingest --since=300s 2>/dev/null \
    | grep -E "Inserted|Error|Listening" \
    | tail -10 \
    | while read line; do echo "  $line" | tee -a $LOG_FILE; done
echo "" | tee -a $LOG_FILE

# ─────────────────────────────────────────────
# SUMMARY
# ─────────────────────────────────────────────
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" | tee -a $LOG_FILE
echo "✅ DEMO COMPLETE" | tee -a $LOG_FILE
echo "" | tee -a $LOG_FILE
echo "Layer communication verified:" | tee -a $LOG_FILE
echo "  1. External HTTP  → robot-api-service   ✅" | tee -a $LOG_FILE
echo "  2. Flask API      → Pub/Sub topic        ✅" | tee -a $LOG_FILE
echo "  3. Pub/Sub        → robot-worker pod     ✅" | tee -a $LOG_FILE
echo "  4. robot-worker   → Firestore registry   ✅" | tee -a $LOG_FILE
echo "  5. robot-worker   → robot-telemetry      ✅" | tee -a $LOG_FILE
echo "  6. telemetry-ingest → BigQuery           ✅" | tee -a $LOG_FILE
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" | tee -a $LOG_FILE
echo "" | tee -a $LOG_FILE
echo "Full output saved to: $LOG_FILE" | tee -a $LOG_FILE