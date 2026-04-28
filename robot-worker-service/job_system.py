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
    robot.crop_type = get_crop_from_position(field_location)

    robot.task_active = True
    robot.current_job_index = 0
    robot.job_progress = 0

    robot.status = "assigned"