from flask import Flask, jsonify, request
import socket
import time
from pubsub_client import PubSubClient

app = Flask(__name__)
pubsub = PubSubClient()


@app.route("/")
def home():
    return jsonify(
        service="Robot Farm API",
        status="running",
        endpoints=[
            "/health",
            "/info",
            "/command/<robot_id>/scan",
            "/command/<robot_id>/scan_crop",
            "/command/<robot_id>/goto",
            "/command/<robot_id>/stop",
            "/command/all/scan",
        ]
    )


@app.route("/health")
def health():
    return jsonify(status="healthy", service="robot-api")


@app.route("/info")
def info():
    return jsonify(hostname=socket.gethostname())


@app.route("/command/<robot_id>/scan", methods=["POST"])
def start_scan(robot_id):
    body = request.get_json(silent=True) or {}
    start_x = body.get("start_x", 0)
    max_x = body.get("max_x", 100)
    pubsub.publish_command({
        "robot_id": robot_id,
        "type": "start_field_scan",
        "start_x": start_x,
        "max_x": max_x,
        "sent_at": time.time()
    })
    return jsonify(status="sent", robot_id=robot_id, start_x=start_x, max_x=max_x)


@app.route("/command/<robot_id>/scan_crop", methods=["POST"])
def scan_crop(robot_id):
    body = request.get_json(silent=True) or {}
    crop_type = body.get("crop_type")

    if not crop_type:
        return jsonify(error="crop_type is required"), 400
    if crop_type not in ["tomatoes", "cabbages", "carrots"]:
        return jsonify(error="crop_type must be tomatoes, cabbages, or carrots"), 400

    pubsub.publish_command({
        "robot_id": robot_id,
        "type": "deploy_to_crop",
        "crop_type": crop_type,
        "sent_at": time.time()
    })
    return jsonify(status="sent", robot_id=robot_id, crop_type=crop_type)


@app.route("/command/<robot_id>/goto", methods=["POST"])
def goto(robot_id):
    body = request.get_json(silent=True) or {}
    field_location = body.get("field_location")

    if not field_location or len(field_location) != 2:
        return jsonify(error="field_location [x, y] is required"), 400

    pubsub.publish_command({
        "robot_id": robot_id,
        "type": "assign_greenhouse_task",
        "field_location": field_location,
        "sent_at": time.time()
    })
    return jsonify(status="sent", robot_id=robot_id, field_location=field_location)


@app.route("/command/<robot_id>/stop", methods=["POST"])
def stop(robot_id):
    pubsub.publish_command({
        "robot_id": robot_id,
        "type": "stop",
        "sent_at": time.time()
    })
    return jsonify(status="sent", robot_id=robot_id)


@app.route("/command/all/scan", methods=["POST"])
def scan_all():
    pubsub.publish_command({
        "robot_id": "all",
        "type": "start_field_scan",
        "sent_at": time.time()
    })
    return jsonify(status="sent", target="all")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=False)