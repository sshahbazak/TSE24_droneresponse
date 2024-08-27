# Final Code


import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import LabelEncoder
from scipy.stats import chi2_contingency
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from collections import defaultdict

# Function to sort and arrange the dictionary
def sort_and_arrange(input_dict):
    sorted_dict = {}
    for key, values in input_dict.items():
        type_dict = defaultdict(list)
        for k, v in values.items():
            type_prefix = k.split('_')[0]
            type_dict[type_prefix].append((k, v))
        
        sorted_values = []
        for type_prefix, items in type_dict.items():
            sorted_items = sorted(items, key=lambda x: x[1], reverse=True)
            sorted_values.extend(sorted_items)
        
        sorted_dict[key] = dict(sorted_values)
    
    return sorted_dict

# Function to generate the required combinations
def generate_combinations(sorted_dict):
    combinations = []
    cycle_types = ['throttle', 'modes', 'states']
    cycle_index = 0
    generated_combinations = set()  # Set to store generated combinations
    
    for key, values in sorted_dict.items():
        # Extract top items for each type
        top_gfact = [k for k in values.keys() if k.startswith('GFACT')][:4]
        top_states = [k for k in values.keys() if k.startswith('states')][:4]
        top_modes = [k for k in values.keys() if k.startswith('modes')][:4]
        top_throttle = [k for k in values.keys() if k.startswith('throttle')][:4]
        
        # Generate combinations
        for i in range(4):
            gfact = top_gfact[i % len(top_gfact)]
            state = top_states[i % len(top_states)]
            mode = top_modes[i % len(top_modes)]
            throttle = top_throttle[i % len(top_throttle)]
            combination = [gfact, state, mode, throttle]
            
            # Ensure combination is unique
            while tuple(combination) in generated_combinations:
                # Rotate cycle types for the next iteration
                cycle_index = (cycle_index + 1) % len(cycle_types)
                
                if cycle_types[cycle_index] == 'throttle':
                    top_throttle.append(top_throttle.pop(0))
                elif cycle_types[cycle_index] == 'modes':
                    top_modes.append(top_modes.pop(0))
                elif cycle_types[cycle_index] == 'states':
                    top_states.append(top_states.pop(0))
                
                # Generate new combination
                gfact = top_gfact[i % len(top_gfact)]
                state = top_states[i % len(top_states)]
                mode = top_modes[i % len(top_modes)]
                throttle = top_throttle[i % len(top_throttle)]
                combination = [gfact, state, mode, throttle]
            
            # Add to generated combinations set
            generated_combinations.add(tuple(combination))
            combinations.append(combination)
    
    return combinations


def Clustering():
    DATA_FILE = 'L1_TESTS_FINAL_SUBMISSION.csv'

    df = pd.read_csv(DATA_FILE)

    df['throttle'] = df['throttle'].apply(lambda x: str(x).split('.')[0] if pd.notna(x) else None)
    df.fillna(value='None', inplace=True)
    df['Wind'] = df['Wind'].apply(lambda x: 1 if x is not None else 0)
    df['duration'] = pd.to_timedelta(df['duration']).dt.total_seconds()
    df = df.drop(columns='Unnamed: 0')
    df['throttle'] = df['throttle'].fillna('None')
    df = df.rename(columns={'MSN State': 'states'})
    df = df.rename(columns={'mode_switch': 'modes'})
    df = df.rename(columns={'Mode': 'initial_mode'})
    df['modes'] = df['modes'].str.replace('AUTO.', '')
    df['GFACT'] = df['GFACT'].str.replace(' mode', '')

    df = df[df['states'] != 'ReceiveMission']
    df = df[['throttle', 'GFACT', 'modes', 'states']]

    # Identifying categorical columns
    categorical_cols = df.select_dtypes(include=['object', 'bool']).columns

    # Convert all values in categorical columns to strings
    df[categorical_cols] = df[categorical_cols].astype(str)

    # Initialize OneHotEncoder
    encoder = OneHotEncoder(sparse_output=False, drop='first')  # drop='first' to avoid multicollinearity

    # Fit and transform the data
    encoded_data = encoder.fit_transform(df[categorical_cols])

    # Get the column names for the encoded columns
    encoded_cols = encoder.get_feature_names_out(categorical_cols)

    # Create a dataframe with the encoded data
    encoded_df = pd.DataFrame(encoded_data, columns=encoded_cols)

    # Drop the original categorical columns from the original dataframe
    df = df.drop(columns=categorical_cols)

    # Concatenate the original dataframe with the encoded dataframe
    df_encoded = pd.concat([df, encoded_df], axis=1)

    df_encoded = df_encoded.drop(columns='throttle_None', axis=1)

    # Drop rows with missing values
    df_encoded = df_encoded.dropna()

    # Standardize the data
    scaler = StandardScaler()
    df_scaled = scaler.fit_transform(df_encoded)

    # Perform K-means clustering
    kmeans = KMeans(n_clusters=3, random_state=22)  # You can adjust the number of clusters
    df_encoded['cluster'] = kmeans.fit_predict(df_scaled)
    
    encoded_cols = list(encoded_cols)
    encoded_cols.remove('throttle_None')
    # Encode categorical features
    categorical_features = encoded_cols
    for feature in categorical_features:
        le = LabelEncoder()
        df_encoded[feature] = le.fit_transform(df_encoded[feature].astype(str))

    # Dictionary to store feature importances for each cluster
    cluster_feature_importance = {}

    # Perform chi-square test for each cluster (one-vs-rest)
    for cluster in df_encoded['cluster'].unique():
        feature_importances = {}

        # Create binary labels for the current cluster
        df_encoded['target'] = (df_encoded['cluster'] == cluster).astype(int)

        # Calculate chi-square statistic for each feature
        for feature in categorical_features:
            contingency_table = pd.crosstab(df_encoded[feature], df_encoded['target'])
            chi2, p, dof, ex = chi2_contingency(contingency_table)
            feature_importances[feature] = chi2

        # Store sorted feature importances
        cluster_feature_importance[cluster] = pd.Series(feature_importances).sort_values(ascending=False)

    sorted_data = sort_and_arrange(cluster_feature_importance)
    combinations = generate_combinations(sorted_data)

    return combinations

if __name__ == '__main__':
    print(Clustering())
