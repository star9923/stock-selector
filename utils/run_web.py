"""Run the Flask web app with Windows-friendly console encoding."""
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

for stream in (sys.stdout, sys.stderr):
    try:
        stream.reconfigure(encoding="utf-8")
    except Exception:
        pass

import app


if __name__ == "__main__":
    app.history_service.init_db()
    app.clean_old_exports(days=7)
    app.app.run(host="0.0.0.0", port=5001, debug=False)
