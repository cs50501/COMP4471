import os
from pathlib import Path
from dotenv import load_dotenv
from src.preprocessing.district_classifier import get_district


import requests


# root path
ROOT = Path(__file__).resolve().parents[1]


# mapillary access token
load_dotenv(ROOT / ".env")
TOKEN = os.getenv("MAPILLARY_ACCESS_TOKEN")


# just to check if there is a token, should work
if TOKEN:
    print("Mapillary API token is loaded successfully")
else:
    print("error: no mapillary api token")
    

# api request
image_id = "682118955840805"
url = f"https://graph.mapillary.com/{image_id}"


params = {
    "access_token": TOKEN,
    "fields": "id,captured_at,thumb_1024_url,computed_geometry,sequence"
}


# json response to get da data
response = requests.get(url, params=params, timeout=20)
data = response.json()
coordinates = data["computed_geometry"]["coordinates"]
longitude = coordinates[0]
latitude = coordinates[1]
district = get_district(longitude, latitude)



# download the actual image
image_url = data["thumb_1024_url"]
image_response = requests.get(image_url, timeout=30)
image_response.raise_for_status


# save the image
folder_name = district.removesuffix(" District").lower().replace(" ", "_")
save_path = ROOT / "data" / "raw" / folder_name / f"{image_id}.jpg"
save_path.parent.mkdir(parents=True, exist_ok=True)
with open(save_path, "wb") as file:
    file.write(image_response.content)
    print(f"Image successfully saved to: {save_path}")