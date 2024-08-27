from schemdraw.parsing import logicparse
import schemdraw
import re
import cairosvg

logic_expr = '(not GFACT_None and not states_Flying and not GFACT_Land and not GFACT_Return and GFACT_Warning and not states_Land and not states_Hover and not states_Takeoff ) or ( not GFACT_None and not states_Flying and not GFACT_Land and GFACT_Return and not GFACT_Warning and not states_Land and not states_Hover and not states_Takeoff ) or ( not GFACT_None and not states_Flying and GFACT_Land and not GFACT_Return and not GFACT_Warning and not states_Land and not states_Hover and not states_Takeoff ) or ( GFACT_None and not states_Flying and not GFACT_Land and not GFACT_Return and not GFACT_Warning and not states_Land and not states_Hover and not states_Takeoff)'

GEOFENCE_ACTION = {1: "Warning", 2: "Hold mode", 3: "Return mode", 4: "Terminate", 5: "Land mode"}

# Using regular expression to find all alphanumeric words
features = re.findall(r'\b\w+\b', logic_expr)

# Convert list to set to get unique elements and remove 'and' and 'or'
features = set(features) - {'and', 'or', 'not'}

# Update logic expression with geofence logic
for feature in features:
    if feature.startswith("GFACT_"):
        extracted_value = feature.split("GFACT_")[1]
        if extracted_value == 'None':
            logic_expr = re.sub(r'GFACT_None', 'geofence_ON and geofenceAction_OFF', logic_expr)
        else:
            logic_expr = re.sub(r'GFACT_{}'.format(extracted_value), r'geofence_ON and geofenceAction_{}'.format(extracted_value), logic_expr)

print("Updated Logic Expression:")
print(logic_expr)

with schemdraw.Drawing(file='Centroid.svg'):
        logic_expr = '(not a and not c ) or ( a and c ) or ( a and b)'
        logicparse(logic_expr, outlabel=r'TopEvent')

# Convert SVG to PNG
cairosvg.svg2pdf(file_obj=open('Centroid.svg', 'rb'), write_to='Centroid.pdf')