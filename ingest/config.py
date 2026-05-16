import os
from pathlib import Path

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://sanskrit:sanskrit@localhost:5433/sanskrit")
MAX_WORKERS = int(os.environ.get("MAX_WORKERS", "6"))
DATA_DIR = Path(os.environ.get("DATA_DIR", "/data"))
REQUEST_TIMEOUT = 60
CLONE_DEPTH = 1
RATE_LIMIT_SLEEP = 2.0
BATCH_SIZE = 2000
