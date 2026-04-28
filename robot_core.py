import random
from config import GRID_MIN, GRID_MAX


class Robot:
    def __init__(self, robot_id):
        self.robot_id = robot_id

        self.position = [
            random.randint(GRID_MIN, GRID_MAX),
            random.randint(GRID_MIN, GRID_MAX)
        ]

        self.status = "idle"
        self.battery = 100

        self.current_job_index = 0
        self.job_progress = 0

        self.crop_type = None
        self.field_location = None
        self.task_active = False

    # =========================
    # SAFETY
    # =========================
    def clamp_position(self):
        self.position[0] = max(GRID_MIN, min(GRID_MAX, self.position[0]))
        self.position[1] = max(GRID_MIN, min(GRID_MAX, self.position[1]))

    # =========================
    # MOVEMENT (PURE ACTIONS ONLY)
    # =========================
    def move_toward(self, target):
        if not target:
            return False

        moved = False

        if self.position[0] < target[0]:
            self.position[0] += 1
            moved = True
        elif self.position[0] > target[0]:
            self.position[0] -= 1
            moved = True

        if self.position[1] < target[1]:
            self.position[1] += 1
            moved = True
        elif self.position[1] > target[1]:
            self.position[1] -= 1
            moved = True

        self.clamp_position()
        return moved

    # =========================
    # PURE STATE STEP (NO AUTONOMY)
    # =========================
    def step(self, command=None):
        """
        Event-driven step function.
        Behavior is controlled externally via Pub/Sub or worker loop.
        """

        moved = False

        # -------------------------
        # Battery safety
        # -------------------------
        if self.battery < 20:
            self.status = "charging"
            self.battery = min(100, self.battery + 1)
            return {"status": self.status, "battery": self.battery}

        # -------------------------
        # Charging mode
        # -------------------------
        if self.status == "charging":
            self.battery = min(100, self.battery + 2)

            if self.battery >= 100:
                self.status = "idle"
                self.task_active = False

            return {"status": self.status, "battery": self.battery}

        # -------------------------
        # External command override (Pub/Sub)
        # -------------------------
        if command:
            if command["type"] == "move":
                moved = self.move_toward(command["target"])
                self.status = "moving"

            elif command["type"] == "work":
                self.status = "working"

            elif command["type"] == "idle":
                self.status = "idle"

        # -------------------------
        # Task-based behavior (if assigned)
        # -------------------------
        elif self.task_active and self.field_location:
            if self.position != self.field_location:
                moved = self.move_toward(self.field_location)
                self.status = "moving_to_field"
            else:
                self.status = "working"

        # -------------------------
        # Battery drain only on activity
        # -------------------------
        if moved or self.status != "idle":
            self.battery = max(0, self.battery - 0.2)

        return {
            "moved": moved,
            "status": self.status,
            "battery": self.battery
        }