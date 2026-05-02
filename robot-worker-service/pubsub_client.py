from google.cloud import pubsub_v1
import json


class PubSubClient:
    def __init__(self):
        self.project_id = "cloud-based-robot-management"

        self.command_subscription = "robot-commands-sub"
        self.telemetry_topic = "robot-telemetry"

        self.subscriber = pubsub_v1.SubscriberClient()
        self.publisher = pubsub_v1.PublisherClient()

        self.subscription_path = self.subscriber.subscription_path(
            self.project_id,
            self.command_subscription
        )

        self.telemetry_topic_path = self.publisher.topic_path(
            self.project_id,
            self.telemetry_topic
        )

    # TELEMETRY
    def publish_telemetry(self, telemetry: dict):
        try:
            data = json.dumps(telemetry).encode("utf-8")
            future = self.publisher.publish(self.telemetry_topic_path, data=data)
        except Exception as e:
            print(f"[PubSubClient] ⚠️ Failed to publish telemetry: {e}")

    # COMMAND SUBSCRIPTION
    def subscribe_to_commands(self, callback):
        print("🚀 Starting Pub/Sub subscription...")

        try:
            flow_control = pubsub_v1.types.FlowControl(max_messages=5)

            streaming_pull_future = self.subscriber.subscribe(
                self.subscription_path,
                callback=callback,
                flow_control=flow_control
            )

            print("✅ Subscription created:", self.subscription_path)
            return streaming_pull_future

        except Exception as e:
            print("❌ Subscription FAILED:", str(e))
            raise

    # CLEAN SHUTDOWN
    def close(self):
        try:
            self.subscriber.close()
            print("[PubSubClient] Subscriber closed.")
        except Exception as e:
            print(f"[PubSubClient] Error closing subscriber: {e}")