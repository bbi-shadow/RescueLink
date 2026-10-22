"""Local development only: SQLite and loopback API, behind the Vite proxy."""
from pathlib import Path
import os
import sys

root = Path(__file__).resolve().parents[1]
path = root / ".env"
if not path.exists():
    sys.exit("Chạy python scripts/setup.py trước.")
for line in path.read_text().splitlines():
    if "=" in line and not line.startswith("#"):
        name, value = line.split("=",1)
        os.environ.setdefault(name, value)
os.environ.setdefault("DATABASE_URL", "sqlite:///" + str(root / "dev-rescue.db"))
sys.path.insert(0, str(root / "backend"))
import uvicorn
uvicorn.run("app.main:create_app", factory=True, host="127.0.0.1", port=8000)
