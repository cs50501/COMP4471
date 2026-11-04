import csv
import os
import requests
from pathlib import Path
from collections import defaultdict
from dotenv import load_dotenv
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


ROOT = Path(__file__).resolve().parents[1]


load_dotenv(ROOT / ".env")
TOKEN = os.getenv("MAPILLARY_ACCESS_TOKEN")


CSV_PATH = ROOT / "data" / "metadata" / "images.csv"
IMAGE_DIR = ROOT / "data" / "raw"


# change this
MAX_PER_DISTRICT = 500


if not TOKEN:
    raise RuntimeError("Mapillary access token not found.")
if not CSV_PATH.exists():
    raise FileNotFoundError(f"Metadata CSV not found: {CSV_PATH}")


session = requests.Session()
retry_strategy = Retry(
    total = 3,
    backoff_factor=1,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["GET"],
    respect_retry_after_header=True
)
session.mount(
    "https://",
    HTTPAdapter(max_retries=retry_strategy)
)


def download_image(image_id, district):
    
    folder_name = district.lower().replace(" ", "_")
    folder = IMAGE_DIR / folder_name
    folder.mkdir(parents=True, exist_ok=True)
    
    save_path = folder / f"{image_id}.jpg"
    temp_path = folder / f"{image_id}.jpg.part"
    
    # Skip images already downloaded successfully
    if save_path.exists() and save_path.stat().st_size > 0:
        return "skipped"
    
    try:
        
        response = session.get(
            f"https://graph.mapillary.com/{image_id}",
            params={
                "access_token": TOKEN,
                "fields": "thumb_1024_url"
            },
            timeout=30
        )
        response.raise_for_status()
        
        image_url = response.json().get("thumb_1024_url")
    
        if not image_url:
            raise ValueError("Image URL unavailable")
        
        with session.get(
            image_url,
            stream=True,
            timeout=60
        ) as image_response:
            
            image_response.raise_for_status()
            
            content_type = image_response.headers.get(
                "Content-Type", ""
            ).lower()
            
            if not content_type.startswith("image/jpeg"):
                raise ValueError(
                    f"Unexpected content type: {content_type}"
                )
                
            with open(temp_path, "wb") as file:
                for chunk in image_response.iter_content(
                    chunk_size=8192
                ):
                    if chunk:
                        file.write(chunk)
                        
        if temp_path.stat().st_size == 0:
            raise ValueError("Downloaded file is empty")
        
        temp_path.replace(save_path)
        
        return "downloaded"
    
    except (requests.RequestException, ValueError, OSError) as error:
        temp_path.unlink(missing_ok=True)
        print(f"Failed {image_id}: {error}")
        return "failed"


def main():
    
    downloaded = 0
    skipped = 0
    failed = 0
    
    district_counts = defaultdict(int)
    
    with open(CSV_PATH, "r", newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        
        for row in reader:
            image_id = row["image_id"].strip()
            district = row["district"].strip()
            
            if not image_id or not district:
                continue
            
            if district_counts[district] >= MAX_PER_DISTRICT:
                continue
            
            result = download_image(image_id, district)
            
            if result == "downloaded":
                downloaded += 1
                district_counts[district] += 1
                
            elif result == "skipped":
                skipped += 1
                district_counts[district] += 1
                
            else:
                failed += 1
                
    print("\nDownload summary:")
    print(f"New downloads: {downloaded}")
    print(f"Existing images skipped: {skipped}")
    print(f"Failed attempts: {failed}")
    
    print("\nImages per district:")
    for district, count in sorted(district_counts.items()):
        print(f"{district}: {count}")
        
        
if __name__ == "__main__":
    main()
