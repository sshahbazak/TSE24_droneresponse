import pandas as pd
import FuzzTest as ft

def run_probe(df):
    results = []
    for _, row in df.iterrows():
        fuzz_test_args = {'drone_id': 'Polkadot'}

        # Dynamically add arguments if they are not None
        if row['modes'] is not None:
            fuzz_test_args['modes'] = [row['modes']]
        if row['states'] is not None:
            fuzz_test_args['states'] = [row['states']]
        if row['GFACT'] is not None:
            fuzz_test_args['GFACT'] = [row['GFACT']]
        if row['throttle'] is not None:
            fuzz_test_args['throttle'] = [row['throttle']]

        print(fuzz_test_args)
        # Call the Fuzz_Test function with the unpacked dictionary
        result = ft.Fuzz_Test(**fuzz_test_args)
        results.append(result)
    
    return results

if __name__ == "__main__":
    data = {
        'modes' : ['POSCTL', 'OFFBOARD', 'STABILIZED'],
        'states' : ['hover', 'hover', 'hover'],
        'GFACT' : ['Return mode', None, 'Land mode'],
        'throttle' : [255, 600, 500]
    }

    # Create the DataFrame
    df = pd.DataFrame(data)

    results = run_probe(df)

    # Print the results
    for result in results:
        print(result)
