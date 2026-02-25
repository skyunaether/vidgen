import subprocess
from typing import List, Optional

class GitManager:
    def __init__(self, repo_path: str = "."):
        self.repo_path = repo_path

    def _run(self, cmd: List[str]) -> str:
        res = subprocess.run(cmd, cwd=self.repo_path, capture_output=True, text=True)
        if res.returncode != 0:
            raise RuntimeError(f"Git command {' '.join(cmd)} failed: {res.stderr}")
        return res.stdout.strip()

    def create_branch(self, branch_name: str, checkout: bool = True):
        args = ["git", "checkout", "-b"] if checkout else ["git", "branch"]
        self._run(args + [branch_name])

    def commit(self, message: str, files: List[str]) -> str:
        self._run(["git", "add"] + files)
        self._run(["git", "commit", "-m", message])
        return self._run(["git", "rev-parse", "HEAD"])

    def current_branch(self) -> str:
        return self._run(["git", "branch", "--show-current"])
