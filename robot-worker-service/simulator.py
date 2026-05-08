# multi robot worker simulator
# This simulator runs multiple robot workers in parallel threads, allowing you to test the behavior of multiple robots interacting with each other and the system. 
# Each worker simulates a robot that listens for commands, updates its position and status in Firestore, and publishes telemetry data to Pub/Sub. 
# The simulator can be used to validate the overall system behavior, including command handling, job execution, collision avoidance, and state management across multiple robots.
import json
import os
import time
import random

from robot_core import Robot
from pubsub_client import PubSubClient
from firestore_client import FirestoreClient
from config import GRID_MAX
from job_system import assign_field_scan, assign_crop_scan


class RobotWorker:
    def __init__(self, robot_id, pubsub, firestore):
        self.robot = Robot(robot_id, firestore_client=firestore)
        self.pubsub = pubsub
        self.firestore = firestore
        self.telemetry_count = 0
        self.command_count = 0
        self.throughput_start = time.time()

    def run_step(self):
        self.robot.run_step()
        self.telemetry_count += 1

        # print throughput every 20 messages
        elapsed = time.time() - self.throughput_start
        if self.telemetry_count % 20 == 0:
            throughput = round(self.telemetry_count / elapsed, 2)
            print(f"[{self.robot.robot_id}] 📊 Throughput: {throughput} telemetry/sec | total: {self.telemetry_count}")

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
        received_at = time.time()
        print("RAW CMD RECEIVED:", cmd)

        if cmd["robot_id"] != self.robot.robot_id and cmd["robot_id"] != "all":
            return

        # calculate response time if sent_at present
        sent_at = cmd.get("sent_at")
        if sent_at:
            latency_ms = round((received_at - sent_at) * 1000, 2)
            print(f"[{self.robot.robot_id}] ⏱️ Command latency: {latency_ms}ms")

        print(f"[{self.robot.robot_id}] COMMAND → {cmd}")
        self.command_count += 1
        print(f"[{self.robot.robot_id}] 📨 Commands received so far: {self.command_count}")

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