"""
This script implements a Genetic Algorithm for optimizing a model using data from fuzz testing.

It starts with an initial processed dataset (i.e., the first generation), where each row in this dataset is treated as a chromosome. 
The first generation begins by training an isolation forest ML model to predict anomalies, which are then scored based on their anomaly levels. 
Afterward, the data that is less anomalous is segregated into parents and mutant candidates based on their anomaly scores. 
Ten random records (modifiable) are selected from the parent candidates to undergo crossovers, creating a new set of inputs/probes that hopefully lead to better anomalies. 
Additionally, ten random records (modifiable) are selected from the mutant candidates to undergo mutation, where some features are modified to obtain new probes.

These probes are then merged and provided to the run_probe function, which utilized FuzzTestor to run them one by one and obtain the results. 
The results are then stored back in the dataset to form the next generation, and the process repeats, leading to progressively better anomalies over time.

Modules Imported:
- Fuzz: Custom module for fuzz testing.
- modelTrain: Custom module for training the model.

Parameters:
- NUM_GENERATIONS: Number of generations the genetic algorithm will run.
- DATA_FILE: File path for the data CSV file.
- NUM_PARENTS: Number of parents selected for crossover in each generation.
- NUM_MUTANTS: Number of mutants generated in each generation.

Feature Dictionary:
- FEATURE_DICT: Dictionary containing features and their possible values or range tuples.
- GEOFENCE_ACTION: Dictionary mapping geofence actions to numeric codes.
- THROTTLE_DICT: Dictionary mapping throttle values to specific codes.
- STATES_DICT: Dictionary mapping states to corresponding functions or values.
- COLUMN_NAMES: List of column names for the dataset.

Classes:
- GeneticAlgorithm: Implements the genetic algorithm with methods for initialization, fitness calculation, selection, crossover, mutation, packaging results, running probes, and the main algorithm loop.

Execution:
- The GeneticAlgorithm class is instantiated and the algorithm is run using the run_algorithm method.
"""


import numpy as np
import pandas as pd
import random
from sklearn.datasets import make_classification
import os
import json
from Fuzz import FuzzTestor as ft
import modelTrain as mt


# Parameters
NUM_GENERATIONS = 10
DATA_FILE = 'data.csv'
NUM_PARENTS = 10
NUM_MUTANTS = 10

# Each key is a feature, and each value is a list of possible values or a range tuple
FEATURE_DICT = {
    'modes' : ['POSCTL','STABILIZED', 'OFFBOARD', 'ALTCTL', 'AUTO.LOITER', 'AUTO.RTL', 'AUTO.LAND'],
    'states' : ['Flying', 'Land', 'Disarm', 'Takeoff', 'Arm', 'Hover'],
    'GFACT' : [None, "Warning", "Hold mode", "Return mode", "Terminate", "Land mode"],
    'throttle' : [0, 225, -100, 260, 600, 100, 550, 445, 435, 450, 615, 570, 300, None]
}
GEOFENCE_ACTION = {"None" : 0, "Warning": 1, "Hold mode" : 2, "Return mode" : 3, "Terminate" : 4, "Land mode" : 5}
THROTTLE_DICT = {0: 1, 260: 2, 550: 3, 600: 4, 615: 5}
STATES_DICT = {'Flying': lambda: random.choice(['BriarWaypoint','BriarWaypoint2','BriarWaypoint3']), 'Land': 'Land', 'Disarm': 'Disarm', 'Takeoff': 'Takeoff', 'Arm': 'Takeoff', 'Hover': 'BriarHover'}
COLUMN_NAMES = ['states', 'GF', 'GFPRED', 'GFACT', 'modes', 'throttle']

class GeneticAlgorithm:
    # Initializes the class, loads data, and sets up instances of Fuzz_Testor and Model.
    def __init__(self) -> None:
        self.population = pd.read_csv(DATA_FILE)
        self.fuzz_testor = ft.Fuzz_Testor()
        self.model_instance = mt.Model()

    # Fitness function: Calculates the fitness of the current population.
    def fitness_function(self):
        return self.model_instance.train_model(DATA_FILE)
    
    # Selection function: Selects parents for crossover using tournament selection.
    def select_parents(self, parent_candidates_df):
        print('[Genetic Algorithm] Selecting Parents for crossovers')

        parents_df = pd.DataFrame()
        
        for _ in range(NUM_PARENTS):
            # Randomly select individuals for the tournament
            tournament = parent_candidates_df.sample(n=3)
            # Select the individual with the lowest anomaly score
            winner = tournament.loc[tournament['anomaly_score'].idxmin()]
            parents_df =  pd.concat([parents_df, winner.to_frame().transpose()], ignore_index=True)
            
        return parents_df[['states', 'GF', 'GFPRED', 'GFACT', 'modes', 'throttle']]
    
    # Crossover function: Performs single-point crossover on selected parents.
    def crossover(self, parents):
        print('[Genetic Algorithm] Crossing Over Parents')
        crossover = []
        for i in range(0, len(parents)-1, 2):
            parent1, parent2 = parents.iloc[i], parents.iloc[i + 1]
            parent1 = np.array(parent1)
            parent2 = np.array(parent2)
            
            # Define the index range for 'GF', 'GFPRED', and 'GFACT' columns
            gf_indices = [COLUMN_NAMES.index(col) for col in ['GF', 'GFPRED', 'GFACT']]
            
            # Define the crossover point
            crossover_point = random.randint(1, len(parent1) - 2)
            
            # Perform crossover
            child1 = np.concatenate((parent1[:crossover_point], parent2[crossover_point:]))
            child2 = np.concatenate((parent2[:crossover_point], parent1[crossover_point:]))
            
            # Ensure 'GF', 'GFPRED', and 'GFACT' are treated as a single column during swapping
            child1[gf_indices] = parent1[gf_indices]
            child2[gf_indices] = parent2[gf_indices]

            crossover.extend([child1, child2])

        # Convert list of children to DataFrame with headers
        crossover_df = pd.DataFrame(crossover, columns=COLUMN_NAMES)
        
        return crossover_df
    
    # Mutate: Introduces mutations into the population.
    def mutate(self, mutant_candidates_df):
        # Randomly sample 10 rows from mutant_candidates_df
        sample_indices = random.sample(range(len(mutant_candidates_df)), min(10, len(mutant_candidates_df)))
        sampled_df = mutant_candidates_df.iloc[sample_indices].copy()

        # Iterate over each sampled row
        for index, row in sampled_df.iterrows():

            # Randomly select a column from the filtered list   
            column_to_mutate = random.choice(mutant_candidates_df.columns)
            
            if column_to_mutate == 'GF':
                # Mutate GF, GFPRED, and GFACT specifically
                sampled_df.at[index, 'GF'] = random.choice(['Yes', 'No'])
                if sampled_df.at[index, 'GF'] == 'No':
                    sampled_df.at[index, 'GFPRED'] = None
                    sampled_df.at[index, 'GFACT'] = None
                else:
                    # sampled_df.at[index, 'GFPRED'] = random.choice(['Yes', 'No'])
                    sampled_df.at[index, 'GFPRED'] = 'Yes'
                    sampled_df.at[index, 'GFACT'] = random.choice(FEATURE_DICT['GFACT'])
            # Mutate other columns based on their dictionary of eligible values
            elif  column_to_mutate == 'modes':
                sampled_df.at[index, 'modes'] = random.choice(FEATURE_DICT['modes'])
            elif column_to_mutate == 'states':
                choice = random.choice(FEATURE_DICT['states'])
                if choice != 'Flying':
                    sampled_df.at[index, 'states'] = choice
                    sampled_df.at[index, 'GFPRED'] = None
                    sampled_df.at[index, 'GFACT'] = None
                else:
                    sampled_df.at[index, 'states'] = choice
            elif column_to_mutate == 'throttle':
                sampled_df.at[index, 'throttle'] = random.choice(FEATURE_DICT['throttle'])
            # elif column_to_mutate == 'GFPRED':
            #     # Mutate GFPRED based on the value of GF
            #     if sampled_df.at[index, 'GF'] == 'Yes':
            #         # sampled_df.at[index, 'GFPRED'] = random.choice(['Yes', 'No'])
            #         sampled_df.at[index, 'GFPRED'] = 'Yes'
            #     else:
            #         sampled_df.at[index, 'GFPRED'] = None
            elif column_to_mutate == 'GFACT':
                # Mutate GFPRED based on the value of GF
                if sampled_df.at[index, 'GF'] == 'Yes':
                    sampled_df.at[index, 'GFACT'] = random.choice(FEATURE_DICT['GFACT'])
                else:
                    sampled_df.at[index, 'GFACT'] = None
        return sampled_df
    
    # Packager: Packages the results into a dictionary for further processing.
    def packager(self, row, values):
        output_dict = json.loads(values)
        '''
        Right now the wind, GFRED and kill_switch are always None. These can be added in future enhancments  
        '''
        initial_mode = 'AUTO.LAND' if row['states'] in ('Arm', 'Disarm', 'Land') else 'OFFBOARD'
        wind = None
        kill_switch = 'No'
        gfpred = 'Yes' if row['GF'] == 'Yes' else None
        throttle = row['throttle'] if row['throttle'] in [0, 260, 550, 600, 615] else None
        duration_str = output_dict['duration']
        duration_in_seconds = pd.to_timedelta(duration_str).total_seconds()

        merged_data = {
            'initial_mode': initial_mode,
            'states': row['states'],
            'Wind': wind,
            'GF': row['GF'],
            'GFPRED': gfpred,
            'GFACT': row['GFACT'],
            'kill_switch': kill_switch,
            'modes': row['modes'],
            'throttle': throttle,
            'max_deviation': output_dict['max_deviation'],
            'max_altitude': output_dict['max_altitude'],
            'duration': duration_in_seconds,
            'final_landing_state': output_dict['final_landing_state'],
            'freefall_occurred': output_dict['freefall_occurred'],
            'mission_complete': output_dict['mission_complete']
        }
        return merged_data
    
    # run_probe: Runs probes on the dataset using fuzz testing.
    def run_probe(self, df):
        results = []
        count = 0
        # Initialize an empty DataFrame with columns
        columns = ['initial_mode', 'states', 'Wind', 'GF', 'GFPRED', 'GFACT', 'kill_switch',
                'modes', 'throttle', 'max_deviation', 'max_altitude', 'duration',
                'final_landing_state', 'freefall_occurred', 'mission_complete']
        probe_data = []
        for _, row in df.iterrows():
            print('[Genetic Algorithm] Probe ' +str(count))
            fuzz_test_args = {'drone_id': 'Polkadot'}

            # Dynamically add arguments if they are not None
            fuzz_test_args['modes'] = [row['modes']]
            if not pd.isna(row['states']) and not pd.isna(row['GFACT']):
                if random.choice([True, False]):
                    row['states'] = 'Flying'
                else:
                    row['GFACT'] = None
                    row['GFPRED'] = None
                    row['GF'] = 'No'
            if not pd.isna(row['states']):
                if row['states'] == 'Flying':
                    fuzz_test_args['states'] = [STATES_DICT['Flying']()]
                else:
                    fuzz_test_args['states'] = [STATES_DICT[row['states']]]
            if not pd.isna(row['GFACT']):
                fuzz_test_args['geofence'] = [GEOFENCE_ACTION.get(row['GFACT'])]

            if not pd.isna(row['throttle']):
                if int(row['throttle']) not in [0, 260, 550, 600, 615]:
                    fuzz_test_args['throttle'] = None
                else:
                    fuzz_test_args['throttle'] = [THROTTLE_DICT.get(int(row['throttle']))]

            # Call the Fuzz_Test function with the unpacked dictionary
            fuzz_test = ft.Fuzz_Test(**fuzz_test_args)
            self.fuzz_testor.run_test(fuzz_test)
            self.fuzz_testor.test_complete.wait()

            var = self.packager(row, self.fuzz_testor.output)
            probe_data.append(var)
            os.system("rm executed_tests.pkl")
            os.system("rm Fuzz_Test_Logs.txt")
            self.fuzz_testor.test_complete.clear()
            #Enabled for testing if you need less probes to run
            # if count >= 2:
            #     break
            count += 1
        probe_df = pd.DataFrame(probe_data, columns=columns)
        print('[Genetic Algorithms] Probe Results')
        print(probe_df)
        return probe_df
    
    # run_algorithm: Main loop for running the genetic algorithm.
    def run_algorithm(self):
        for generation in range(NUM_GENERATIONS):
            print('[Genetic Algorithm] Sarting Generation ' +str(generation))

            df = self.fitness_function()

            # Eliteness
            # elite_df = df[df['anomaly'] == -1]


            normal_data = df[df['anomaly'] == 1]

            # Calculate the median anomaly score
            median_score = normal_data['anomaly_score'].median()

            # Splitting dataframe into parent candidates and non-candidates based on median score
            parent_candidates_df = normal_data[normal_data['anomaly_score'] < median_score]
            mutant_candidates_df = normal_data[normal_data['anomaly_score'] >= median_score][COLUMN_NAMES]

            # Crossover
            parents = self.select_parents(parent_candidates_df)  # Ensure even number of parents

            print('[Genetic Algorithm] Crossing Over Parents')
            crossover_df = self.crossover(parents)

            # Mutation
            print('[Genetic Algorithm] Mutating chromosomes')
            mutated_df = self.mutate(mutant_candidates_df)

            # Run sim probes on mutated_df and crossover_df
            print('[Genetic Algorithm] Running probes')
            merged_df = pd.concat([crossover_df, mutated_df])
            probe_df = self.run_probe(merged_df)

            print('[Genetic Algorithm] Saving probe results')
            self.population = pd.concat([self.population, probe_df], ignore_index=True)
            self.population.to_csv('data.csv', index=False, na_rep='None')
    
    # Cleans up resources upon deletion.
    def __del__(self) -> None:
        self.fuzz_testor.trigger_shutdown()


ga = GeneticAlgorithm()
ga.run_algorithm()
del ga