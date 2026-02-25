import pytest
from utils import RunManager
import os
import shutil

def test_run_manager(tmp_path):
    rm = RunManager(base_dir=str(tmp_path / "runs"))
    run_dir = rm.create_run("test_123")
    
    assert run_dir.exists()
    assert run_dir.name == "test_123"
    assert (run_dir / "dev_changes").exists()
    
    rm.save_json(run_dir, "test.json", {"foo": "bar"})
    assert (run_dir / "test.json").exists()
