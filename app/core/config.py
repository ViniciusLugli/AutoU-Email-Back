from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]

DATA_DIR = BASE_DIR / "data"

if not DATA_DIR.exists():
    DATA_DIR.mkdir(parents=True)

def get_data_dir() -> Path:
    return DATA_DIR