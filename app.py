from flask import Flask, jsonify
import os
import socket

app = Flask(__name__)

# =========================
# CONFIG
# =========================
NUM_ROBOTS = int(os.getenv("NUM_ROBOTS", 3))

# =========================
# ROUTES
# =========================
@app.route("/")
def home():
    return "Robot Fleet Manager API is running!"

@app.route("/health")
def health():
    return jsonify(
        status="healthy",
        service="robot-fleet-api"
    )

@app.route("/info")
def info():
    return jsonify(
        hostname=socket.gethostname(),
        service="robot-fleet-api",
        num_robots_configured=NUM_ROBOTS
    )

# Optional: readiness probe (useful for Kubernetes)
@app.route("/ready")
def ready():
    return jsonify(status="ready")


# =========================
# MAIN ENTRYPOINT
# =========================
if __name__ == "__main__":
    print("🚀 Starting Robot Fleet Manager API Service")


    app.run(
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8080)),
        debug=False
    )


