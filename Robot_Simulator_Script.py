####### OLD SIMULATOR - NOT USED IN FINAL VERSION ########## LOCAL only
import time
import json
import random
import threading
from queue import Queue

# =========================
# GLOBAL SIMULATED PUB/SUB
# =========================
telemetry_queue = Queue()

JOBS = [
    "till_soil",
    "plant_seeds",
    "water_crop",
    "harvest_crop"
]

# =========================
# ZONE SYSTEM
# =========================
def get_crop_from_position(position):
    x, y = position

    if 0 <= x <= 33:
        return "tomatoes"
    elif 34 <= x <= 66:
        return "cabbages"
    elif 67 <= x <= 100:
        return "carrots"
    return None


# =========================
# ROBOT CORE
# =========================
class Robot:
    def __init__(self, robot_id):
        self.robot_id = robot_id
        self.position = [random.randint(0, 100), random.randint(0, 100)]
        self.status = "idle"
        self.battery = 100

        self.current_job_index = 0
        self.job_progress = 0

        self.crop_type = None
        self.field_location = None
        self.task_active = False

    def move_toward(self, target):
        if self.position[0] < target[0]:
            self.position[0] += 1
        elif self.position[0] > target[0]:
            self.position[0] -= 1

        if self.position[1] < target[1]:
            self.position[1] += 1
        elif self.position[1] > target[1]:
            self.position[1] -= 1

    def step(self):
        if self.task_active and self.field_location:
            self.move_toward(self.field_location)
            self.status = "working"
        else:
            self.position[0] += random.randint(-1, 1)
            self.position[1] += random.randint(-1, 1)
            self.status = "moving"

        self.battery -= 0.2

        if self.battery < 20:
            self.status = "charging"
            self.battery += 1
            if self.battery >= 100:
                self.battery = 100
                self.status = "idle"


# =========================
# JOB SYSTEM
# =========================
def get_next_job(robot):
    if robot.current_job_index < len(JOBS):
        return JOBS[robot.current_job_index]
    return None


def complete_job(robot):
    robot.current_job_index += 1

    if robot.current_job_index >= len(JOBS):
        print(f"[{robot.robot_id}] Completed full cycle for {robot.crop_type}")
        robot.current_job_index = 0
        robot.job_progress = 0


def execute_job(robot):
    if not robot.task_active:
        return

    robot.crop_type = get_crop_from_position(robot.position)

    job = get_next_job(robot)
    if job is None:
        return

    robot.job_progress += 1
    robot.status = f"{job}_in_progress"

    print(f"[{robot.robot_id}] {job} ({robot.crop_type}) {robot.job_progress}/3")

    if robot.job_progress >= 3:
        robot.job_progress = 0
        complete_job(robot)


# =========================
# ROBOT WORKER (CLEAN)
# =========================
class RobotWorker:
    def __init__(self, robot_id):
        self.robot = Robot(robot_id)
        self.command_queue = Queue()

    def publish_telemetry(self):
        while True:
            self.robot.step()
            execute_job(self.robot)

            data = {
                "robot_id": self.robot.robot_id,
                "position": self.robot.position,
                "status": self.robot.status,
                "battery": round(self.robot.battery, 2),
                "crop": self.robot.crop_type,
                "current_job": get_next_job(self.robot),
                "field_location": self.robot.field_location
            }

            telemetry_queue.put(data)
            print(f"[{self.robot.robot_id}] TELEMETRY {data}")

            time.sleep(2)

    def listen_for_commands(self):
        print(f"[{self.robot.robot_id}] LISTENER STARTED")

        while True:
            if not self.command_queue.empty():
                cmd = json.loads(self.command_queue.get())

                if cmd["type"] == "assign_greenhouse_task":
                    self.robot.field_location = cmd["field_location"]
                    self.robot.task_active = True
                    self.robot.current_job_index = 0

                elif cmd["type"] == "stop":
                    self.robot.task_active = False
                    self.robot.status = "idle"

            time.sleep(0.5)


# =========================
# CONTROLLER (MULTI-ROBOT)
# =========================
def fake_controller(robots):
    time.sleep(3)

    for r in robots:
        r.command_queue.put(json.dumps({
            "type": "assign_greenhouse_task",
            "field_location": [
                random.randint(0, 100),
                random.randint(0, 100)
            ]
        }))


# =========================
# TELEMETRY VIEWER
# =========================
def telemetry_consumer():
    while True:
        if not telemetry_queue.empty():
            print(f"[TELEMETRY RECEIVED] {telemetry_queue.get()}")
        time.sleep(1)


# =========================
# MAIN
# =========================
if __name__ == "__main__":
    print("🚀 MULTI-ROBOT GREENHOUSE SIMULATION")

    robots = []

    for i in range(3):
        worker = RobotWorker(f"robot-{i+1}")
        robots.append(worker)

        threading.Thread(target=worker.publish_telemetry, daemon=True).start()
        threading.Thread(target=worker.listen_for_commands, daemon=True).start()

    threading.Thread(target=telemetry_consumer, daemon=True).start()
    threading.Thread(target=fake_controller, args=(robots,), daemon=True).start()

    while True:
        time.sleep(10)