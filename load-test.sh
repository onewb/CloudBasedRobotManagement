#!/bin/bash

EXTERNAL_IP="35.227.171.39"
NUM_ROBOTS=5
RESULTS_FILE="load_test_results.txt"

echo "🚀 Load test started at $(date)" | tee $RESULTS_FILE
echo "Target: $EXTERNAL_IP | Robots: $NUM_ROBOTS" | tee -a $RESULTS_FILE
echo "─────────────────────────────────────" | tee -a $RESULTS_FILE

# scale up to 5 robots
echo "⬆️  Scaling robot-worker to $NUM_ROBOTS replicas..."
kubectl scale deployment robot-worker --replicas=$NUM_ROBOTS
kubectl rollout status deployment robot-worker

# get all pod names
PODS=($(kubectl get pods -l app=robot-worker -o jsonpath='{.items[*].metadata.name}'))
echo "🤖 Active pods: ${PODS[@]}" | tee -a $RESULTS_FILE

# send commands to all pods simultaneously and measure response time
echo "" | tee -a $RESULTS_FILE
echo "📡 Sending commands to all robots simultaneously..." | tee -a $RESULTS_FILE

for POD in "${PODS[@]}"; do
    (
        START=$(date +%s%3N)

        RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" -X POST \
            http://$EXTERNAL_IP/command/$POD/scan_crop \
            -H "Content-Type: application/json" \
            -d '{"crop_type": "tomatoes"}')

        END=$(date +%s%3N)
        LATENCY=$((END - START))

        echo "  $POD → HTTP $RESPONSE | ${LATENCY}ms" | tee -a $RESULTS_FILE
    ) &
done
wait  # wait for all parallel curls to finish

# wait and measure throughput
echo "" | tee -a $RESULTS_FILE
echo "⏳ Waiting 30s to measure throughput..." | tee -a $RESULTS_FILE
sleep 30

# check resource utilization
echo "" | tee -a $RESULTS_FILE
echo "💻 Resource utilization:" | tee -a $RESULTS_FILE
kubectl top pods -l app=robot-worker | tee -a $RESULTS_FILE

# check bigquery completions during test
echo "" | tee -a $RESULTS_FILE
echo "📊 BigQuery completions during test:" | tee -a $RESULTS_FILE
bq query --use_legacy_sql=false \
    'SELECT COUNT(*) as completed_cells, ROUND(COUNT(*)/10000*100,2) as pct_complete FROM robot_data.grid_completions' \
    | tee -a $RESULTS_FILE

echo "" | tee -a $RESULTS_FILE
echo "✅ Load test complete at $(date)" | tee -a $RESULTS_FILE

# scale back down
echo "⬇️  Scaling down..." 
kubectl scale deployment robot-worker --replicas=1