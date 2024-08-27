import pandas as pd
import numpy as np
import warnings
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import OneHotEncoder

class Model:
    def __init__(self):
        self.encoder = None
        self.model = None
        self.numerical_cols = None
        self.categorical_cols = None

    def train_model(self, data_file):
        print('[Model Training] Starting Model Training process....')
        df = pd.read_csv(data_file)
        # df.fillna(value = 'None',inplace=True)
        df['Wind'] = df['Wind'].apply(lambda x: 1 if x is not None else 0)
        # print(df.dtypes)

        # Define the numerical and categorical columns
        self.numerical_cols = ['Wind', 'max_deviation', 'max_altitude', 'duration']
        self.categorical_cols = [col for col in df.columns if col not in self.numerical_cols]

        # One-hot encode categorical variables
        self.encoder = OneHotEncoder(sparse_output=False)
        encoded_categorical = self.encoder.fit_transform(df[self.categorical_cols])

        # Get feature names for encoded categorical variables
        encoded_categorical_feature_names = self.encoder.get_feature_names_out(self.categorical_cols)

        # Create a DataFrame from the encoded categorical variables
        encoded_categorical_df = pd.DataFrame(encoded_categorical, columns=encoded_categorical_feature_names)

        # Combine numerical and encoded categorical columns
        df_combined = pd.concat([df[self.numerical_cols], encoded_categorical_df], axis=1)

        # Fit Isolation Forest model for anomaly detection
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")  # Suppress specific warning
            self.model = IsolationForest(contamination=0.1, random_state=42)
            self.model.fit(df_combined)

        # Predict anomalies
        y_pred = self.model.predict(df_combined)

        # Get anomaly scores
        anomaly_scores = self.model.decision_function(df_combined)
        print(f'[Model Training] Anomaly Score ranges - min: {min(anomaly_scores)}, max: {max(anomaly_scores)}')

        # Add anomaly scores and predictions to the DataFrame
        df['anomaly_score'] = anomaly_scores
        df['anomaly'] = y_pred
        print('[Model Training] Model Successfully Trained')

        # Return the DataFrame (optional)
        return df

    def get_anomaly_score(self, row):
        
        numerical_data = pd.DataFrame(row[self.numerical_cols].values.reshape(1, -1), columns=self.numerical_cols)
        categorical_data = pd.DataFrame(row[self.categorical_cols].values.reshape(1, -1), columns=self.categorical_cols)

        # One-hot encode the categorical data using the trained encoder
        encoded_categorical = self.encoder.transform(categorical_data)

        # Create DataFrames for numerical and encoded categorical data with feature names
        numerical_df = pd.DataFrame(numerical_data, columns=self.numerical_cols)
        encoded_categorical_df = pd.DataFrame(encoded_categorical, columns=self.encoder.get_feature_names_out(self.categorical_cols))

        # Combine numerical and encoded categorical columns
        combined_data = pd.concat([numerical_df, encoded_categorical_df], axis=1)

        # Compute the anomaly score using the trained model
        anomaly_score = self.model.decision_function(combined_data)
        
        return anomaly_score[0]

# Example usage:
if __name__ == '__main__':
    model_instance = Model()
    df = model_instance.train_model('sample.csv')

    # Assuming you want to get anomaly score for the first row
    row = df.iloc[0]
    anomaly_score = model_instance.get_anomaly_score(row)
    print(f'Anomaly score for row {0}: {anomaly_score}')
