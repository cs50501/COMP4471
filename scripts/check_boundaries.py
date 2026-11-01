# just to check the hksar_18_district_boundary.json file if it works

import json
from pathlib import Path
from shapely.geometry import Point, shape


ROOT = Path(__file__).resolve().parents[1]


json_path = ROOT / "data" / "boundaries" / "hksar_18_district_boundary.json"


with open(json_path, "r", encoding="utf-8-sig") as file:
    data=json.load(file)
    print(data.keys())

districts = data["features"]

print("Number of districts:", len(districts))
print("First district properties:", districts[0]["properties"])
    
    
# test point
longitude = 114.173
latitude = 22.279

point = Point(longitude, latitude)


# test if the point is correct according to the json file, the test point should be roughly in Wan Chai
for district in districts:
    polygon = shape(district["geometry"])
    
    if polygon.covers(point):
        print("District:", district["properties"]["District"])
        break
    else:
        print("No matching district found")