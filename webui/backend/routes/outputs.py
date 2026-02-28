"""Output file listing and download routes."""
from __future__ import annotations

from pathlib import Path

from litestar import get
from litestar.exceptions import NotFoundException
from litestar.response import File

from webui.backend.models import OutputFile


@get("/api/outputs/download")
async def download_output(path: str) -> File:
    """Stream an output file for download (path passed as query param)."""
    p = Path(path)
    if not p.exists() or not p.suffix == ".mp4":
        raise NotFoundException(f"File not found: {path}")
    return File(path=p, filename=p.name, media_type="video/mp4")


@get("/api/outputs")
async def list_outputs() -> list[OutputFile]:
    """List all generated MP4 files in the configured output directory."""
    from vidgen.config import Config
    cfg = Config.load()
    output_dir = Path(cfg.output_dir)
    if not output_dir.exists():
        return []

    files = sorted(output_dir.glob("*.mp4"), key=lambda p: p.stat().st_ctime, reverse=True)
    result = []
    for f in files:
        stat = f.stat()
        result.append(OutputFile(
            name=f.name,
            path=str(f),
            size_bytes=stat.st_size,
            created_at=stat.st_ctime,
        ))
    return result
