from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IMAGE_DIR = ROOT / "data" / "raw"

TARGET_PER_DISTRICT = 3000

total_images = 0

print("\nCOMP4471 Dataset Download Progress")
print("-" * 55)

for district_folder in sorted(IMAGE_DIR.iterdir()):

    if not district_folder.is_dir():
        continue

    # Count only JPEG images
    image_count = len(list(district_folder.glob("*.jpg")))

    total_images += image_count

    percentage = image_count / TARGET_PER_DISTRICT * 100

    print(
        f"{district_folder.name:<25} "
        f"{image_count:>5}/{TARGET_PER_DISTRICT} "
        f"({percentage:.1f}%)"
    )

print("-" * 55)
print(f"Total downloaded images: {total_images:,}")
print(f"Overall target: {TARGET_PER_DISTRICT * 18:,}")
print(
    f"Overall progress: "
    f"{total_images / (TARGET_PER_DISTRICT * 18) * 100:.1f}%"
)
