from google.cloud import pubsub_v1
import time, json, random, threading

PROJECT_ID = "cloud-based-robot-management"

# Create clients
publisher = pubsub_v1.PublisherClient()
subscriber = pubsub_v1.SubscriberClient()

# Define paths
topic_path = publisher.topic_path(PROJECT_ID, "robot-telemetry")
subscription_path = subscriber.subscription_path(PROJECT_ID, "commands-sub")

robot_id = "robot-1"

# 🔹 Publish telemetry
def publish_telemetry():
    while True:
        data = {
            "robot_id": robot_id,
            "position": [random.randint(0,100), random.randint(0,100)],
            "status": random.choice(["idle", "moving", "working"])
        }

        publisher.publish(topic_path, json.dumps(data).encode("utf-8"))
        print(f"Sent: {data}")
        time.sleep(2)

# 🔹 Receive commands
def callback(message):
    print(f"Received command: {message.data.decode()}")
    message.ack()

# 🔹 Listen for commands
def listen_for_commands():
    subscriber.subscribe(subscription_path, callback=callback)
    print("Listening for commands...")
    while True:
        time.sleep(10)

# 🔹 Run both in parallel
if __name__ == "__main__":
    threading.Thread(target=publish_telemetry).start()
    threading.Thread(target=listen_for_commands).start()

