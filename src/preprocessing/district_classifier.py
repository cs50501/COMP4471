import json
from pathlib import Path
from shapely.geometry import Point, shape


ROOT = Path(__file__).resolve().parents[2]
json_path = ROOT / "data" / "boundaries" / "hksar_18_district_boundary.json"


with open(json_path, "r", encoding="utf-8-sig") as file:
    data = json.load(file)

districts = data["features"]


def get_district(longitude, latitude):
    point = Point(longitude, latitude)

    for district in districts:
        polygon = shape(district["geometry"])

        if polygon.covers(point):
            return district["properties"]["District"]

    return "unassigned"
