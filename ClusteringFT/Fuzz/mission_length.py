import paho.mqtt.client as mqtt
import time
import json
import argparse

MQTT_MISSION_START = "drone/{}/mission-start"  # Replace with actual topic
MQTT_MISSION_END = "drone/{}/mission-end"  # Replace with actual topic
MQTT_BROKER = "mqtt"
MQTT_PORT = 1883

MQTT_SUB = "update_drone"
MQTT_MISSION="drone/{}/mission-spec"
connected = False
start_mission_time = 0

class MissionTimer:
    def __init__(self, uav_name):
        self.start_time = None
        self.end_time = None
        self.uav_name = uav_name
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.start_mission_time = 0 


    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print("Connected to MQTT broker successfully!")
            self.client.subscribe(MQTT_SUB)
            print("sending mission")
            time.sleep(2)
            self.client.publish(MQTT_MISSION,json.dumps(MISSION_FILE))
            self.start_mission_time = time.time()
        else:
            print("Failed to connect to MQTT broker with return code: {}".format(rc))

    def on_message(self, client, userdata, msg):
        msg = json.loads(msg.payload)
        if msg["status"] == "success":
            print("start mission time",self.start_mission_time)
            total_time = time.time() - self.start_mission_time
            print("Total Time for mission: {} seconds".format(total_time))
            self.client.loop_stop()
            self.client.disconnect()

    def start(self):
        global connected
        global start_mission_time
        self.client.connect(MQTT_BROKER,MQTT_PORT)
        self.client.loop_forever()

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--uav_name', type=str, required=True, help='The name of the UAV.')
    args = parser.parse_args()
    MQTT_MISSION = MQTT_MISSION.format(args.uav_name)
    # Load the mission file (optional)
    f = open("missions/FUZZ_MISSION.json")
    MISSION_FILE = json.load(f)
    f.close()
    timer = MissionTimer(args.uav_name)
    timer.start()

