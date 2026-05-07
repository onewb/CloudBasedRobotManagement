from google.cloud import pubsub_v1
import json
import os


class PubSubClient:
    def __init__(self, robot_id=None):
        self.project_id = os.getenv("GCP_PROJECT_ID", "cloud-based-robot-management")
        self.robot_id = robot_id
        self.telemetry_topic = "robot-telemetry"
        self.commands_topic = "robot-commands"

        self.subscriber = pubsub_v1.SubscriberClient()
        self.publisher = pubsub_v1.PublisherClient()

        self.telemetry_topic_path = self.publisher.topic_path(
            self.project_id, self.telemetry_topic
        )
        self.commands_topic_path = self.publisher.topic_path(
            self.project_id, self.commands_topic
        )

        # per-pod subscription if robot_id provided, else fall back to shared
        if robot_id:
            self.subscription_id = f"robot-commands-{robot_id}"
        else:
            self.subscription_id = "robot-commands-sub"

        self.subscription_path = self.subscriber.subscription_path(
            self.project_id, self.subscription_id
        )

        if robot_id:
            self._ensure_subscription()

    def _ensure_subscription(self):
        """Create this robot's subscription if it doesn't exist yet."""
        try:
            self.subscriber.get_subscription(
                request={"subscription": self.subscription_path}
            )
            print(f"[PubSubClient] Subscription exists: {self.subscription_id}")
        except Exception:
            print(f"[PubSubClient] Creating subscription: {self.subscription_id}")
            self.subscriber.create_subscription(
                request={
                    "name": self.subscription_path,
                    "topic": self.commands_topic_path,
                }
            )
            print(f"[PubSubClient] ✅ Subscription created: {self.subscription_id}")

    def publish_telemetry(self, telemetry: dict):
        try:
            data = json.dumps(telemetry).encode("utf-8")
            self.publisher.publish(self.telemetry_topic_path, data=data)
        except Exception as e:
            print(f"[PubSubClient] ⚠️ Failed to publish telemetry: {e}")

    def subscribe_to_commands(self, callback):
        print("🚀 Starting Pub/Sub subscription...")
        try:
            flow_control = pubsub_v1.types.FlowControl(max_messages=5)
            streaming_pull_future = self.subscriber.subscribe(
                self.subscription_path,
                callback=callback,
                flow_control=flow_control
            )
            print("✅ Subscription active:", self.subscription_path)
            return streaming_pull_future
        except Exception as e:
            print("❌ Subscription FAILED:", str(e))
            raise

    def delete_subscription(self):
        """Delete this robot's subscription on shutdown."""
        try:
            self.subscriber.delete_subscription(
                request={"subscription": self.subscription_path}
            )
            print(f"[PubSubClient] 🗑️ Subscription deleted: {self.subscription_id}")
        except Exception as e:
            print(f"[PubSubClient] Error deleting subscription: {e}")

    def close(self):
        try:
            self.subscriber.close()
            print("[PubSubClient] Subscriber closed.")
        except Exception as e:
            print(f"[PubSubClient] Error closing subscriber: {e}")