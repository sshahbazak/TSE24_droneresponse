# Genetic Algorithm for Fuzz Testing Optimization

This documentation provides an overview of a Genetic Algorithm (GA) implementation used to optimize model parameters based on data from fuzz testing. The algorithm iteratively improves the detection of anomalies using an isolation forest model.

## Overview

The script starts with an initial dataset (the first generation), where each row is treated as a chromosome. An isolation forest model is trained to detect anomalies, and based on the results, the dataset is divided into parents and mutant candidates. The GA performs crossover and mutation operations to generate new probe inputs, which are then evaluated using fuzz testing. Over several generations, the algorithm aims to produce increasingly better anomalies.

## Modules and Dependencies

- **FuzzTestor (Fuzz Module)**: Custom module for executing fuzz tests.
- **modelTrain**: Custom module for training the isolation forest model used in the fitness evaluation.

## Parameters

- **NUM_GENERATIONS**: The number of generations the genetic algorithm will run. Default is 10.
- **DATA_FILE**: Path to the CSV file containing the dataset.
- **NUM_PARENTS**: Number of parents selected for crossover in each generation.
- **NUM_MUTANTS**: Number of mutants generated in each generation.

## Feature Dictionary

The script includes several dictionaries that define the features and their possible values:

- **FEATURE_DICT**: Contains features and their possible values or range tuples.
- **GEOFENCE_ACTION**: Maps geofence actions to numeric codes.
- **THROTTLE_DICT**: Maps throttle values to specific codes.
- **STATES_DICT**: Maps states to corresponding functions or values.
- **COLUMN_NAMES**: List of column names in the dataset.

## Classes and Methods

### GeneticAlgorithm Class

Implements the genetic algorithm. Key methods include:

- **`__init__(self)`**: Initializes the class, loads the dataset, and sets up instances of `FuzzTestor` and `Model`.
- **`fitness_function(self)`**: Calculates the fitness of the current population by training the model.
- **`select_parents(self, parent_candidates_df)`**: Selects parents for crossover using tournament selection.
- **`crossover(self, parents_df)`**: Performs crossover to generate new offspring.
- **`mutate(self, mutant_candidates_df)`**: Generates mutants by modifying certain features.
- **`run_algorithm(self)`**: The main loop for running the genetic algorithm across multiple generations.

### Model Class (modelTrain.py)

The `Model` class is responsible for:

- **Training** an isolation forest model on the dataset.
- **Encoding** categorical variables using one-hot encoding.
- **Predicting** anomalies and scoring them based on their anomaly levels.

## Execution

To run the genetic algorithm:

1. Instantiate the `GeneticAlgorithm` class.
2. Call the `run_algorithm()` method to start the process.

## Usage Example

```python
if __name__ == "__main__":
    ga = GeneticAlgorithm()
    ga.run_algorithm()
