import os
import requests
import math
import json
import csv
import time
import random
from pathlib import Path
from dotenv import load_dotenv
from shapely.geometry import shape, box
from src.preprocessing.district_classifier import get_district


ROOT = Path(__file__).resolve().parents[2]


load_dotenv(ROOT / ".env")
TOKEN = os.getenv("MAPILLARY_ACCESS_TOKEN")


json_path = ROOT / "data" / "boundaries" / "hksar_18_district_boundary.json"


with open(json_path, "r", encoding="utf-8-sig") as file:
    district_data = json.load(file)


districts = district_data["features"]


MAX_METADATA_PER_DISTRICT = 6000


# basically split the districts into smaller grid boxes because there's a limit for how many images u can get per request
def generate_grid(polygon, cell_size=0.01):
    west, south, east, north = polygon.bounds
    
    n_cols = math.ceil((east - west) / cell_size)
    n_rows = math.ceil((north - south) / cell_size)
    
    grid = []
    
    for row in range(n_rows):
        for col in range(n_cols):
            
            x_min = west + col * cell_size
            y_min = south + row * cell_size
            
            x_max = min(x_min + cell_size, east)
            y_max = min(y_min + cell_size, north)
            
            cell = box(x_min, y_min, x_max, y_max)
            
            if polygon.intersection(cell).area > 0:
                grid.append((x_min, y_min, x_max, y_max))
                
    return grid


def split_bbox(bbox):
    west, south, east, north = bbox
    
    mid_lon = (west + east) / 2
    mid_lat = (south + north) / 2
    
    return [
        (west, south, mid_lon, mid_lat),
        (mid_lon, south, east, mid_lat),
        (west, mid_lat, mid_lon, north),
        (mid_lon, mid_lat, east, north)
    ]


def search_images(bbox, max_retries=3):
    url = "https://graph.mapillary.com/images"
    
    params = {
        "access_token": TOKEN,
        "bbox": ",".join(map(str, bbox)),
        "fields": "id,computed_geometry,sequence,captured_at",
        "limit": 500
    }
    
    for attempt in range(1, max_retries + 1):
        
        try:
            response = requests.get(
                url,
                params=params,
                timeout=30
            )
            
            response.raise_for_status()
            data = response.json()
            
            return data["data"]
        
        except requests.RequestException as error:
            
            status = (
                error.response.status_code
                if error.response is not None
                else None
            )
            
            retryable = (
                status is None
                or status == 429
                or 500 <= status < 600
            )
            
            if not retryable or attempt == max_retries:
                raise
            
            wait_time = 2 ** attempt
            
            print(
                f"Request_failed: {error}."
                f"Retrying in {wait_time} seconds..."
            )
            
            time.sleep(wait_time)


def search_images_recursive(bbox, depth=0, max_depth=3):
    
    images = search_images(bbox)
    
    print(f"Depth {depth}: Found {len(images)} images")
    
    # Store the images already discovered
    all_images = {image["id"]: image for image in images}
    
    # Stop if the result count is below our threshold
    if len(images) < 400:
        return list(all_images.values())
    
    # Prevent excessive subdivision
    if depth >= max_depth:
        print("Warning: Maximum depth reached!")
        return list(all_images.values())
    
    # Split into four smaller bounding boxes
    smaller_boxes = split_bbox(bbox)
    
    for cell in smaller_boxes:
        cell_images = search_images_recursive(
            cell,
            depth=depth + 1,
            max_depth=max_depth
        )
        
        # Merge child results with existing results
        for image in cell_images:
            all_images[image["id"]] = image
            
    return list(all_images.values())


def filter_images_by_district(images, district_name):
    filtered_images = {}
    
    for image in images:
        geometry = image.get("computed_geometry") or {}
        coordinates = geometry.get("coordinates")
        
        if not coordinates:
            continue
        
        longitude, latitude = coordinates
        
        if get_district(longitude, latitude) == district_name:
            filtered_images[image["id"]] = image
            
    return list(filtered_images.values())


def save_metadata_csv(images, district_name):
    
    save_path = ROOT / "data" / "metadata" / "images.csv"
    save_path.parent.mkdir(parents=True, exist_ok=True)
    
    fieldnames = [
        "image_id",
        "latitude",
        "longitude",
        "district",
        "sequence_id",
        "captured_at"
    ]
    
    # Read existing image IDs
    existing_ids = set()
    
    if save_path.exists():
        with open(save_path, "r", newline="", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            
            for row in reader:
                existing_ids.add(row["image_id"])
                
    # Check if the CSV already exists and has a header
    has_header = save_path.exists() and save_path.stat().st_size > 0
    
    new_count = 0
    
    with open(save_path, "a", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        
        if not has_header:
            writer.writeheader()
            
        for image in images.values():
            
            image_id = str(image["id"])
            
            # Skip images already recorded
            if image_id in existing_ids:
                continue
            
            geometry = image.get("computed_geometry") or {}
            coordinates = geometry.get("coordinates")
            
            if not coordinates:
                continue
            
            longitude, latitude = coordinates
            
            sequence = image.get("sequence")
            if isinstance(sequence, dict):
                sequence = sequence.get("id")
                
            writer.writerow({
                "image_id": image_id,
                "latitude": latitude,
                "longitude": longitude,
                "district": district_name.removesuffix(" District"),
                "sequence_id": sequence,
                "captured_at": image.get("captured_at")
            })
            
            # Update the set so duplicates are also
            # prevented within the current batch
            existing_ids.add(image_id)
            new_count += 1
            
    print(f"New images added: {new_count}")
    print(f"Total unique image IDs: {len(existing_ids)}")
    print(f"Metadata saved to: {save_path}")


def load_existing_ids(district_name):
    
    path = ROOT / "data" / "metadata" / "images.csv"
    existing_ids = set()
    
    if not path.exists():
        return existing_ids
    
    with open(path, "r", newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        
        for row in reader:
            if row["district"] == district_name.removesuffix(" District"):
                existing_ids.add(row["image_id"])
                
    return existing_ids


def get_grid_id(district_name, bbox):
    coordinates = ",".join(f"{value:.10f}" for value in bbox)
    
    return f"{district_name}|{coordinates}"


PROGRESS_PATH = ROOT / "data" / "metadata" / "search_progress.csv"


def load_completed_grids():
    completed = set()
    
    if not PROGRESS_PATH.exists():
        return completed
    
    with open(PROGRESS_PATH, "r", newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        
        for row in reader:
            completed.add(row["grid_id"])
            
    return completed


def mark_grid_completed(grid_id, district_name):
    
    PROGRESS_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    has_header = (
        PROGRESS_PATH.exists()
        and PROGRESS_PATH.stat().st_size > 0
    )
    
    with open(PROGRESS_PATH, "a", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        
        if not has_header:
            writer.writerow(["grid_id", "district"])
            
        writer.writerow([grid_id, district_name])






if __name__ == "__main__":
    
    completed_grids = load_completed_grids()
    
    # None = all 18 districts
    ONLY_DISTRICT = None
    
    for district in districts:
        
        name = district["properties"]["District"]
        polygon = shape(district["geometry"])
        
        if ONLY_DISTRICT is not None and name != ONLY_DISTRICT:
            continue
        
        # Load image IDs already saved for this district
        existing_ids = load_existing_ids(name)
        
        # Generate grid and randomize search order
        grid = generate_grid(polygon)
        random.Random(42).shuffle(grid)
        
        print(f"\n{'=' * 50}")
        print(f"Searching {name}")
        print(f"Total grid cells: {len(grid)}")
        print(f"Existing images: {len(existing_ids)}")
        print(f"Target: {MAX_METADATA_PER_DISTRICT}")
        print(f"{'=' * 50}")
        
        for i, bbox in enumerate(grid, start=1):
            
            # Stop once the metadata target is reached
            if len(existing_ids) >= MAX_METADATA_PER_DISTRICT:
                print(f"{name}: Metadata target reached!")
                break
            
            grid_id = get_grid_id(name, bbox)
            
            # Skip previously completed grids
            if grid_id in completed_grids:
                print(f"Grid {i}/{len(grid)}: Already completed. Skipping.")
                continue
            
            # Search Mapillary
            images = search_images_recursive(bbox)
            
            # Keep only images in the correct district
            filtered_images = filter_images_by_district(
                images, name
            )
            
            # Exclude image IDs already saved
            new_candidates = [
                image for image in filtered_images
                if str(image["id"]) not in existing_ids
            ]
            
            # Randomize which images to keep
            random.shuffle(new_candidates)
            
            # Calculate how many more images we need
            remaining = MAX_METADATA_PER_DISTRICT - len(existing_ids)
            
            # Select up to the remaining quota
            selected_images = new_candidates[:remaining]
            
            new_images = {
                str(image["id"]): image
                for image in selected_images
            }
            
            # Save metadata
            save_metadata_csv(new_images, name)
            
            # Update existing IDs
            existing_ids.update(new_images.keys())
            
            # Mark complete only if we saved all new candidates
            if len(new_candidates) <= remaining:
                mark_grid_completed(grid_id, name)
                completed_grids.add(grid_id)
            else:
                print("Grid partially saved due to metadata limit.")
                
            print(
                f"Grid {i}/{len(grid)}: "
                f"Added {len(new_images)} images. "
                f"Total: {len(existing_ids)}"
            )
            
        print(f"\nFinished {name}")
        print(f"Total metadata images: {len(existing_ids)}")
        
    print("\nAll selected districts processed!")





