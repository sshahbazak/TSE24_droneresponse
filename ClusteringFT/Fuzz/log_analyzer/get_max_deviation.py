import pandas as pd
import numpy as np
import glob
import os
import csv

"""
Directories should be set up as follows:
>path_to_analysis_directory/
	-this_script
	>blueprint/
		-blueprint.ulg
	>contender_logs/
		-contender1.ulg
		-contender2.ulg
		-...

If this file is not already in the analysis directory:
set this path to your analysis directory -- 
the one that contains the "blueprint" and "contender_logs" folders
for example: 
"/home/droneresponse/Desktop/log_storage/" (you need the final "/" at the end)
"""
# def log_parser():
	# path = "/home/droneresponse/Desktop/log_storage/"
path = "/catkin_ws/src/fuzz_test_service/Fuzz/log_analyzer/"

def get_names():
	blueprint_name = glob.glob(path + "blueprint" + "/*.ulg")[0]
	if len(glob.glob(path + "blueprint" + "/*.csv")) == 0:
		os.system("ulog2csv " + blueprint_name)
	blueprint_name = (blueprint_name.rsplit("/", 1)[1]).split(".")[0] + "_vehicle_local_position_0.csv"
	contender_list = glob.glob(path + "contender_logs" + "/*.ulg")
	print(contender_list)
	return blueprint_name, contender_list[0]

def get_closest_timestamp(value, arr, timestamps):
	timestampIndex = np.abs(arr - value).argmin()
	difference = np.abs(value - arr[timestampIndex])
	return difference, timestamps[timestampIndex]

def log_parser():
	#set threshold for what to consider a deviation from the intended flight path
	try:
		os.system("rm -r "+path+"ulog2csv_workspace")
	except:
		pass
	threshold = 1

	blueprint_name, contender = get_names()

	blueprint_data = pd.read_csv(path + "blueprint/" + blueprint_name, usecols=['x', 'y', 'z'])

	x_list = blueprint_data['x'].tolist()
	y_list = blueprint_data['y'].tolist()
	z_list = blueprint_data['z'].tolist()

	rows = []

	# headings = ["log_name", "max_deviation", "max_altitude", "duration", "final_landing_state", "freefall_occurred"]
	os.mkdir(path+"ulog2csv_workspace")
	os.system("cp " + contender + " " + path + "ulog2csv_workspace")
	contender_name_base = (contender.rsplit("/", 1)[1])
	os.system("ulog2csv " + path + "ulog2csv_workspace/" + contender_name_base)
	os.system("ulog_info " + path + "ulog2csv_workspace/" + contender_name_base + " | grep duration > "+path+"ulog2csv_workspace/duration.txt")
	contender_name = contender_name_base.split(".")[0] + "_vehicle_local_position_0.csv"
	contender_data = pd.read_csv(path + "ulog2csv_workspace/" + contender_name, usecols=['x', 'y', 'z', 'timestamp'])

	contender_x = np.array(contender_data['x'].tolist())
	contender_y = np.array(contender_data['y'].tolist())
	contender_z = np.array(contender_data['z'].tolist())
	contender_timestamps = np.array(contender_data['timestamp'].tolist())

	max_difference = 0
	max_timestamp = 0
	max_axis = ""
	violating_axes = []
	for x in x_list:
		difference, timestamp = get_closest_timestamp(x, contender_x, contender_timestamps)
		if difference > max_difference:
			max_difference, max_timestamp = difference, timestamp
			max_axis = "x"
		if difference > threshold and "x" not in violating_axes:
			violating_axes.append("x")
			# break
	for y in y_list:
		difference, timestamp = get_closest_timestamp(y, contender_y, contender_timestamps)
		if difference > max_difference:
			max_difference, max_timestamp = difference, timestamp
			max_axis = "y"
		if difference > threshold and "y" not in violating_axes:
			violating_axes.append("y")
			# break
	for z in z_list:
		difference, timestamp = get_closest_timestamp(z, contender_z, contender_timestamps)
		if difference > max_difference:
			max_difference, max_timestamp = difference, timestamp
			max_axis = "z"
		if difference > threshold and "z" not in violating_axes:
			violating_axes.append("z")
			# break

	contender_name = contender_name_base.split(".")[0] + "_vehicle_land_detected_0.csv"
	contender_data = pd.read_csv(path + "ulog2csv_workspace/" + contender_name, usecols=['freefall', 'landed'])
	contender_freefall = np.array(contender_data['freefall'].tolist())
	contender_landed = np.array(contender_data['landed'].tolist())

	freefall_occurred = 1 in contender_freefall
	end_land_status = bool(contender_landed[-1])

	max_altitude = abs(min(contender_z))

	duration = ""
	with open(path + "ulog2csv_workspace/" + "duration.txt") as d:
		for line in d:
			duration = line.rsplit(" ", 1)[1].rstrip("\n")
			break

	row = []
	# row.append(contender_name_base)
	row.append(max_difference)
	row.append(max_altitude)
	row.append(duration)
	row.append(end_land_status)
	row.append(freefall_occurred)

	

	os.system("cd " + path)
	os.system("rm -r "+path+"ulog2csv_workspace")
	os.system("rm -r "+path+"contender_logs/*")
	return row

# print(log_parser())