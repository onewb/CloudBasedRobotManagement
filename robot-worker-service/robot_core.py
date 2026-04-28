import time
import random
from robot_core import Robot
from job_system import execute_job, assign_task, get_next_job
from pubsub_client import PubSubClient

class RobotWorker:
    def __init__(self, robot_id, pubsub):
        self.robot = Robot(robot_id)
        self.pubsub = pubsub

    def run(self):
        while True:
            self.robot.step()
            execute_job(self.robot)

            telemetry = {
                "robot_id": self.robot.robot_id,
                "position": self.robot.position,
                "status": self.robot.status,
                "battery": self.robot.battery,
                "job": get_next_job(self.robot)
            }

            self.pubsub.publish_telemetry(telemetry)

            print(f"[{self.robot.robot_id}] {telemetry}")

            time.sleep(2)


def start_simulation(num_robots=3):
    pubsub = PubSubClient()

    for i in range(num_robots):
        worker = RobotWorker(f"robot-{i}", pubsub)
        worker.run()