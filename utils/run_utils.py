import os
import json
from datetime import datetime
from pathlib import Path

class RunManager:
    def __init__(self, base_dir: str = "runs"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(exist_ok=True)
        
    def create_run(self, run_id: str = None) -> Path:
        if not run_id:
            run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        run_dir = self.base_dir / run_id
        run_dir.mkdir(exist_ok=True)
        (run_dir / "dev_changes").mkdir(exist_ok=True)
        return run_dir
        
    def save_json(self, run_dir: Path, filename: str, data: dict):
        with open(run_dir / filename, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
