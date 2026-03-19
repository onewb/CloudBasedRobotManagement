from google.cloud import pubsub_v1
import time, json, random

PROJECT_ID = "cloud-based-robot-management"

publisher = pubsub_v1.PublisherClient()
topic_path = publisher.topic_path(PROJECT_ID, "robot-telemetry")
subscription_path=subscriber.subscription_path(PROJECT_ID,"commands-sub")

robot_id = "robot-1"

# 🔹 Publish telemetry , While true , creates artifical robot id/position between 100x100/ and a status
def publish_telemetry():
    while True:
        data = {
            "robot_id": robot_id,                                           #robot ID
            "position": [random.randint(0,100), random.randint(0,100)],     #position []
            "status": random.choice(["idle", "moving", "working"])          #status
        }

        publisher.publish(topic_path, json.dumps(data).encode("utf-8"))     #publish (pub/sub)
        print(f"Sent: {data}")                                              #print data sent
        time.sleep(2)                                                       #repeats every 2 seconds

# 🔹 Receive commands , handles incoming commands from cloud
def callback(message):
    print(f"Received command: {message.data.decode()}")                     #print received command
    message.ack()                                                          #acknowledge command (pub/sub)

# Listens for commands in infinite loop, 10 seconds,  
def listen_for_commands():
    subscriber.subscribe(subscription_path, callback=callback)      # connects to a pub/sub subscritpion to run callback() whenever message recieved
    print("Listening for commands...")
    while True:
        time.sleep(10)

# 🔹 Run both in parallel as threads
if __name__ == "__main__":
    threading.Thread(target=publish_telemetry).start()
    threading.Thread(target=listen_for_commands).start()

