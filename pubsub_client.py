from google.cloud import pubsub_v1
import json
import os


class PubSubClient:
    def __init__(self):
        self.project_id = os.getenv("GCP_PROJECT_ID")

        self.publisher = pubsub_v1.PublisherClient()
        self.subscriber = pubsub_v1.SubscriberClient()

        self.telemetry_topic_path = self.publisher.topic_path(
            self.project_id, "robot-telemetry"
        )

        self.commands_subscription_path = self.subscriber.subscription_path(
            self.project_id, "commands-sub"
        )

        self.flow_control = pubsub_v1.types.FlowControl(
            max_messages=10
        )

    # Publish telemetry
    def publish_telemetry(self, data):
        return self.publisher.publish(
            self.telemetry_topic_path,
            json.dumps(data).encode("utf-8")
        )

    # Subscribe to commands
    def subscribe_to_commands(self, callback):
        streaming_pull_future = self.subscriber.subscribe(
            self.commands_subscription_path,
            callback=callback,
            flow_control=self.flow_control
        )

        print("📡 Listening for commands...")
        return streaming_pull_future