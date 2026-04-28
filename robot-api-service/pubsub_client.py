from google.cloud import pubsub_v1
import json
import os

class PubSubClient:
    def __init__(self):
        self.project_id = os.getenv("GCP_PROJECT_ID", "cloud-based-robot-management")

        self.publisher = pubsub_v1.PublisherClient()

        self.commands_topic_path = self.publisher.topic_path(
            self.project_id, "robot-commands"
        )

    def publish_command(self, data):
        return self.publisher.publish(
            self.commands_topic_path,
            json.dumps(data).encode("utf-8")
        )