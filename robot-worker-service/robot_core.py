from job_system import assign_task, reconcile, get_crop_from_position
from config import GRID_MAX

class Robot:
    def __init__(self, robot_id, firestore_client=None):
        self.robot_id = robot_id

        self.position = [0, 0]
        self.status = "idle"

        self.current_job = None
        self.field_location = None
        self.target_position = None

        self.task_active = False
        self.current_job_index = 0
        self.job_progress = 0
        self.crop_type = None
        self.battery = 100
        self.cycle_complete_pending = False

        self.scanning = False
        self.scan_position = None
        self.scan_max_x=GRID_MAX #default, overridden per command

        self.firestore = firestore_client  # injected from simulator

    def set_task(self, job_type, field_location):
        self.current_job = job_type
        self.field_location = list(field_location)
        self.target_position = list(field_location)
        self.crop_type = get_crop_from_position(field_location)
        assign_task(self, field_location)

    def clear_task(self):
        self.current_job = None
        self.field_location = None
        self.target_position = None
        self.task_active = False
        self.current_job_index = 0
        self.job_progress = 0
        self.crop_type = None
        self.status = "idle"

    def run_step(self):
        # move toward target if not there yet
        if self.target_position and self.position != self.target_position:
            tx, ty = self.target_position
            x, y = self.position

            # calculate next position
            next_x = x + (1 if x < tx else -1 if x > tx else 0)
            next_y = y + (1 if y < ty else -1 if y > ty else 0)
            next_pos = [next_x, next_y]

            # check for collision before moving
            if self.firestore:
                occupied = self.firestore.get_occupied_positions(self.robot_id)
                if next_pos in occupied:
                    print(f"[{self.robot_id}] ⚠️ Cell {next_pos} occupied, waiting...")
                    self.status = "waiting"
                    # still update firestore with current position
                    self.firestore.update_position(self.robot_id, self.position, self.status)
                    return

            self.position = next_pos

        # update firestore with new position
        if self.firestore:
            self.firestore.update_position(self.robot_id, self.position, self.status)

        # reconcile job state
        reconcile(self)