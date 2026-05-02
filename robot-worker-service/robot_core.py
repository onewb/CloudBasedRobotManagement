from job_system import assign_task, reconcile, get_crop_from_position


class Robot:
    def __init__(self, robot_id):
        self.robot_id = robot_id

        # position
        self.position = [0, 0]

        # state
        self.status = "idle"

        # task fields
        self.current_job = None
        self.field_location = None
        self.target_position = None

        # job system fields
        self.task_active = False
        self.current_job_index = 0
        self.job_progress = 0
        self.crop_type = None
        self.battery = 100  # battery logic removed but field kept for reconcile

    def set_task(self, job_type, field_location):
        self.current_job = job_type
        self.field_location = list(field_location)
        self.target_position = list(field_location)
        self.crop_type = get_crop_from_position(field_location)
        assign_task(self, field_location)  # hands off to job system

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
        # movement phase — only move if not yet at target
        if self.target_position and self.position != self.target_position:
            tx, ty = self.target_position
            x, y = self.position

            if x < tx:
                x += 1
            elif x > tx:
                x -= 1

            if y < ty:
                y += 1
            elif y > ty:
                y -= 1

            self.position = [x, y]

        # always reconcile job state after movement
        reconcile(self)