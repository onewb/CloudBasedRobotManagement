from flask import Flask, jsonify
import socket
from pubsub_client import PubSubClient

app = Flask(__name__)
pubsub = PubSubClient()

@app.route("/")
def home():
    return "Robot API Service Running"

@app.route("/health")
def health():
    return jsonify(status="healthy", service="robot-api")

@app.route("/info")
def info():
    return jsonify(hostname=socket.gethostname())

#  command endpoint
@app.route("/command/<robot_id>")
def send_command(robot_id):
    pubsub.publish_command({
        "robot_id": robot_id,
        "type": "assign_greenhouse_task",
        "field_location": [50, 50]   
    })
    return jsonify(status="sent")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=False) 