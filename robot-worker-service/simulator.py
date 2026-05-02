# multi robot worker simulator
import json
import os
import time
import random

from robot_core import Robot
from pubsub_client import PubSubClient


class RobotWorker:
    def __init__(self, robot_id, pubsub):
        self.robot = Robot(robot_id)
        self.pubsub = pubsub

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
        }

        self.pubsub.publish_telemetry(telemetry)
        print(f"[{self.robot.robot_id}] TELEMETRY → {telemetry}")

    def handle_command(self, cmd):
        print("RAW CMD RECEIVED:", cmd)

        if cmd["robot_id"] != self.robot.robot_id:
            return

        print(f"[{self.robot.robot_id}] COMMAND → {cmd}")

        if cmd["type"] == "assign_greenhouse_task":
            self.robot.set_task(
                job_type="greenhouse_task",
                field_location=cmd["field_location"]
            )

        elif cmd["type"] == "stop":
            self.robot.clear_task()

        else:
            print(f"[{self.robot.robot_id}] Unknown command type: {cmd['type']}")


def start_worker(robot_id=None):
    pubsub = PubSubClient()

    # Prefer env var for Kubernetes injection, then arg, then random
    robot_id = robot_id or os.environ.get("ROBOT_ID") or f"robot-{random.randint(1000,9999)}"

    worker = RobotWorker(robot_id, pubsub)

    print(f"🤖 Worker started for {robot_id}")
    print("📡 Listening for commands...")

    def callback(message):
        try:
            cmd = json.loads(message.data.decode("utf-8"))
            worker.handle_command(cmd)
        except Exception as e:
            print(f"[{robot_id}] Bad message, skipping: {e}")
        finally:
            message.ack()  # Always ack — don't redeliver malformed messages

    future = pubsub.subscribe_to_commands(callback)
    print("📡 Subscription future active:", future)

    while True:
        # Check subscription is still alive
        if future.done():
            print(f"[{robot_id}] ⚠️ Subscription died: {future.exception()}")
            break

        worker.run_step()
        time.sleep(2)  # 2s loop — matches telemetry cadence, won't flood Pub/Sub


if __name__ == "__main__":
    start_worker()