import json
import os
from datetime import datetime, timezone
from google.cloud import pubsub_v1, bigquery
# This subscriber listens to telemetry messages from the robot workers, processes them, and inserts relevant data into BigQuery for analysis.

PROJECT_ID = os.getenv("GCP_PROJECT_ID", "cloud-based-robot-management")
SUBSCRIPTION_ID = "telemetry-ingest-sub"
DATASET_ID = "robot_data"
TABLE_ID = "grid_completions"

subscriber = pubsub_v1.SubscriberClient()
bq_client = bigquery.Client(project=PROJECT_ID)

subscription_path = subscriber.subscription_path(PROJECT_ID, SUBSCRIPTION_ID)
table_ref = f"{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}"


def insert_completion(data: dict):      # Insert a completed cycle into BigQuery with the robot's position, crop type, and timestamp.
    row = {
        "robot_id": data.get("robot_id"),
        "x": data["position"][0],
        "y": data["position"][1],
        "crop_type": data.get("crop_type"),
        "job": data.get("job"),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    errors = bq_client.insert_rows_json(table_ref, [row])
    if errors:
        print(f"[BigQuery] ❌ Insert error: {errors}")
    else:
        print(f"[BigQuery] ✅ Inserted completion at {row['x']},{row['y']} crop={row['crop_type']}")


def callback(message):                  # Callback function to process incoming telemetry messages, extract relevant data, and insert completed cycles into BigQuery.
    try:
        data = json.loads(message.data.decode("utf-8"))

        if data.get("status") == "completed_cycle":
            insert_completion(data)

    except Exception as e:
        print(f"[subscriber] Error: {e}")
    finally:
        message.ack()


def listen():                           # Start listening to the Pub/Sub subscription for telemetry messages and process them using the callback function.
    print(f"[telemetry-ingest] Listening on {subscription_path}...")
    future = subscriber.subscribe(subscription_path, callback=callback)
    try:
        future.result()
    except KeyboardInterrupt:
        future.cancel()
        print("[telemetry-ingest] Stopped.")