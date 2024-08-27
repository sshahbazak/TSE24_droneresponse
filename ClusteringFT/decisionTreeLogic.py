'''
Assume here that the input variable fuzz_testor_output is in this format - 

{
    "filename": "2024-07-12/16_35_12.ulg",
    "mission": "(0, 5)",
    "max_deviation": 33.531126164,
    "max_altitude": 4.9189122e-05,
    "duration": "0:01:23",
    "final_landing_state": true,
    "freefall_occurred": false,
    "mission_complete": false
}

'''
import json
import pandas as pd
import ast


def decision_tree(self, index, ones_columns, fuzz_testor_output):
        output_dict = json.loads(fuzz_testor_output)
        mission_list = list(ast.literal_eval(output_dict['mission']))
        print('[Debug] output_dict - ', output_dict)
        print('[Debug] mission_list - ', mission_list)
        anomaly = False
        if 'AUTO.LAND' in mission_list and 'Takeoff' not in mission_list:
            if output_dict['final_landing_state'] != True:
                anomaly = True
        elif ('ALTCTL' in mission_list or 'POSCTL' in mission_list or 'AUTO.LOITER' in mission_list) and 'Takeoff' not in mission_list:
            if output_dict['mission_complete'] == True or  output_dict['final_landing_state'] == True or int(output_dict['max_deviation']) < 2:
                anomaly = True
        elif 'AUTO.RTL' in mission_list and 'Takeoff' not in mission_list:
            if output_dict['final_landing_state'] != True:
                anomaly = True
        elif any('GFACT' in item for item in ones_columns):
            for i in ones_columns:
                if 'GFACT' in i:
                    action = i.split('_')[1]
                    if action == 'Land':
                        if output_dict['final_landing_state'] == False or int(output_dict['max_deviation']) < 10:
                            anomaly = True
                    elif action != 'None':
                        if int(output_dict['max_deviation']) < 10 or output_dict['mission_complete'] == True:
                            anomaly=True
        elif pd.to_timedelta(output_dict['duration']).total_seconds() < 40:
            anomaly = True
        elif output_dict['mission_complete'] == False and (int(output_dict['max_deviation']) > 2 or (int(output_dict['max_altitude']) < 10 or int(output_dict['max_altitude']) > 15)):
            anomaly = True
        
        if anomaly:
            return 1
        return 0