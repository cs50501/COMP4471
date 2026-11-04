import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main():
    
    print("Starting COMP4471 data collection pipeline...", flush=True)
    
    print("\nStep 1: Collecting image metadata...", flush=True)
    
    subprocess.run(
        [
            sys.executable,
            "-m",
            "src.data_collection.mapillary_search"
        ],
        cwd=ROOT,
        check=True
    )
    
    print("\nStep 2: Downloading images...", flush=True)
    
    subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.download_dataset"
        ],
        cwd=ROOT,
        check=True
    )
    
    print("\nPipeline finished!", flush=True)


if __name__ == "__main__":
    main()
