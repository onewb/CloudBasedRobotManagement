from config import JOBS


# =========================
# HELPERS
# =========================

def get_crop_from_position(position):
    x, _ = position

    if 0 <= x <= 33:
        return "tomatoes"
    elif 34 <= x <= 66:
        return "cabbages"
    else:
        return "carrots"


def is_at_location(robot):
    if not robot.field_location:
        return False

    return (
        abs(robot.position[0] - robot.field_location[0]) <= 1 and
        abs(robot.position[1] - robot.field_location[1]) <= 1
    )


# =========================
# STATE TRANSITION ENGINE
# =========================

def reconcile(robot):
    """
    Stateless-safe reconciliation step.
    Designed for Pub/Sub-driven worker calls.
    """

    # 1. No task
    if not robot.task_active:
        robot.status = "idle"
        return

    # 2. Battery safety override
    if robot.battery < 20:
        robot.status = "charging"
        return

    # 3. Charging override
    if robot.status == "charging":
        return

    # 4. Movement phase
    if not is_at_location(robot):
        robot.status = "moving_to_field"
        return

    # 5. Job completion check
    if robot.current_job_index >= len(JOBS):
        robot.status = "completed_cycle"
        robot.task_active = False
        robot.current_job_index = 0
        robot.job_progress = 0
        robot.current_job = None        # add this
        robot.field_location = None     # add this
        robot.target_position = None    # add this
        robot.crop_type = None          # add this
        return

    job = JOBS[robot.current_job_index]

    # 6. Execute job step
    robot.status = f"{job}_in_progress"
    robot.job_progress += 1

    print(
        f"[{robot.robot_id}] RECONCILE {job} "
        f"({robot.job_progress}/3) crop={robot.crop_type}"
    )

    # 7. Transition condition
    if robot.job_progress >= 3:
        print(f"[{robot.robot_id}] Job complete: {job}")
        robot.job_progress = 0
        robot.current_job_index += 1


# =========================
# TASK ASSIGNMENT
# =========================

def assign_task(robot, field_location):
    robot.field_location = field_location
    robot.current_job = "greenhouse_task"
    robot.task_active = True
    robot.status = "assigned"
    from config import JOBS



def execute_job(robot):
    """
    Worker-compatible execution wrapper
    """
    if not robot.task_active:
        return

    if robot.current_job == "greenhouse_task":
        # simulate progress
        robot.status = "working"

        # simple completion condition
        if robot.position == list(robot.field_location):
            robot.task_active = False
            robot.status = "completed"
            robot.current_job = None


def get_next_job(robot):
    """
    Return current job safely for telemetry
    """
    if robot.current_job_index < len(JOBS):
        return JOBS[robot.current_job_index]
    return None