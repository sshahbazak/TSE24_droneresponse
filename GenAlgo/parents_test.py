import pandas as pd
import numpy as np
import random
import modelTrain as mt

# Selection function: Tournament selection
def select_parents(parent_candidates_df, num_parents):
    print('[Genetic Algorithm] Selecting Parents for crossovers')
    
    parents_df = pd.DataFrame()
    
    for _ in range(num_parents):
        # Randomly select individuals for the tournament
        tournament = parent_candidates_df.sample(n=3)
        # Select the individual with the lowest anomaly score
        winner = tournament.loc[tournament['anomaly_score'].idxmin()]
        parents_df =  pd.concat([parents_df, winner.to_frame().transpose()], ignore_index=True)
        
    return parents_df[['states', 'GF', 'GFPRED', 'GFACT', 'modes', 'throttle']]


# Crossover function: Single-point crossover
def crossover(parent1, parent2, column_names):
    parent1 = np.array(parent1)
    parent2 = np.array(parent2)
    
    # Define the index range for 'GF', 'GFPRED', and 'GFACT' columns
    gf_indices = [column_names.index(col) for col in ['GF', 'GFPRED', 'GFACT']]
    
    # Define the crossover point
    crossover_point = random.randint(1, len(parent1) - 2)
    
    # Perform crossover
    child1 = np.concatenate((parent1[:crossover_point], parent2[crossover_point:]))
    child2 = np.concatenate((parent2[:crossover_point], parent1[crossover_point:]))
    
    # Ensure 'GF', 'GFPRED', and 'GFACT' are treated as a single column during swapping
    child1[gf_indices] = parent1[gf_indices]
    child2[gf_indices] = parent2[gf_indices]
    
    return child1, child2

model_instance = mt.Model()
df = model_instance.train_model('sample.csv')
# fitness_scores = [fitness_function(chromosome) for chromosome in population]

# Eliteness
elite_df = df[df['anomaly'] == -1]


normal_data = df[df['anomaly'] == 1]
normal_data = normal_data.where(pd.notnull(normal_data), None)

# Calculate the median anomaly score
median_score = normal_data['anomaly_score'].median()

column_names = ['states', 'GF', 'GFPRED', 'GFACT', 'modes', 'throttle']

# Splitting dataframe into parent candidates and non-candidates based on median score
parent_candidates_df = normal_data[normal_data['anomaly_score'] < median_score]
mutant_candidates_df = normal_data[normal_data['anomaly_score'] >= median_score]

# Crossover
parents = select_parents(parent_candidates_df, 30)  # Ensure even number of parents

print('[Genetic Algorithm] Crossing Over Parents')
  # Adjust column names as needed
new_population = []
for i in range(0, len(parents)-1, 2):
    parent1, parent2 = parents.iloc[i], parents.iloc[i + 1]
    child1, child2 = crossover(parent1, parent2, column_names)
    new_population.extend([child1, child2])

    print('Parent 1 - ', parent1)
    print('Parent 2 - ', parent2)
    print('Child 1 - ', child1)
    print('Child 2 - ', child2)

# Convert list of children to DataFrame with headers
new_population_df = pd.DataFrame(new_population, columns=column_names)

print(new_population_df)