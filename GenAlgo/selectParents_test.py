import pandas as pd
import random

def select_parents(population_df, num_parents):
    # Calculate the 10th and 90th percentiles
    lower_bound = population_df['anomaly_scores'].quantile(0.1)
    upper_bound = population_df['anomaly_scores'].quantile(0.9)

    # Filter the dataframe to exclude the top and bottom 10%
    filtered_df = population_df[(population_df['anomaly_scores'] > lower_bound) & 
                                (population_df['anomaly_scores'] < upper_bound)]
    
    parents = []
    
    for _ in range(num_parents):
        # Randomly select individuals for the tournament
        tournament = filtered_df.sample(n=3)
        # Select the individual with the lowest anomaly score
        winner = tournament.loc[tournament['anomaly_scores'].idxmin()]
        parents.append(winner)
        
    return parents

# Example usage:
# Assuming your dataframe is called population_df and has a column 'anomaly_scores'
population_df = pd.DataFrame({
    'anomaly_scores': [0.2, 0.4, 0.6, 0.8, 1.0, 1.2, 1.4, 1.6, 1.8, 2.0, 
                       2.2, 2.4, 2.6, 2.8, 3.0, 3.2, 3.4, 3.6, 3.8, 4.0]
})

num_parents = 4
selected_parents = select_parents(population_df, num_parents)
print(selected_parents)
