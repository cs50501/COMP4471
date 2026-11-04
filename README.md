# COMP4471/ELEC4240 Project
A repository for the COMP4471/ELEC4240 Project


## Project Overview

This project aims to predict the geographical district of any given street-level image of Hong Kong, using deep learning.

The dataset contains thousands of images in each of Hong Kong's 18 districts.

The intended modelling approach involves fine-tuning the pretrained computer vision models such as ResNet or Vision Transformers.


## Project Structure

- `data/boundaries/`
  - GeoJSON district boundaries for Hong Kong.

- `data/metadata/`
  - `images.csv`: Image IDs, coordinates, district labels,
    Mapillary sequence IDs and capture timestamps.
  - `search_progress.csv`: Records processed geographic cells.

- `data/raw/`
  - Downloaded JPEG images, organized by district.

- `src/preprocessing/district_classifier.py`
  - Determines the administrative district from GPS coordinates.

- `src/data_collection/mapillary_search.py`
  - Searches Mapillary using geographic grid cells.
  - Subdivides dense areas and filters images by district.
  - Saves metadata and tracks search progress.

- `scripts/download_dataset.py`
  - Downloads images using the metadata CSV.
  - Skips existing images and retries failed requests.
  - Targets up to 3,000 images per district.

- `scripts/run_pipeline.py`
  - Runs metadata collection followed by image downloading.


## Setup

1. Clone the repository

2. Install python dependencies

    pip install -r requirements.txt


## Running the project pipeline

Run the complete pipeline:

    python -m scripts.run_pipeline

Alternatively, run each stage separately


### Stage 1: Metadata Collection

    python -m src.data_collection.mapillary_search

Discovers image IDs and geographic metadata for the 18
Hong Kong districts.


### Stage 2: Image Downloading

    python -m scripts.download_dataset

Downloads JPEG images into district-specific folders.


## Dataset Targets

- 18 administrative districts
- Up to 6000 metadata candidates per district
- Up to 3000 downloaded images per district
- Target dataset size: approximately 54000 images

Actual counts depend on image availability and download success.


## Notes

- Already downloaded images are skipped on subsequent runs.
- Previously processed geographic grid cells are tracked.
- Mapillary search coverage is best-effort, not exhaustive.
- Geographic and sequence diversity should be considered
  when preparing training and testing datasets.
- Raw images are distributed separately from the GitHub repository.


## Data Sources

- Mapillary street-level imagery
- Hong Kong government district boundary data

Dataset redistribution and attribution must follow the
applicable source licensing requirements.