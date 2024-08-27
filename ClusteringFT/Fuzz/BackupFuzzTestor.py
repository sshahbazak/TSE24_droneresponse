from collections import defaultdict
import asyncio
import argparse 
import threading
import paho.mqtt.client as mqtt
import time 
import subprocess
import json
import collections 
import signal
import sys 
import logging 
import queue 
import pickle
import os 
from geometry_msgs.msg import PoseStamped
from dataclasses import dataclass, field, asdict
from time import gmtime, strftime
import numpy as np
from typing import Tuple
from DockerInterface import Docker_Interface
from entities import Fuzz_Test
from BackupROSInterface import ROS_Interface
import sys 

#testing

#FLIGHT MODES 
MODES = ['ALTCTL', 'POSCTL', 'OFFBOARD', 'STABILIZED']
#neutral is 550
THROTTLE_POS_ALTCTL = [0,260,550,600,615]
#netural is 435
THROTTLE_STABILIZE = [0,225,435,445,450]
#default
THROTTLE_DEFAULT = [-100,0,100,300,570]

GEOFENCE_ACTIONS = {0: "None",1:"Warning",2:"Hold mode", 3:"Return mode", 4: "Terminate", 5:"Land mode"}
MODE_TO_THROTTLE = {
    "STABILIZED": THROTTLE_STABILIZE,
    "POSCTL": THROTTLE_POS_ALTCTL,
    "ALTCTL": THROTTLE_POS_ALTCTL
}

#Flight MODES and STATES
MODES = ['ALTCTL', 'POSCTL', 'OFFBOARD', 'STABILIZED', 'AUTO.LOITER', 'AUTO.RTL', 'AUTO.LAND']
STATES = ['Takeoff','BriarWaypoint','BriarWaypoint2','BriarWaypoint3','BriarHover','Land','Disarm']

#MAVROS SERVICE TOPICS 
SET_PARAM_TOPIC = 'mavros/param/set'
GET_PARAM_TOPIC = 'mavros/param/get'
SEND_CMD = 'mavros/cmd/command'
MAV_STATE = '/mavros/state'
SERVICES = [SEND_CMD,GET_PARAM_TOPIC,SET_PARAM_TOPIC]

#MQTT MISSION SENDER PUB TOPIC and SUB TOPIC for onboard updates 
MQTT_MISSION="drone/{}/mission-spec"
MQTT_SUB = "update_drone"

#BLUEPRINT MISSION
MISSION_FILE = 'missions/FUZZ_MISSION.json'
class Fuzz_Testor():
    def __init__(self,uav_id="Polkadot") -> None:
        signal.signal(signal.SIGINT, self.signal_handler)
        self.uav_id = uav_id
        #prepare threading events and bind to class 
        self.init_shared_variables()
        #prepare MQTT, and Docker Handler
        #we attach MQTT to the Fuzz_Testor since it has our main testing logic 
        self.__init_mqtt()

        self.mqtt_connected.wait()
        self.__init_docker_interface()
        self.__init_mission_file()

        #init value for mission completion time 
        self.threshold = 74
        #start time checking thread 
        self.time_thread = threading.Thread(target=self.check_time_threshold)
        self.time_thread.start()

        self.mission_thread = threading.Thread(target=self.send_mission_thread)
        self.mission_thread.start()

        '''
        self.cleanup_dict = {
            "kill_command": self.kill_cleanup,
            "mode_switch": self.mode_cleanup,
            "geofence_params": self.geofence_cleanup,
            "rtl_altitude": self.rtl_cleanup,
        }
        '''
        self.fuzz_type = None 
        self.executed_tests = set()

    
    def save_executed_tests(self):
        with open('executed_tests.pkl', 'wb') as f:
            pickle.dump(self.executed_tests, f)
                
    def load_executed_tests(self):
        # Define file path
        file_path = 'executed_tests.pkl'
        
        # Load executed tests from the file if it exists
        # for geofence tests it will be a set not partitioned by states
        self.executed_tests = self._load_executed_tests()
        
        # Process the loaded tests for standard fuzzes
        # for standard tests (with states) we need to create a dictionary
        if 'state' in self.fuzz_type:
            self.tested_modes_by_state = defaultdict(set)
            self._process_executed_tests()

    def _load_executed_tests(self):
        if os.path.exists('executed_tests.pkl'):
            try:
                with open('executed_tests.pkl', 'rb') as f:
                    print('[fuzz_testor] found executed tests, loading...')
                    return pickle.load(f)
            except EOFError:
                return set()
        else:
            return set()

    def _process_executed_tests(self):
        includes_modes = '_mode' in self.fuzz_type
        includes_throttles = '_throttle' in self.fuzz_type
        for tuple in self.executed_tests:
            if includes_modes and includes_throttles:
                # Structure: (mode, throttle, state)
                mode, throttle, state = tuple
                executed_test = (mode, throttle)
            elif includes_modes:
                # Structure: (mode, state)
                mode, state = tuple
                executed_test = (mode,) 
            elif includes_throttles:
                # Structure: (throttle, state)
                throttle, state = tuple
                executed_test = (throttle,) 
            self.tested_modes_by_state[state].add(executed_test)

    def init_shared_variables(self) -> None:
        self.mqtt_message_queue = queue.Queue()
        #main lock for each fuzz HIT (each fuzz task/scenario)
        self.main_lock = threading.Lock()
        self.critical_lock = threading.Lock()
        #throttle lock and variable
        self.throttle_lock = threading.Lock()
        self.throttle_value = None 

        #EVENTS 
        self.mission_ready = threading.Event()
        self.mission_time = threading.Event()
        self.mission_abort = threading.Event()
        self.mqtt_connected = threading.Event()
        self.force_shutdown = threading.Event()



    def __init_mqtt(self) -> None:
        self.mqtt_client = mqtt.Client("Fuzzing_System")
        self.mqtt_client.on_connect = self.mqtt_on_connect

        self.mqtt_client.connect("mqtt",1883)
        self.mqtt_client.loop_start()

    def __init_mission_file(self) -> None:
        f = open("missions/FUZZ_MISSION.json")
        self.mission_file = json.load(f)
        f.close()
        return 

    def mqtt_on_connect(self, client, userdata, flags, rc) -> None:
        if rc == 0:
            print("Connected to MQTT broker successfully!")
            #simple flag to control mqtt on message 
            self.message_sent = False
            self.mqtt_client.subscribe([("update_drone",0),("fuzz_mission/ready",1)])
            self.mqtt_client.message_callback_add("fuzz_mission/ready",self.mqtt_on_mission_ready)
            self.mqtt_client.message_callback_add("update_drone",self.mqtt_on_message)
            self.mqtt_connected.set()
        else:
            print("Failed to connect to MQTT broker with return code: {}".format(rc))
    
    def __init_docker_interface(self) -> None:
        self.docker_interface = Docker_Interface(self.mqtt_client,self.uav_id)
        self.docker_interface.run_onboard()

    def _abort_mission(self):
        #use docker handler for shutdown 
        #set mission abort event 
        self.mission_ready.clear()
        #shut down state machine and px4 
        self.docker_interface.abort_mission()
        return 

    def _cleanup(self):
        self.ros_interface.cleanup()
        time.sleep(1)
        self.docker_interface.run_onboard()
        return 
    
    def _adjust_wind(self):
        #self.docker_interface.adjust_wind()
        pass 

    def enqueue_mqtt_message(self):
        self.mqtt_message_queue.put(json.dumps(self.mission_file))

    def mqtt_on_mission_ready(self,client, userdata, msg):
        print('[fuzz_testor] received mission ready')
        if not self.mission_ready.is_set():
            self.mission_ready.set()
        #self.mqtt_client.publish("fuzz_mission/ack")
    

    def send_mission(self,message):
        #wait for state machine to be ready 
        print('[fuzz_testor] waiting for state machine ...')
        ##
        
        self.mission_ready.wait()
        # we need a small sleep before we publish the mission 
        time.sleep(2)
        self.mqtt_client.publish(MQTT_MISSION.format(self.uav_id),message)
        print('[fuzz_testor] recieved ready, publishing mission')
        self._start_mission_timer()

    def send_mission_thread(self):
        while not self.force_shutdown.is_set():
            try:
                message = self.mqtt_message_queue.get(timeout=1)  # Wait for a message
                self.send_mission(message)
                self.mqtt_message_queue.task_done()
            except queue.Empty:
                continue

    def load_msg(self,msg):
        msg = json.loads(msg.payload)
        status = msg["status"]
        if status == "success":
            return status
        curr_state = status["state_name"]
        return curr_state

    def _start_mission_timer(self):
        print('[fuzz_tester] starting timer')
        self.mission_start_time = time.time()
        self.mission_time.set()
    

    def run_test(self,fuzz_test:Fuzz_Test):
        '''
        Executes a fuzz test based on the provided Fuzz_Test instance.
        Can be a single test, or multiple depending on input.

        Args:
            fuzz_test (Fuzz_Test): An instance of Fuzz_Test containing all necessary parameters for the test.
        '''
        throttle_value = self.throttle_value if fuzz_test.throttle else None
        throttle_lock = self.throttle_lock if fuzz_test.throttle else None

        # Initialize ROS_Interface with throttle parameters if applicable
        self.ros_interface = ROS_Interface(
            throttle_value=throttle_value,
            throttle_lock=throttle_lock
        )

        # Set up geofence if applicable
        if fuzz_test.geofence:
            self.fuzz_test_combinations = fuzz_test.test_combinations
            print('combinations: ',fuzz_test.test_combinations)
            self.fuzz_type = fuzz_test.fuzz_type
            #turn geofence on 
            self.ros_interface.toggle_geofence(20.0)
            self.ros_interface.sub_geo_breach()
            
        else:
            #make sure geofence is off 
            self.ros_interface.toggle_geofence(0.0)
            self.fuzz_type = fuzz_test.fuzz_type
            self.fuzz_test_combinations = fuzz_test.test_combinations
            self.mode_throttle_combos = fuzz_test.remove_states_from_combinations()
        self.load_executed_tests()
        self.fuzz_test = fuzz_test 
        print('[fuzz_testor] preparing to send mission')
        self.enqueue_mqtt_message()
        return 

    def select_fuzz_test(self,current_state):
        if "geo" in self.fuzz_type:
            available_tests = self.fuzz_test_combinations - self.executed_tests
        else:
            if current_state not in self.fuzz_test.states:
                return None 
            tested = self.tested_modes_by_state.get(current_state,set())
            available_tests = self.mode_throttle_combos - tested
        if not available_tests:
            return None 
        return available_tests.pop()

    def execute_fuzz_test(self, fuzz_tuple):
        command_dict = self.fuzz_test.populate_command(fuzz_tuple)
        if "geo" in self.fuzz_type:
            self.ros_interface.reset_fuzz_done_flag()
            self.ros_interface.reset_geo_flag()
            self.ros_interface.send_geo_commands(command_dict)
        else:
            self.ros_interface.send_command(command_dict)
        return 
    '''
    Main function that relies on MQTT for fuzzing based on the drone state.
    '''
    def mqtt_on_message(self, client, userdata, msg):
        # if we aren't in the abort state or we are still waiting for mission ready signal 
        if self.mission_abort.is_set() or not self.mission_ready.is_set():
            return 

        #skip if we have already sent a message 
        curr_state = self.load_msg(msg)
        with self.critical_lock:
            if self.mission_abort.is_set():
                return 
            if curr_state == "success":
                self.mission_time.clear()
                ulg_file_path = self.docker_interface.get_latest_ulg_file()
                self.save_contender_file(ulg_file_path)
                self.write_to_file(ulg_file_path,self.recent_test,{"mission_complete":True})
                self.save_executed_tests()
                #force auto.land to reset in case of a manual switch
                self.ros_interface.cleanup()
                #record success and get ready for next mission 
                self.enqueue_mqtt_message()
                self.message_sent = False 
            else:
                #if we already sent a message don't send a HIT until next mission
                if self.message_sent:
                    return 
                #logic for selecting and executing fuzz tests 
                fuzz_to_execute = self.select_fuzz_test(curr_state)
                #if no fuzz to execute, means we finished all tests for that particular state, 
                #now wait for the next state to test.
                if not fuzz_to_execute:
                    if self.executed_tests == self.fuzz_test_combinations:
                        print('[fuzz_testor] finished with all tests!')
                        self.trigger_shutdown()
                    return 
                '''
                TODO:
                - experiment with timing
                - ex:
                    if curr_state == "Takeoff":
                        time.sleep(2.0)
                '''
                if curr_state == "Takeoff":
                    time.sleep(10.0)
                print(f'[fuzz_testor] executing {fuzz_to_execute}')
                self.execute_fuzz_test(fuzz_to_execute)
                #updating executed tests 
                if "state" in self.fuzz_type:
                    self.tested_modes_by_state.setdefault(curr_state, set()).add(fuzz_to_execute)
                    executed_tuple = fuzz_to_execute + (curr_state,)
                    self.executed_tests.add(executed_tuple)
                    self.recent_test = executed_tuple 
                elif "geo" in self.fuzz_type:
                    self.executed_tests.add(fuzz_to_execute)
                    self.recent_test = fuzz_to_execute
                self.message_sent = True 
        
    def check_time_threshold(self):
        while True:
            self.mission_time.wait()
            if self.force_shutdown.is_set():
                print('shutdown_handler] shutting down timing thread')
                return 
            mission_time = time.time() - self.mission_start_time
            if mission_time >= self.threshold:
                with self.critical_lock:
                    if self.mission_time.is_set():
                        self.mission_abort.set()
                        print('[fuzz_testor] time exceeded, restarting state machine')
                        ulg_file_path = self.docker_interface.get_latest_ulg_file()
                        self.save_contender_file(ulg_file_path)
                        self.write_to_file(ulg_file_path, self.recent_test, {"mission_complete": False})
                        self.save_executed_tests()
                        self._abort_mission()
                        self._cleanup()
                        self.mission_time.clear()
                        self.mission_abort.clear()
                        self.enqueue_mqtt_message()
                        self.message_sent = False 
                        
    '''
    Function to copy the log file from the px4 container into the fuzz service container.
    '''
    def save_contender_file(self, ulg_file_path):
        source_container = "dr-onboardautonomy-px4"
        source_id = os.popen(f"docker ps -qf name={source_container}").read().strip()
        source_path = "/home/user/Firmware/build/px4_sitl_default/logs/"+ulg_file_path
        destination_path = "/catkin_ws/src/fuzz_test_service/log_analyzer/contender_logs"
        os.system(f"docker cp {source_id}:{source_path} {destination_path}")


    def write_to_file(self, ulg_file_path, recent_test, json_message):
        '''
        Logs these things:
        - the log file path, a tuple with the most recent fuzz test executed, and a Boolean for the mission completion 
        - Run the log analyser to parse the ulog file for the fuzz mission and add max_deviation, max_altitude,duration, final_landing_state, freefall_occurred
        '''
        # Convert the tuple and JSON message to strings
        recent_test_str = str(recent_test)
        json_message_str = json.dumps(json_message)

        # Create a formatted message that includes all parts
        # This uses a simple comma-separated format. Adjust the separator if needed.
        formatted_message = f"{ulg_file_path}, {recent_test_str}, {json_message_str}, \n"

        # Write the formatted message to the file
        with open("Fuzz_Test_Logs.txt", 'a') as f:
            f.write(formatted_message)
    

    '''
    Functions below gracefully shutdown all running processes and threads.
    signal_handler - recieves interrupt and shutdowns rospy, docker, and timer
    shutdown_timer - sets events to exit timer thread
    '''
    def trigger_shutdown(self):
        os.kill(os.getpid(), signal.SIGINT)

    def signal_handler(self,sig, frame):
        self.handle_shutdown()

    def shutdown_timer(self):
        self.mission_time.set() 
        self.force_shutdown.set()
        return 

    def handle_shutdown(self):
        print('[shutdown_handler] forcing exit of all threads ....')
        self.shutdown_timer()
        self.ros_interface.shutdown()
        print('[shutdown_handler] successfully shutdown rospy')
        self.docker_interface.abort_mission()
        print('[shutdown_handler] successfully shutdown docker')
        sys.exit(0) 
   
fuzz_testor = Fuzz_Testor()
fuzz_test = Fuzz_Test(drone_id="Polkadot",
modes=['AUTO.RTL'],
geofence=[1],
throttle=[5]
)
fuzz_testor.run_test(fuzz_test)




