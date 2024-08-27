from  log_analyzer import get_max_deviation
import json

def write_to_file(ulg_file_path, recent_test, json_message):
        '''
        Logs these things:
        - the log file path, a tuple with the most recent fuzz test executed, and a Boolean for the mission completion 
        - Run the log analyser to parse the ulog file for the fuzz mission and add max_deviation, max_altitude,duration, final_landing_state, freefall_occurred
        '''
        max_difference, max_altitude, duration, end_land_status, freefall_occurred = get_max_deviation.log_parser()

        # Convert the tuple and JSON message to strings
        recent_test_str = str(recent_test)
        json_message_str = json.dumps(json_message)
        json_message_str_cleaned = json_message_str.strip('"').replace("'", "\"")
        json_message_dict = json.loads(json_message_str_cleaned)
        mission_complete = json_message_dict['mission_complete']

        json_object = {
            "filename": ulg_file_path,
            "mission": recent_test_str,
            "mission_complete": mission_complete,
            "max_deviation": max_difference,
            "max_altitude": max_altitude,
            "duration": duration,
            "final_landing_state": end_land_status,
            "freefall_occurred": freefall_occurred
        }

        json_output = json.dumps(json_object, indent=4)

        # Write the formatted message to the file
        with open("Fuzz_Test_Logs.txt", 'a') as f:
            f.write(json_output)

write_to_file("2024-06-03/17_49_00.ulg", "('POSCTL', 550, 0)", "{'mission_complete': false}")
    