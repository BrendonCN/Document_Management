from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "app.db"
STORAGE_DIR = DATA_DIR / "storage"

SECRET_KEY = "dev-document-management-secret-change-in-production"
SESSION_COOKIE = "dm_session"
SESSION_MAX_AGE = 60 * 60 * 24 * 7  # 7 days

# Ensure data directories exist at import time for local runs
DATA_DIR.mkdir(parents=True, exist_ok=True)
STORAGE_DIR.mkdir(parents=True, exist_ok=True)
