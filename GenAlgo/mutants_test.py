import numpy as np
import random
import modelTrain as mt
import pandas as pd

# Example feature dictionary
# Each key is a feature, and each value is a list of possible values or a range tuple
feature_dict = {
    'modes' : ['POSCTL','STABILIZED', 'OFFBOARD', 'ALTCTL', 'AUTO.LOITER', 'AUTO.RTL', 'AUTO.LAND'],
    'states' : ['Flying', 'Land', 'Disarm', 'Takeoff', 'Arm', 'Hover'],
    'GFACT' : ["Warning", "Hold mode", "Return mode", "Terminate", "Land mode"],
    'throttle' : [0, 225, -100, 260, 600, 100, 550, 445, 435, 450, 615, 570, 300, None]
}

def mutate(mutant_candidates_df):
    # Randomly sample 10 rows from mutant_candidates_df
    sample_indices = random.sample(range(len(mutant_candidates_df)), min(10, len(mutant_candidates_df)))
    sampled_df = mutant_candidates_df.iloc[sample_indices].copy()

    # Iterate over each sampled row
    for index, row in sampled_df.iterrows():
        print(row)

        # Randomly select a column from the filtered list   
        column_to_mutate = random.choice(mutant_candidates_df.columns)
        # print(column_to_mutate)
        
        if column_to_mutate == 'GF':
            # Mutate GF, GFPRED, and GFACT specifically
            sampled_df.at[index, 'GF'] = random.choice(['Yes', 'No'])
            if sampled_df.at[index, 'GF'] == 'No':
                sampled_df.at[index, 'GFPRED'] = None
                sampled_df.at[index, 'GFACT'] = None
            else:
                sampled_df.at[index, 'GFPRED'] = random.choice(['Yes', 'No'])
                sampled_df.at[index, 'GFACT'] = random.choice(feature_dict['GFACT'])
        # Mutate other columns based on their dictionary of eligible values
        # elif column_to_mutate == 'modes':
        elif  column_to_mutate == 'modes':
            sampled_df.at[index, 'modes'] = random.choice(feature_dict['modes'])
        elif column_to_mutate == 'states':
            choice = random.choice(feature_dict['states'])
            if choice != 'Flying':
                sampled_df.at[index, 'states'] = choice
                sampled_df.at[index, 'GFPRED'] = None
                sampled_df.at[index, 'GFACT'] = None
            else:
                sampled_df.at[index, 'states'] = choice
        elif column_to_mutate == 'throttle':
            sampled_df.at[index, 'throttle'] = random.choice(feature_dict['throttle'])
        elif column_to_mutate == 'GFPRED':
            # Mutate GFPRED based on the value of GF
            if sampled_df.at[index, 'GF'] == 'Yes':
                sampled_df.at[index, 'GFPRED'] = random.choice(['Yes', 'No'])
            else:
                sampled_df.at[index, 'GFPRED'] = None
        elif column_to_mutate == 'GFACT':
            # Mutate GFPRED based on the value of GF
            if sampled_df.at[index, 'GF'] == 'Yes':
                sampled_df.at[index, 'GFACT'] = random.choice(feature_dict['GFACT'])
            else:
                sampled_df.at[index, 'GFACT'] = None
    return sampled_df


model_instance = mt.Model()
df = model_instance.train_model('sample.csv')
# fitness_scores = [fitness_function(chromosome) for chromosome in population]


normal_data = df[df['anomaly'] == 1]
normal_data = normal_data.where(pd.notnull(normal_data), None)

# Calculate the median anomaly score
median_score = normal_data['anomaly_score'].median()

column_names = ['states', 'GF', 'GFPRED', 'GFACT', 'modes', 'throttle']

# Splitting dataframe into parent candidates and non-candidates based on median score
parent_candidates_df = normal_data[normal_data['anomaly_score'] < median_score]
mutant_candidates_df = normal_data[normal_data['anomaly_score'] >= median_score][column_names]

mutated_df = mutate(mutant_candidates_df)
print(mutated_df)