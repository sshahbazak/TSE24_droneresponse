import subprocess
import paho.mqtt.client as mqtt
import time
import os
import signal

class Docker_Interface:
    def __init__(self, mqtt_client=None,uav_id=None):
        # bash command to start the state machine
        self.uav_id = uav_id 
        self.state_machine_start = f"/bin/bash -c 'cd /catkin_ws/src/dr_onboard_autonomy/src/dr_onboard_autonomy && python state_machine.py _uav_name:={self.uav_id} _mqtt_host:=mqtt _local_mqtt_host:=mqtt_local'"
        self.dev_image_id = "dr-onboardautonomy-vs-code"
        self.px4_image_id = "dr-onboardautonomy-px4"
        self.airlease_id = "microservice-air-lease-air-lease"
        self.airlease = self.get_container_name_by_image_id(self.airlease_id)
        # initialize process to None
        self.process = None
        # get container name to use
        self.state_machine_container = self.get_container_name_by_image_id(self.dev_image_id)
        self.px4_container = self.get_container_name_by_image_id(self.px4_image_id)
        # MQTT client instance
        self.mqtt_client = mqtt_client

    def get_container_name_by_image_id(self, image_id):
        """Retrieve the container ID for a given image ID."""
        try:
            # This command lists all containers, filters those matching the image ID, and gets the name
            command = f"docker ps --filter ancestor={image_id} --format '{{{{.ID}}}}'"
            result = subprocess.run(command, shell=True, check=True, stdout=subprocess.PIPE, text=True)
            container_name = result.stdout.strip()
            if container_name:
                return container_name
            else:
                print("[docker_interface] No running containers found for the given image ID.")
                return None
        except subprocess.CalledProcessError as e:
            print(f"[docker_interface] Failed to execute docker command: {e}")
            return None

    def start_px4(self):
        """Start the PX4 container."""
        command = f"docker start {self.px4_container}"
        result = os.system(command)
        if result == 0:
            print(f"[docker_interface] Started PX4 container {self.px4_container}")
        else:
            print(f"[docker_interface] Failed to start PX4 container {self.px4_container}")

    def restart_airlease(self):
        """Start the PX4 container."""
        command = f"docker restart {self.airlease}"
        result = os.system(command)
        if result == 0:
            print(f"[docker_interface] Started airlease container {self.airlease}")
        else:
            print(f"[docker_interface] Failed to start airlease container {self.airlease}")

    def stop_px4(self):
        """Stop the PX4 container."""
        command = f"docker stop {self.px4_container}"
        result = os.system(command)
        if result == 0:
            print(f"[docker_interface] Stopped PX4 container {self.px4_container}")
        else:
            print(f"[docker_interface] Failed to stop PX4 container {self.px4_container}")


    def spawn_state_machine(self):
        command = ["docker", "exec", self.state_machine_container, "/bin/bash", "-c", self.state_machine_start]
        self.process = subprocess.Popen(command, preexec_fn=os.setpgrp,stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return self.process

    def abort_mission(self):
        self.mqtt_client.publish("all-drones/abort", "Shutdown",qos=1)
        unique_pattern = f"state_machine.py _uav_name:={self.uav_id}"
        kill_command = ["docker", "exec", self.state_machine_container, "pkill", "-f", unique_pattern]
        try:
            subprocess.run(kill_command, check=True)
            print('[docker_interface] State machine process killed successfully.')
        except subprocess.CalledProcessError as e:
            if e.returncode == 1:
                print('[docker_interface] No process found to kill.')
            else:
                print(f'[docker_interface] Error while killing the process: {e}')
        self.stop_px4()
        self.restart_airlease()
        self.start_px4()
    
    def get_latest_ulg_file(self):
        """Get the full path of the most recently written .ulg file in the latest log directory."""
        try:
            # Command to find the full path of the most recent .ulg file
            command = (
                f"docker exec {self.px4_container} /bin/bash -c "
                f"'cd /home/user/Firmware/build/px4_sitl_default/logs/ && "
                f"latest_dir=$(ls -td -- */ | head -n 1) && "
                f"cd $latest_dir && "
                f"latest_file=$(ls -t *.ulg | head -n 1) && "
                f"echo $latest_dir$latest_file'"
            )
            # Run the command and capture the output
            result = subprocess.run(command, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            latest_ulg_file_path = result.stdout.strip()
            return latest_ulg_file_path
        except subprocess.CalledProcessError as e:
            print(f"[docker_interface] Failed to get the latest .ulg file path: {e.stderr}")
            return None

    def run_onboard(self):
        self.process = self.spawn_state_machine()
        process_pid = os.getpgid(self.process.pid)
        print('[docker_interface] state machine process started with PID:', process_pid)