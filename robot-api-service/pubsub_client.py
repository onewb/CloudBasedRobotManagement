from google.cloud import pubsub_v1
import json
import os


class PubSubClient:
    def __init__(self):
        self.project_id = os.getenv(    # allow override via env var, default to cloud-based-robot-management (GCP ID)
            "GCP_PROJECT_ID",
            "cloud-based-robot-management"
        )

        try:                                                                # initialize Pub/Sub clients, handle exceptions gracefully 
            self.publisher = pubsub_v1.PublisherClient()
            self.subscriber = pubsub_v1.SubscriberClient()
        except Exception as e:
            print(f"[PubSub INIT ERROR] {e}")
            self.publisher = None
            self.subscriber = None

        self.commands_topic_path = None
        if self.publisher:
            self.commands_topic_path = self.publisher.topic_path(           #construct topic path for robot commands
                self.project_id,
                "robot-commands"
            )

    def publish_command(self, data):                                        # publish a command message to the robot-commands topic, handle uninitialized publisher gracefully
        if not self.publisher or not self.commands_topic_path:
            print("[WARN] PubSub not initialized. Skipping publish.")
            return None

        return self.publisher.publish(
            self.commands_topic_path,
            json.dumps(data).encode("utf-8")
        )