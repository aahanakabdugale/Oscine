"""
Oscine Dataset Downloader & Integrity Verifier
Automates downloading, unpacking, and verifying the 60-clip contrastive speech dataset.
"""

import os
import sys
import zipfile
import urllib.request

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATASET_DIR = os.path.join(PROJECT_ROOT, "dataset")

# Placeholder URL for public cloud mirror (Google Drive direct link or Hugging Face repository zip)
DATASET_MIRROR_URL = os.getenv(
    "OSCINE_DATASET_URL",
    "https://drive.google.com/uc?export=download&id=YOUR_GOOGLE_DRIVE_FILE_ID"
)

EXPECTED_SPEAKERS = [f"speech_0{i}" for i in range(1, 7)]


def check_existing_dataset() -> bool:
    """Verifies if the dataset is already present locally with all 60 audio files."""
    if not os.path.exists(DATASET_DIR):
        return False

    wav_count = 0
    for root, _, files in os.walk(DATASET_DIR):
        for f in files:
            if f.endswith(".wav"):
                wav_count += 1

    return wav_count >= 60


def download_and_extract(url: str = DATASET_MIRROR_URL, target_dir: str = DATASET_DIR):
    """Downloads dataset zip archive from public cloud mirror and extracts to target_dir."""
    os.makedirs(target_dir, exist_ok=True)
    zip_path = os.path.join(PROJECT_ROOT, "oscine_dataset.zip")

    print("========================================================")
    print("           OSCINE DATASET MIRROR DOWNLOADER             ")
    print("========================================================")

    if check_existing_dataset() and "--force" not in sys.argv:
        print("[OK] Dataset already present locally with all 60 audio files in:")
        print(f"     {DATASET_DIR}")
        print("     To force re-download, pass --force.")
        return

    print(f"[*] Downloading dataset archive from:\n    {url}")
    print(f"[*] Destination: {zip_path}")

    def progress_hook(block_num, block_size, total_size):
        downloaded = block_num * block_size
        if total_size > 0:
            pct = min(100.0, (downloaded / total_size) * 100.0)
            mb = downloaded / (1024 * 1024)
            total_mb = total_size / (1024 * 1024)
            sys.stdout.write(f"\r    Progress: {pct:.1f}% ({mb:.1f} MB / {total_mb:.1f} MB)")
        else:
            sys.stdout.write(f"\r    Downloaded: {downloaded / (1024 * 1024):.1f} MB")
        sys.stdout.flush()

    try:
        urllib.request.urlretrieve(url, zip_path, reporthook=progress_hook)
        print("\n[OK] Download complete. Extracting archive...")

        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(DATASET_DIR)

        print(f"[OK] Extracted dataset to: {DATASET_DIR}")

        # Clean up temporary zip
        if os.path.exists(zip_path):
            os.remove(zip_path)

    except Exception as exc:
        print(f"\n[ERROR] Failed to download dataset archive: {exc}")
        print("\nAlternative: The dataset is available directly in this git repo under ./dataset/.")
        print("You can also download manually from the Google Drive mirror link in README.md.")
        return

    # Run verification
    from verify_labels import verify_and_calibrate_labels
    verify_and_calibrate_labels()


if __name__ == "__main__":
    download_and_extract()
