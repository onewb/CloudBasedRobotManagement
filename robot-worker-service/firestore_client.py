from google.cloud import firestore
import os

# Firestore client for robot-worker-service, responsible for updating robot positions and statuses in Firestore, as well as retrieving occupied positions of other robots/

class FirestoreClient:
    def __init__(self):
        self.project_id = os.getenv("GCP_PROJECT_ID", "cloud-based-robot-management")           # allow override via env var, default to cloud-based-robot-management (GCP ID)
        self.db = firestore.Client(project=self.project_id)

    def update_position(self, robot_id, position, status):                                         # updates the robot's current position and status in firestore 
        """Write this robot's current position to Firestore."""
        self.db.collection("robots").document(robot_id).set({
            "position": position,
            "status": status,
        })

    def get_occupied_positions(self, my_robot_id):                                              # returns list of positions occupied by all other robots
        """Return list of positions occupied by all OTHER robots."""
        robots = self.db.collection("robots").stream()
        occupied = []
        for doc in robots:
            if doc.id != my_robot_id:
                data = doc.to_dict()
                if data and "position" in data:
                    occupied.append(data["position"])
        return occupied

    def remove_robot(self, robot_id):                                                           # removes the robot's document from firestore when it shuts down
        """Clean up when robot shuts down."""
        self.db.collection("robots").document(robot_id).delete()