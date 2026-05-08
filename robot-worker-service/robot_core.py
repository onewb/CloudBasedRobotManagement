from job_system import assign_task, reconcile, get_crop_from_position
from config import GRID_MAX
# Robot class representing each robot in the system, responsible for maintaining its own state, position, and job information. 
# Contains methods for setting and clearing tasks, as well as the main run_step function that handles movement, collision avoidance, Firestore updates, and job reconciliation in each simulation step.


class Robot:
    def __init__(self, robot_id, firestore_client=None):        # initialize robot with default position, status, and job state. Accepts a Firestore client for updating position and status in the database, as well as a robot ID for identifying the robot in Pub/Sub subscriptions and Firestore documents.
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

    def set_task(self, job_type, field_location):       # set a new task for the robot, updating its current job, target location, and status accordingly. This function is called when the robot receives a new command, and it prepares the robot to start working on the assigned task.
        self.current_job = job_type
        self.field_location = list(field_location)
        self.target_position = list(field_location)
        self.crop_type = get_crop_from_position(field_location)
        assign_task(self, field_location)

    def clear_task(self):               # clear the robot's current task, resetting its job state and status. This function is called when a task is completed or when the robot receives a stop command, ensuring that the robot is ready for new assignments. It also sets a flag to indicate that the robot has completed a cycle, which can be used to trigger any necessary cleanup or state updates in the job reconciliation logic.
        self.current_job = None
        self.field_location = None
        self.target_position = None
        self.task_active = False
        self.current_job_index = 0
        self.job_progress = 0
        self.crop_type = None
        self.status = "idle"

    def run_step(self):                     # main function to be called in each simulation step, responsible for moving the robot towards its target position while checking for collisions, updating its position and status in Firestore, and reconciling its job state. This function encapsulates the core logic of the robot's behavior during each step of the simulation. It handles movement, collision avoidance, and job execution in a cohesive manner.
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
        reconcile(self)                                     # call the reconcile function to determine the robot's next status and actions based on its current job, progress, and location. This allows the robot to transition between different states such as moving towards a field location, executing a job step, or completing a task cycle in a structured manner.