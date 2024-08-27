import pandas as pd
from itertools import combinations
import Clustering as clt
import random
import FaultTreeHelper
import json
from Fuzz import FuzzTestor as ft
import os
import ast  
import itertools

MODES = ['ALTCTL', 'POSCTL', 'OFFBOARD', 'STABILIZED', 'AUTO.LOITER', 'AUTO.RTL', 'AUTO.LAND']
MODES_MAP = {'LOITER': 'AUTO.LOITER', 'RTL':'AUTO.RTL', 'LAND': 'AUTO.LAND'}
STATES = ['Takeoff','BriarWaypoint','BriarWaypoint2','BriarWaypoint3','BriarHover','Land','Disarm']
# THROTTLE_DICT = {0: 1, 260: 2, 550: 3, 600: 4, 615: 5}
GEOFENCE_ACTION = {"None" : 0, "Warning": 1, "Hold" : 2, "Return" : 3, "Terminate" : 4, "Land" : 5}
# Mapping for states suffixes
STATES_MAPPING = {
    "Hover": "BriarHover",
    "Flying": ["BriarWaypoint", "BriarWaypoint2", "BriarWaypoint3"]
}

# MODES = ['ALTCTL']
# STATES = ['Takeoff']
# THROTTLE_DICT = {0: 1}
# GEOFENCE_ACTION = {"None" : 0}
ANOMALY_FILE = 'probes2.json'
LOGIC_FILE = 'logic.txt'

class ClusteringFT():

    def __init__(self) -> None:
        
        self.fuzz_test_args = {}
        self.cases = []
        self.truthTable = pd.DataFrame()
        self.top_features = []
        self.keys = []

    def fault_tree_helpers(self, index):
        exp = FaultTreeHelper.minLogicFunc(self.truthTable)
        print('[Debug] Logic Function - ', exp)
        logic_expr = FaultTreeHelper.convert_logic_to_boolean(exp)
        logic_expr = logic_expr.strip()
        print('[ClusteringFT] Minimal Logic Function - ', logic_expr)
        with open(LOGIC_FILE, 'a') as f:
            f.write('Combination ' + str(index)+'Logic - ' +logic_expr + '\n')
        if logic_expr == '(0)':
            return
        print('[ClusteringFT] Constructing Fault Trees...')
        # logic_expr = '(geofence and throttle) or modes'
        FaultTreeHelper.drawFaultTree(logic_expr, index)
        mincut = FaultTreeHelper.mincutSets(logic_expr)
        print('[ClusteringFT] Minimum Cut Sets - ', mincut)
        return
        
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

        
        output_dict['combination'] = ones_columns
        output_dict['combination_index'] = index
        output_dict['anomaly'] = anomaly

        for i, item in enumerate(ones_columns):
            if "throttle" in item:
                number_str = item.split('_')[1]
                throttle_value = int(number_str)  # Convert the extracted string to an integer
                if throttle_value in [-100, 0, 225, 260]:
                    throttle_value = 'Low'
                elif throttle_value in [100, 435, 550]:
                    throttle_value = 'Mid'
                elif throttle_value in [300, 445, 600, 570, 450, 615]:
                    throttle_value = 'High'
                ones_columns[i] = f"throttle_{throttle_value}" 
        print('[ClusteringFT] Found an anomaly! Adding it to anomaly file..')
        print('[ClusteringFT] Anomaly Details - ', fuzz_testor_output)
        with open(ANOMALY_FILE, 'a') as f:
                json.dump(output_dict, f, indent=4)
                f.write('\n')
        if anomaly:
            return 1
        
        return 0

    def validate_combinations(self):
        for index, row in self.truthTable.iterrows():
            # Get the columns that have ones
            ones_columns = [col for col in self.truthTable.columns if row[col] == 1]
            # Get the prefixes of these columns
            prefixes = [col.split('_')[0] for col in ones_columns]

            # Check if any prefix appears more than once
            if len(set(prefixes)) < len(prefixes):
                self.truthTable.at[index, 'result'] = 0
                continue

            #  # Check if both 'GFACT' and 'states' are set to 1
            if 'GFACT' in prefixes and 'states' in prefixes:
                self.truthTable.at[index, 'result'] = 0
                continue

            # Check if a single state column is 1 and all others are 0
            if len(ones_columns) == 1 and ones_columns[0].startswith('states'):
                self.truthTable.at[index, 'result'] = 0
                continue

            # Check valid combinations
            valid_combinations = [
                ['GFACT'],
                ['GFACT', 'modes'],
                ['GFACT', 'modes', 'throttle'],
                ['states', 'modes'],
                ['states', 'throttle'],
                ['states', 'modes', 'throttle']
            ]

            valid = False
            for combination in valid_combinations:
                if all(any(ones.startswith(prefix) for ones in ones_columns) for prefix in combination):
                    valid = True
                    break

            if not valid:
                self.truthTable.at[index, 'result'] = 0
        return
    
    def create_fuzz_args(self, valid_combinations):
        special_dicts = []
        print(valid_combinations)
        fuzz_test_args = {'drone_id': 'Polkadot'}
        for combination in valid_combinations:
            prefix, suffix = combination.split('_', 1)

            if prefix == 'GFACT':
                prefix = 'geofence'
                suffix = GEOFENCE_ACTION.get(suffix, suffix)
            elif prefix == 'states':
                if suffix == 'Hover':
                    suffix = STATES_MAPPING['Hover']
                elif suffix == 'Flying':
                    suffix = random.choice(STATES_MAPPING['Flying'])

            elif prefix == 'modes' and suffix in ['LOITER', 'RTL', 'LAND']:
                suffix = MODES_MAP[suffix]

            elif prefix == 'throttle':
                value = int(float(suffix))
                if value in [-100, 0, 225, 260]:
                    suffix = random.choice([1, 2])
                elif value in [100, 435, 550]:
                    suffix = 3
                elif value in [300, 445, 600]:
                    suffix = 4
                elif value in [570, 450, 615]:
                    suffix = 5

            if prefix not in fuzz_test_args:
                fuzz_test_args[prefix] = []
            if suffix not in fuzz_test_args[prefix]:
                fuzz_test_args[prefix].append(suffix)
        
        return fuzz_test_args
    

    def run_probes(self, index, ones_columns, fuzz_args):
        print('[ClusteringFT] Running Probe - ', fuzz_args)
        self.fuzz_testor = ft.Fuzz_Testor()
        fuzz_test = ft.Fuzz_Test(**fuzz_args)
        self.fuzz_testor.run_test(fuzz_test)
        self.fuzz_testor.test_complete.wait()
        os.system("rm executed_tests.pkl")
        os.system("rm Fuzz_Test_Logs.txt") 
        self.fuzz_testor.test_complete.clear()
        self.fuzz_testor.trigger_shutdown()
        var = self.decision_tree(index, ones_columns, self.fuzz_testor.output)
        return var

    def run_pipeline(self):
        self.top_features = clt.Clustering()
        print('[ClusteringFT] Top Combinations from Clustering - ', self.top_features)
        count = 0

        for comb, features in enumerate(self.top_features):
            count += 1
            if count >= 2:
                break
            print('[Debug] Running Combination ' +str(comb))
            print('[Debug] Combination Details - ', features)

            combinations = list(itertools.product([0, 1], repeat=len(features)))

            # Create a dataframe from these combinations
            self.truthTable = pd.DataFrame(combinations, columns=features)

            # Add a 'result' column with NaN values
            self.truthTable['result'] = None

            self.validate_combinations()

            for index, row in self.truthTable.iterrows():
                if row['result'] is None:
                    print('[Debug] Running Truth table row - ')
                    print(row)

                    ones_columns = [col for col in self.truthTable.columns if row[col] == 1 and col != 'result']

                    fuzz_args = self.create_fuzz_args(ones_columns)

                    # Run probes and get the result
                    result_value = self.run_probes(comb, ones_columns, fuzz_args)
                    # result_value = random.choice([0, 1])

                    # Set the result value for the current row
                    self.truthTable.at[index, 'result'] = result_value


            self.fault_tree_helpers(comb)
            print('[ClusteringFT] Final Truth Table for the combination - ')
            print(self.truthTable)
            self.truthTable.to_csv('TruthTable_' +str(comb)+'.csv', index=False)



        return


cl = ClusteringFT()
cl.run_pipeline()
