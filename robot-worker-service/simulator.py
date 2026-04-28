#multi robot engine

import json
import time
import random

from robot_core import Robot
from job_system import execute_job, assign_task, get_next_job
from pubsub_client import PubSubClient


class RobotWorker:
    """
    Single robot worker instance.
    In Kubernetes, many pods run many workers OR 1 worker per pod.
    """

    def __init__(self, robot_id, pubsub: PubSubClient):
        self.robot = Robot(robot_id)
        self.pubsub = pubsub

    # =========================
    # MAIN WORK LOOP
    # =========================
    def run_step(self):
        """
        One iteration of robot logic.
        Called repeatedly instead of infinite thread loops.
        """

        self.robot.step()
        execute_job(self.robot)

        telemetry = {
            "robot_id": self.robot.robot_id,
            "position": self.robot.position,
            "status": self.robot.status,
            "battery": round(self.robot.battery, 2),
            "crop": self.robot.crop_type,
            "current_job": get_next_job(self.robot),
            "field_location": self.robot.field_location
        }

        self.pubsub.publish_telemetry(telemetry)

        print(f"[{self.robot.robot_id}] TELEMETRY → {telemetry}")

    # =========================
    # COMMAND HANDLER
    # =========================
    def handle_command(self, message):
        try:
            cmd = json.loads(message.data.decode())

            if cmd.get("robot_id") != self.robot.robot_id:
                message.ack()
                return

            print(f"[{self.robot.robot_id}] COMMAND → {cmd}")

            if cmd["type"] == "assign_greenhouse_task":
                assign_task(self.robot, cmd["field_location"])

            elif cmd["type"] == "stop":
                self.robot.task_active = False
                self.robot.status = "idle"

            message.ack()

        except Exception as e:
            print(f"[ERROR] {e}")
            message.nack()


# =========================
# WORKER PROCESS ENTRYPOINT
# =========================
def start_worker(robot_id=None, run_forever=True):
    """
    Kubernetes-safe worker entrypoint.
    NO threading fleet simulation.
    NO infinite multi-robot spawning.
    """

    pubsub = PubSubClient()

    # If no robot_id provided, assign one worker identity
    robot_id = robot_id or f"robot-{random.randint(1000,9999)}"

    worker = RobotWorker(robot_id, pubsub)

    print(f"🤖 Worker started for {robot_id}")

    # =========================
    # SUBSCRIBE TO COMMANDS
    # =========================
    def callback(message):
        worker.handle_command(message)

    pubsub.subscribe_to_commands(callback)

    # =========================
    # MAIN LOOP (controlled, safe for pods)
    # =========================
    while run_forever:
        worker.run_step()
        time.sleep(2)