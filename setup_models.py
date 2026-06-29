"""
setup_models.py
Run this once after cloning: python setup_models.py
Downloads AI model weights from Google Drive automatically.
"""
import os
import sys
import urllib.request
from pathlib import Path


# ── Replace these IDs with your real Google Drive file IDs ──────────────────
MODELS = {
    "unet_weights2.pth":       "https://drive.google.com/file/d/1h-jT0dKaVvrxsPhkCZphHw9I_urkSzdE/view?usp=sharing",
    "best_convnext_4.pth":     "https://drive.google.com/file/d/1CN-2tRfEXQVndU3zb3TDJfctqLZzxkCP/view?usp=sharing",
    "best_convnext_5.pth":     "https://drive.google.com/file/d/1bRk5VhJ0Blh8Khec5UQK05mT42HP5G5x/view?usp=sharing",
    "best_efficientnet_2.pth": "https://drive.google.com/file/d/1DyjR2D8ZMeDXqDggrjnhrv7Iry7PrsCc/view?usp=sharing",
}

WEIGHTS_DIR = Path("models/weights")


def download_file_from_google_drive(file_id: str, dest_path: Path):
    """Download a file from Google Drive by file ID."""
    import requests

    def get_confirm_token(response):
        for key, value in response.cookies.items():
            if key.startswith("download_warning"):
                return value
        return None

    URL = "https://docs.google.com/uc?export=download"
    session = requests.Session()

    print(f"  Connecting to Google Drive...")
    response = session.get(URL, params={"id": file_id}, stream=True)
    token = get_confirm_token(response)

    if token:
        params = {"id": file_id, "confirm": token}
        response = session.get(URL, params=params, stream=True)

    # Download with progress bar
    total = int(response.headers.get("content-length", 0))
    downloaded = 0
    chunk_size = 32768

    with open(dest_path, "wb") as f:
        for chunk in response.iter_content(chunk_size):
            if chunk:
                f.write(chunk)
                downloaded += len(chunk)
                if total:
                    percent = int(downloaded * 100 / total)
                    mb_done = downloaded / 1024 / 1024
                    mb_total = total / 1024 / 1024
                    print(
                        f"\r  Downloading... {percent}% "
                        f"({mb_done:.1f} MB / {mb_total:.1f} MB)",
                        end="", flush=True
                    )
    print()


def setup():
    print("=" * 55)
    print("  OralCancer AI — Model Setup")
    print("=" * 55)
    print()

    # Create weights directory
    WEIGHTS_DIR.mkdir(parents=True, exist_ok=True)

    all_exist = True
    for filename in MODELS:
        if not (WEIGHTS_DIR / filename).exists():
            all_exist = False
            break

    if all_exist:
        print("✅ All model files already exist. Nothing to download.")
        print()
        return

    print("📥 Downloading AI model weights from Google Drive...")
    print("   This only happens once (~418 MB total). Please wait.\n")

    try:
        import requests
    except ImportError:
        print("Installing requests library...")
        os.system(f"{sys.executable} -m pip install requests")
        import requests

    for filename, file_id in MODELS.items():
        dest = WEIGHTS_DIR / filename
        if dest.exists():
            print(f"  ✅ {filename} already exists. Skipping.")
            continue

        print(f"\n📦 Downloading {filename}...")
        try:
            download_file_from_google_drive(file_id, dest)
            size_mb = dest.stat().st_size / 1024 / 1024
            print(f"  ✅ Saved ({size_mb:.1f} MB)")
        except Exception as e:
            print(f"  ❌ Failed to download {filename}: {e}")
            print(f"     Please download manually from Google Drive")
            print(f"     and place in: models/weights/{filename}")

    print()
    print("=" * 55)
    print("  ✅ Setup complete! You can now run: python main.py")
    print("=" * 55)


if __name__ == "__main__":
    setup()