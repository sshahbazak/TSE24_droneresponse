# TSE24_droneresponse - Documentation for the Fault Analysis Pipeline

## 1. Introduction

This pipeline aims to perform fault analysis using clustering, anomaly detection, and fault tree generation. The process starts by clustering the input dataset, analyzing feature importance, constructing truth tables, and executing tests based on valid feature combinations. The results are processed through a decision tree for anomaly detection, and finally, fault trees are constructed to diagnose potential system failures. This document provides a detailed overview of each step involved in this pipeline.

## 2. Clustering (Clustering.py)

### Overview

The `Clustering.py` script is responsible for clustering the data provided in the `L1_TESTS_FINAL_SUBMISSION.csv` file. The purpose of clustering is to categorize the data into groups that exhibit similar behavior. The following steps are involved in this process:

1. **Data Preprocessing**: The raw data is cleaned and prepared for analysis. This includes handling missing values, normalizing numerical data, and ensuring that the dataset is in a suitable format for encoding and transformation.

2. **Data Encoding**: Categorical data is encoded into numerical format using techniques like one-hot encoding or label encoding, which are necessary for applying machine learning algorithms.

3. **Data Transformation**: Transformations such as scaling and normalization are applied to the data to make it suitable for clustering. This ensures that features with different scales do not disproportionately affect the clustering results.

4. **K-Means Clustering**: The preprocessed and encoded data is then clustered using the K-Means algorithm. This method partitions the data into `k` clusters, where each data point belongs to the cluster with the nearest mean.

5. **Feature Importance Using Chi-Squared Test**: After clustering, a chi-squared contingency test is applied to find the importance of each feature within the clusters. This statistical test measures how likely the observed distribution of feature values would be, assuming the features are independent of the clusters.

6. **Combination Generation**: Based on the feature importance scores, combinations of important features are generated. These combinations represent the most significant feature interactions and are returned for further analysis.

## 3. Truth Table Construction and Validation

Once the significant feature combinations are identified, a truth table is constructed to validate these combinations. The truth table serves as a guide for which combinations of features are feasible for running probes and which are not.

### Valid Combinations

A list of predefined valid combinations is used to determine feasibility:

```python
valid_combinations = [
    ['GFACT'],
    ['GFACT', 'modes'],
    ['GFACT', 'modes', 'throttle'],
    ['states', 'modes'],
    ['states', 'throttle'],
    ['states', 'modes', 'throttle']
]
```

Any combination not listed here is marked as `0` in the truth table, indicating that it is not a valid scenario for testing. Valid combinations are marked as `1` and are used in subsequent testing phases.

## 4. Execution of Valid Combinations (Theo's Code)

Theo's code is utilized to run tests based on the valid feature combinations identified in the truth table. This code performs the following:

- **HIFuzz Testing**: It executes HIFuzz tests using the specified combinations of features such as `GFACT`, `modes`, `states`, and `throttle`.
- **Logging Improvements**: Modifications have been made to the logging mechanism to ensure detailed output. The log file now includes information about the test configurations, results, truth table entries, deviation calculations, and the specific combination and test being executed.
- **Initialization Fixes**: Enhancements have been implemented to correctly initialize the testing environment, allowing for multiple probes to be executed sequentially without reinitialization issues.

## 5. Anomaly Detection Using Decision Tree

The output from Theo's code is passed through a decision tree to classify the test results. This decision tree helps identify anomalies in the system's behavior based on the test results. If an anomaly is detected, the output is marked as `1`; otherwise, it is marked as `0`.

### Future Improvements

There is ongoing work to refine this decision tree. Jane is currently developing a more sophisticated decision tree model that will provide more accurate anomaly detection capabilities.

## 6. Fault Tree Helpers

After completing the anomaly detection process, the final truth table is processed using the `FaultTreeHelper.py` script. This module performs the following functions:

- **Minimum Logic Function**: It identifies the simplest logical representation of the fault scenarios based on the truth table.
- **Boolean Logic Expression**: A boolean logic expression is constructed, representing the logical dependencies between different features and fault conditions.
- **Fault Tree Visualization**: Using the `schemdraw` library, a visual fault tree is generated. This tree illustrates the logical structure of the fault analysis, showing how different conditions and failures lead to a fault.
- **Minimum Cut Sets**: The script identifies the minimum cut sets, which are the smallest combinations of conditions that can lead to a fault. These cut sets are critical for understanding and mitigating system vulnerabilities.