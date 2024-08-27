import numpy as np
import pandas as pd
# import random
# import os
# import json
# from sklearn.datasets import make_classification
# from sympy import symbols, Not, And, Or
# from sympy.logic.boolalg import to_cnf
# from itertools import combinations
# import matplotlib.pyplot as plt
# import pyparsing as pp
# from schemdraw import logic, Drawing
from schemdraw.parsing import logicparse
import schemdraw
import re
import logicmin
import cairosvg

GEOFENCE_ACTION = {1: "Warning", 2: "Hold mode", 3: "Return mode", 4: "Terminate", 5: "Land mode"}


def minLogicFunc(truthtable):

    # Identify the input columns and the output column
    input_columns = [col for col in truthtable.columns if col != 'result']
    output_column = 'result'

    # Initialize the truth table with the appropriate number of inputs and 1 output
    t = logicmin.TT(len(input_columns), 1)

    # Add rows to the truth table (input, output)
    for index, row in truthtable.iterrows():
        inputs = ''.join(str(row[col]) for col in input_columns)
        output = str(row[output_column])
        t.add(inputs, output)
    # Initialize the truth table with 3 inputs and 1 output
    # t = logicmin.TT(3, 1)

    # Add rows to the truth table (input, output)
    # t.add("000", "1")
    # t.add("001", "0")
    # t.add("010", "0")
    # t.add("011", "0")
    # t.add("100", "0")
    # t.add("101", "0")
    # t.add("110", "0")
    # t.add("111", "0")

    # Minimize functions and get solutions
    sols = t.solve()

    # Print solution mapped to variable names (xnames=inputs, ynames=outputs)
    # Add debug information
    return sols.printN(xnames=input_columns, ynames=output_column, info=False)




def drawFaultTree(logic_expr, Centroid):
    # Using regular expression to find all alphanumeric words
    features = re.findall(r'\b\w+\b', logic_expr)

    # Convert list to set to get unique elements and remove 'and' and 'or'
    features = set(features) - {'and', 'or', 'not'}


    for feature in features:
        print('Feature - ', feature)
        if feature.startswith("GFACT_"):
            extracted_value = feature.split("GFACT_")[1]
            if extracted_value == 'None':
                pattern = r'\bGFACT_None\b'
                replacement = '(geofence_ON and geofenceAction_OFF)'
            else:
                pattern = r'\bGFACT_{}\b'.format(re.escape(extracted_value))
                replacement = '(geofence_ON and geofenceAction_{})'.format(extracted_value)
            
            logic_expr = re.sub(pattern, replacement, logic_expr)
        # else:
        #     logic_copy = re.sub(r'\b{}\b'.format(feature), r'{}_{}'.format(feature, value), logic_copy)
        
        # logic_copy = re.sub(r'\b{}\b'.format(feature), r'{}_{}'.format(feature, value), logic_copy)/

    print('[Debug] This is the final logic expression - ', logic_expr)

    with schemdraw.Drawing(file='Combination_'+str(Centroid)+'.svg', show=False):
        # logic_expr = '(not a and not c ) or ( a and c ) or ( a and b)'
        logicparse(logic_expr, outlabel=r'TopEvent')
    cairosvg.svg2pdf(file_obj=open('Combination_'+str(Centroid)+'.svg', 'rb'), write_to='Combination_'+str(Centroid)+'.pdf')
    



def convert_logic_to_boolean(expression):
    # Replace <= with an empty string (assuming it's not part of the logic operation)
    expression = expression.replace('r <=', '')

    if expression == '0':
        return '0'

    # Replace each term
    expression = expression.replace('.', ' and ').replace('+', ') or (')

    # Use re.sub() to replace matches with 'not something'
    expression = re.sub(r'(\w+)\'', r'not \1', expression)

    # Replace variables surrounded by spaces with themselves and concatenate with "and"
    terms = expression.split()
    # for i in range(len(terms)):
    #     if terms[i].isalpha():
    #         terms[i] = f'({terms[i]})'

    return '(' + ' '.join(terms) + ')'


def mincutSets(expression):

        # Step 1: Split by 'or' to get main conditions
    main_conditions = expression.split('or')

    # List to store elements
    mincutSets = []

    minFeatures = 5

    # Step 2: Process each main condition
    for condition in main_conditions:
        # Split by 'and' to get individual elements
        mincut = condition.split('and')
        
        # Trim and remove extra spaces from each element
        mincut = [elem.strip().replace('(', '').replace(')', '') for elem in mincut]

        if len(mincut) < minFeatures:
            minFeatures = len(mincut)
            # Add to the main list of elements
        mincutSets.append(tuple(mincut))

    for i in mincutSets:
        if len(i) > minFeatures:
            mincutSets.remove(i)
    return mincutSets



# # Example usage:
# logical_expression = "s <= a'.c' + a.c + a.b"
# boolean_expression = convert_logic_to_boolean(logical_expression)
# print(boolean_expression)
