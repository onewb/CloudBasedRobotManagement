from google.cloud import pubsub_v1
import json
import os

# Pub/Sub client for robot-api-service, responsible for publishing commands to the robot-commands topic. 
# This client is used by the API service to send commands to the robots based on incoming HTTP requests. 
# It includes error handling to ensure that issues with Pub/Sub initialization or publishing are logged without crashing the service.

class PubSubClient:
    def __init__(self, robot_id=None):                  # initialize Pub/Sub client for robot-worker-service, setting up topic paths and a subscription for receiving commands. If a robot_id is provided, it creates a dedicated subscription for that robot; otherwise, it falls back to a shared subscription. Also includes error handling for Pub/Sub initialization.
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

    def _ensure_subscription(self):                                         # helper function to check if the robot's subscription exists and create it if not, ensuring that each robot has its own subscription for receiving commands without interference.
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

    def publish_telemetry(self, telemetry: dict):                           # publish telemetry data to the robot-telemetry topic, with error handling to catch and log any issues that occur during publishing.
        try:
            data = json.dumps(telemetry).encode("utf-8")
            self.publisher.publish(self.telemetry_topic_path, data=data)
        except Exception as e:
            print(f"[PubSubClient] ⚠️ Failed to publish telemetry: {e}")

    def subscribe_to_commands(self, callback):                              # subscribe to the robot's command subscription, setting up a callback function to handle incoming messages. Includes flow control to limit the number of messages processed concurrently and error handling to catch issues during subscription setup.
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

    def delete_subscription(self):                                            # clean up the robot's subscription when it shuts down, ensuring that resources are freed and that the robot no longer receives commands. Includes error handling to catch and log any issues that occur during subscription deletion.
        """Delete this robot's subscription on shutdown."""
        try:
            self.subscriber.delete_subscription(
                request={"subscription": self.subscription_path}
            )
            print(f"[PubSubClient] 🗑️ Subscription deleted: {self.subscription_id}")
        except Exception as e:
            print(f"[PubSubClient] Error deleting subscription: {e}")

    def close(self):                                                        # close the Pub/Sub subscriber client, with error handling to catch and log any issues that occur during closing.   
        try:
            self.subscriber.close()
            print("[PubSubClient] Subscriber closed.")
        except Exception as e:
            print(f"[PubSubClient] Error closing subscriber: {e}")