# Cloud-Based Robot Management System

## 📌 Project Overview

A cloud-native multi-robot agricultural simulation system built on Google Kubernetes Engine. Multiple autonomous robot agents navigate a 100×100 grid, perform sequential farming job cycles at each cell, coordinate in real time to avoid occupying the same position, and report completion data to BigQuery for analytics.

The system is fully event-driven — robots never poll for work, they react to Pub/Sub messages. All inter-service communication happens through GCP managed services, never directly between pods.


---

##  Google Cloud Services

| Service | Purpose |
|---|---|
| Google Kubernetes Engine (GKE) | Runs all containerized services in `robot-cluster` (`us-west1-a`) |
| Cloud Pub/Sub | Event-driven messaging — `robot-commands` and `robot-telemetry` topics |
| Cloud Firestore | Real-time shared position registry for collision avoidance |
| BigQuery | Analytics — stores completed cell records in `robot_data.grid_completions` |
| Artifact Registry | Stores Docker images in `us-west1` |
| Cloud Build | Builds container images from source on each deploy |
| Cloud Load Balancer | Exposes `robot-api-service` at a public external IP |

---

##  Robot Behavior

Each robot pod is an autonomous agent that runs a strict state machine:

```
idle → assigned → moving_to_field → waiting (if cell occupied)
     → till_soil_in_progress (3 steps)
     → plant_seeds_in_progress (3 steps)
     → water_crop_in_progress (3 steps)
     → harvest_crop_in_progress (3 steps)
     → completed_cycle → next cell
```

### Grid Layout

```
x: 0──────────33 | 34──────────66 | 67──────────100
      TOMATOES   |    CABBAGES    |    CARROTS
```

### Snake Scan Pattern

Robots sweep the grid in a boustrophedon (lawnmower) pattern:

```
x=0 → y: 0, 1, 2 ... 100   (forward)
x=1 → y: 100, 99 ... 0     (backward)
x=2 → y: 0, 1, 2 ... 100   (forward)
```

---

##  Microservices

### `robot-worker-service`
Core simulation engine. Each pod represents one robot instance.

Key files:
- `simulator.py` — main runtime loop, command handler, graceful shutdown
- `robot_core.py` — state machine, movement logic, Firestore injection
- `job_system.py` — task assignment, job progression, snake scan, crop zone scan
- `pubsub_client.py` — per-pod subscription management, telemetry publisher
- `firestore_client.py` — position registry, collision detection
- `config.py` — grid dimensions, job list, crop zone boundaries

### `robot-api-service`
REST API exposing HTTP endpoints to control robots externally.

| Endpoint | Method | Description |
|---|---|---|
| `/` | GET | List all endpoints |
| `/health` | GET | Health check |
| `/command/<robot_id>/scan` | POST | Start full grid scan |
| `/command/<robot_id>/scan_crop` | POST | Deploy robot to crop zone |
| `/command/<robot_id>/goto` | POST | Send robot to specific coordinate |
| `/command/<robot_id>/stop` | POST | Stop robot |
| `/command/all/scan` | POST | Broadcast scan to all robots |

### `telemetry-ingest-service`
Listens to `robot-telemetry` topic, filters for `completed_cycle` events, and writes one row per completed cell to BigQuery.

---

##  Pub/Sub Topics

| Topic | Publisher | Subscriber | Purpose |
|---|---|---|---|
| `robot-commands` | `robot-api-service` | Each robot pod (own subscription) | Send commands to robots |
| `robot-telemetry` | `robot-worker` pods | `telemetry-ingest-service` | Stream robot state |

Each robot pod creates its own unique subscription (`robot-commands-{pod-name}`) on startup and deletes it on graceful shutdown.

---

##  Command Reference

### Send via HTTP (external IP)

```bash
# Deploy robot to crop zone
curl -X POST http://<EXTERNAL_IP>/command/<robot_id>/scan_crop \
  -H "Content-Type: application/json" \
  -d '{"crop_type": "cabbages"}'

# Start full grid scan
curl -X POST http://<EXTERNAL_IP>/command/<robot_id>/scan \
  -H "Content-Type: application/json" \
  -d '{"start_x": 0, "max_x": 100}'

# Send robot to coordinate
curl -X POST http://<EXTERNAL_IP>/command/<robot_id>/goto \
  -H "Content-Type: application/json" \
  -d '{"field_location": [50, 50]}'

# Stop robot
curl -X POST http://<EXTERNAL_IP>/command/<robot_id>/stop

# Broadcast scan to all robots
curl -X POST http://<EXTERNAL_IP>/command/all/scan
```

### Send via Pub/Sub directly

```bash
gcloud pubsub topics publish robot-commands \
  --message='{"robot_id": "<pod_name>", "type": "start_field_scan"}'

gcloud pubsub topics publish robot-commands \
  --message='{"robot_id": "<pod_name>", "type": "deploy_to_crop", "crop_type": "tomatoes"}'
```

---

##  Example Telemetry Payload

```json
{
  "robot_id": "robot-worker-abc123",
  "position": [34, 12],
  "status": "water_crop_in_progress",
  "job": "crop_scan_cabbages",
  "field_location": [34, 12],
  "crop_type": "cabbages",
  "job_index": 2,
  "job_progress": 2,
  "scanning": true,
  "scan_position": [34, 12]
}
```

---

## 📈 Analytics

Query grid completion progress in BigQuery:

```bash
# Overall completion
bq query --use_legacy_sql=false \
  'SELECT COUNT(*) as completed_cells,
   ROUND(COUNT(*)/10000*100, 2) as pct_complete
   FROM robot_data.grid_completions'

# Breakdown by crop zone
bq query --use_legacy_sql=false \
  'SELECT crop_type, COUNT(*) as completed_cells
   FROM robot_data.grid_completions
   GROUP BY crop_type ORDER BY crop_type'

# Recent completions
bq query --use_legacy_sql=false \
  'SELECT robot_id, x, y, crop_type, timestamp
   FROM robot_data.grid_completions
   ORDER BY timestamp DESC LIMIT 10'
```

---

##  Deployment

### Build and deploy a service

```bash
cd ~/robot-worker-service
gcloud builds submit --tag us-west1-docker.pkg.dev/cloud-based-robot-management/robot-repo/robot-worker:latest
kubectl rollout restart deployment robot-worker
kubectl rollout status deployment robot-worker
kubectl logs -f deployment/robot-worker
```

### Scale robots

```bash
kubectl scale deployment robot-worker --replicas=2
```

### Scale down and clear Firestore

```bash
~/scale-down.sh
```

---

##  Load Testing

```bash
~/load-test.sh
```

Spins up 5 robot pods, sends commands simultaneously, measures HTTP latency per pod, captures resource utilization, and queries BigQuery completion count. Results saved to `load_test_results.txt`.

---

##  Telemetry Demo

```bash
~/demo-telemetry.sh
```

Passive observer that walks through all communication layers — HTTP → Pub/Sub → robot pod → Firestore → telemetry topic → BigQuery — and prints what it sees at each hop. Results saved to `telemetry_demo.txt`.

---

##  Performance Metrics

- **Command latency** — time from HTTP request to robot receipt, logged per command as `⏱️ Command latency: Xms`
- **Throughput** — telemetry messages per second, logged every 20 messages as `📊 Throughput: X telemetry/sec`
- **Resource utilization** — CPU and memory per pod via `kubectl top pods`

---

## Project Structure

```
~/
├── load-test.sh                     # load testing script
├── demo-telemetry.sh                # telemetry communication demo
├── robot-worker-service/
│   ├── simulator.py                 # main worker runtime
│   ├── robot_core.py                # robot state machine
│   ├── job_system.py                # job logic and scan patterns
│   ├── pubsub_client.py             # Pub/Sub wrapper
│   ├── firestore_client.py          # Firestore position registry
│   ├── config.py                    # grid and crop zone config
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── deployment.yaml
│   └── scale-down.sh
├── robot-api-service/
│   ├── app.py                       # Flask REST API
│   ├── pubsub_client.py             # command publisher
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── api-deployment.yaml
│   └── service.yaml
└── telemetry-ingest-service/
    ├── app.py                       # entrypoint
    ├── subscriber.py                # BigQuery writer
    ├── Dockerfile
    ├── requirements.txt
    └── deployment.yaml
```

---

##  IAM Service Account

Service account `serviceaccpubsub` is bound to Kubernetes service account `robot-worker-sa` via Workload Identity with the following roles:

- `roles/pubsub.editor` — create, delete, publish, subscribe
- `roles/datastore.user` — Firestore read/write
- `roles/bigquery.dataEditor` — BigQuery insert