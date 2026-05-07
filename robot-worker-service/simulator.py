# multi robot worker simulator
import json
import os
import time
import random

from robot_core import Robot
from pubsub_client import PubSubClient
from firestore_client import FirestoreClient
from job_system import assign_field_scan
from config import GRID_MAX
from job_system import assign_field_scan, assign_crop_scan


class RobotWorker:
    def __init__(self, robot_id, pubsub, firestore):
        self.robot = Robot(robot_id, firestore_client=firestore)
        self.pubsub = pubsub
        self.firestore = firestore

    def run_step(self):
        self.robot.run_step()

        telemetry = {
            "robot_id": self.robot.robot_id,
            "position": self.robot.position,
            "status": self.robot.status,
            "job": self.robot.current_job,
            "field_location": self.robot.field_location,
            "crop_type": self.robot.crop_type,
            "job_index": self.robot.current_job_index,
            "job_progress": self.robot.job_progress,
            "scanning": self.robot.scanning,
            "scan_position": self.robot.scan_position,
        }

        self.pubsub.publish_telemetry(telemetry)
        print(f"[{self.robot.robot_id}] TELEMETRY → {telemetry}")

    def handle_command(self, cmd):
        print("RAW CMD RECEIVED:", cmd)

        if cmd["robot_id"] != self.robot.robot_id and cmd["robot_id"] != "all":
            return

        print(f"[{self.robot.robot_id}] COMMAND → {cmd}")

        if cmd["type"] == "assign_greenhouse_task":
            self.robot.set_task(
                job_type="greenhouse_task",
                field_location=cmd["field_location"]
            )
        elif cmd["type"] == "start_field_scan":
            start_x = cmd.get("start_x", 0)
            max_x = cmd.get("max_x", GRID_MAX)
            self.robot.scan_max_x = max_x
            assign_field_scan(self.robot, start_x=start_x)
        elif cmd["type"] == "deploy_to_crop":
            crop_type = cmd.get("crop_type")
            if not crop_type:
                print(f"[{self.robot.robot_id}] ❌ deploy_to_crop missing crop_type")
            else:
                assign_crop_scan(self.robot, crop_type)
        elif cmd["type"] == "stop":
            self.robot.clear_task()
        else:
            print(f"[{self.robot.robot_id}] Unknown command type: {cmd['type']}")


def start_worker(robot_id=None):
    robot_id = robot_id or os.environ.get("ROBOT_ID") or f"robot-{random.randint(1000,9999)}"

    pubsub = PubSubClient(robot_id=robot_id)
    firestore = FirestoreClient()

    worker = RobotWorker(robot_id, pubsub, firestore)

    print(f"🤖 Worker started for {robot_id}")
    print("📡 Listening for commands...")

    def callback(message):
        try:
            cmd = json.loads(message.data.decode("utf-8"))
            worker.handle_command(cmd)
        except Exception as e:
            print(f"[{robot_id}] Bad message, skipping: {e}")
        finally:
            message.ack()

    future = pubsub.subscribe_to_commands(callback)
    print("📡 Subscription future active:", future)

    try:
        while True:
            if future.done():
                print(f"[{robot_id}] ⚠️ Subscription died: {future.exception()}")
                break
            worker.run_step()
            time.sleep(0.5)
    finally:
        firestore.remove_robot(robot_id)
        pubsub.delete_subscription()
        pubsub.close()
        print(f"[{robot_id}] 🧹 Cleaned up Firestore and Pub/Sub subscription.")


if __name__ == "__main__":
    start_worker()