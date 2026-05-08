from config import JOBS, GRID_MIN, GRID_MAX

# Job system for robot-worker-service, responsible for managing robot state transitions and task assignments based on current job progress and field location. 
# Contains helper functions for determining crop types and scan locations, as well as the main reconcile function that implements the state transition logic.
# Also includes task assignment functions for both specific field tasks and full grid scans
# =========================
# HELPERS
# =========================

def get_crop_from_position(position):           #determine crop type based on x coordinate of the position, using predefined zones (0-33 = tomatoes, 34-66 = cabbages, 67-100 = carrots)
    x, _ = position

    if 0 <= x <= 33:
        return "tomatoes"
    elif 34 <= x <= 66:
        return "cabbages"
    else:
        return "carrots"


def is_at_location(robot):                      #check if robot is within 1 unit of its target field location, return False if no target location is set
    if not robot.field_location:
        return False

    return (
        abs(robot.position[0] - robot.field_location[0]) <= 1 and
        abs(robot.position[1] - robot.field_location[1]) <= 1
    )


def get_next_scan_location(robot):              # calculate the next cell in the snake pattern based on the robot's current scan position, alternating direction on each row, and respecting the robots assigned max_x boundary. Returns none if the scan is complete.
    """
    Returns the next [x, y] cell in the snake pattern.
    Even x rows scan y forward (0→100), odd x rows scan y backward (100→0).
    Returns None when the full grid is complete.
    """
    x, y = robot.scan_position
    max_x = robot.scan_max_x  # each robot knows its own boundary

    if x % 2 == 0:
        next_y = y + 1
        if next_y > GRID_MAX:
            next_x = x + 1
            next_y = GRID_MAX
        else:
            next_x = x
    else:
        next_y = y - 1
        if next_y < GRID_MIN:
            next_x = x + 1
            next_y = GRID_MIN
        else:
            next_x = x

    if next_x > max_x:
        return None  # this robot's section complete

    return [next_x, next_y]


# =========================
# STATE TRANSITION ENGINE
# =========================

def reconcile(robot):                       # main state transition function, called on every position update from the robot. Determines what the robot's next status and actions should be based on its current job, progress, and location. Handles movement towards field locations, execution of job steps, and completion of tasks including full grid scans.
    # 1. No task
    if not robot.task_active:
        robot.status = "idle"
        return

    # 2. Movement phase
    if not is_at_location(robot):
        robot.status = "moving_to_field"
        return

    # 3. Job completion check
    if robot.current_job_index >= len(JOBS):
        if not robot.cycle_complete_pending:
            # first step — broadcast completed_cycle, don't advance yet
            robot.status = "completed_cycle"
            robot.cycle_complete_pending = True
            return
        
        # second step — now advance
        robot.cycle_complete_pending = False
        robot.current_job_index = 0
        robot.job_progress = 0
        robot.crop_type = get_crop_from_position(robot.position)

        if robot.scanning:
            next_loc = get_next_scan_location(robot)
            if next_loc is None:
                robot.status = "scan_complete"
                robot.task_active = False
                robot.scanning = False
                robot.current_job = None
                robot.field_location = None
                robot.target_position = None
                robot.crop_type = None
                robot.scan_position = None
                print(f"[{robot.robot_id}] ✅ Full grid scan complete.")
            else:
                robot.scan_position = next_loc
                robot.field_location = list(next_loc)
                robot.target_position = list(next_loc)
                robot.crop_type = get_crop_from_position(next_loc)
                robot.status = "moving_to_field"
                print(f"[{robot.robot_id}] 🔁 Next scan cell → {next_loc}")
        else:
            robot.status = "completed_cycle"
            robot.task_active = False
            robot.current_job = None
            robot.field_location = None
            robot.target_position = None
            robot.crop_type = None
        return
    job = JOBS[robot.current_job_index]

    # 4. Execute job step
    robot.status = f"{job}_in_progress"
    robot.job_progress += 1

    print(
        f"[{robot.robot_id}] RECONCILE {job} "
        f"({robot.job_progress}/3) crop={robot.crop_type}"
    )

    if robot.job_progress >= 3:
        print(f"[{robot.robot_id}] Job complete: {job}")
        robot.job_progress = 0
        robot.current_job_index += 1


# =========================
# TASK ASSIGNMENT
# =========================

def assign_task(robot, field_location):             # assign a specific field task to the robot, setting its target location and job type. This is used for tasks like greenhouse assignments where the robot needs to go to a specific coordinate rather than performing a full grid scan.
    robot.field_location = list(field_location)
    robot.target_position = list(field_location)
    robot.current_job = "greenhouse_task"
    robot.task_active = True
    robot.scanning = False
    robot.status = "assigned"


def assign_field_scan(robot, start_x=0):            # assign a full grid scan task to the robot, initializing its scan position and setting the appropriate job type. The robot will then autonomously move through the grid in a snake pattern, scanning each cell until it reaches its assigned max_x boundary.
    """
    Kick off a full 100x100 grid snake scan from [0,0].
    """
    start = [start_x, GRID_MIN]
    robot.scan_position = list(start)
    robot.field_location = list(start)
    robot.target_position = list(start)
    robot.current_job = "field_scan"
    robot.task_active = True
    robot.scanning = True
    robot.current_job_index = 0
    robot.job_progress = 0
    robot.crop_type = get_crop_from_position(start)
    robot.status = "assigned"
    print(f"[{robot.robot_id}] 🌱 Field scan started from {start}")

def assign_crop_scan(robot, crop_type):         # assign a crop-specific scan task to the robot, determining the appropriate starting location based on the crop type and initializing the robot's state for performing a snake pattern scan within that crop's zone.
    from config import CROP_ZONES

    if crop_type not in CROP_ZONES:
        print(f"[{robot.robot_id}] ❌ Unknown crop type: {crop_type}")
        return

    zone = CROP_ZONES[crop_type]
    start = [zone["min_x"], GRID_MIN]

    robot.scan_position = list(start)
    robot.field_location = list(start)
    robot.target_position = list(start)
    robot.current_job = f"crop_scan_{crop_type}"
    robot.task_active = True
    robot.scanning = True
    robot.scan_max_x = zone["max_x"]
    robot.current_job_index = 0
    robot.job_progress = 0
    robot.crop_type = crop_type
    robot.status = "assigned"
    print(f"[{robot.robot_id}] 🌱 Crop scan started for {crop_type} from {start} to x={zone['max_x']}")