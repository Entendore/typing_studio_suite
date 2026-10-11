"""Core constants, utilities, and configuration."""
from __future__ import annotations
from collections import OrderedDict
from pathlib import Path
from typing import Dict, FrozenSet, Final, Optional
from contextlib import contextmanager
import logging, os, platform, subprocess, tempfile, shutil, sys
import numpy as np

CWD: Final[Path] = Path.cwd()
INPUT_DIR: Final[Path] = CWD / "input"
OUTPUT_DIR: Final[Path] = CWD / "output"
TEMP_DIR: Final[Path] = CWD / "temp"
SETTINGS_FILE: Final[Path] = CWD / "settings.json"

for _d in (INPUT_DIR, OUTPUT_DIR, TEMP_DIR):
    _d.mkdir(parents=True, exist_ok=True)

SUPPORTED_EXTENSIONS: FrozenSet[str] = frozenset({
    ".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".c", ".cpp", ".h", ".hpp",
    ".cs", ".go", ".rs", ".rb", ".php", ".swift", ".kt", ".sh", ".bash",
    ".zsh", ".sql", ".html", ".htm", ".css", ".scss", ".json", ".yaml",
    ".yml", ".toml", ".ini", ".cfg", ".txt", ".md", ".lua", ".dart", ".r", ".m",
})

SKIP_DIRS: FrozenSet[str] = frozenset({
    ".git", ".hg", ".svn", "__pycache__", "node_modules", ".venv", "venv",
    ".env", ".idea", ".vscode", "dist", "build", ".tox", ".mypy_cache",
    ".pytest_cache", ".next", ".nuxt", "target", "vendor", ".bundle",
})

EXT_TO_LANGUAGE: Dict[str, str] = {
    ".py": "Python", ".js": "JavaScript", ".jsx": "JavaScript", ".ts": "TypeScript", ".tsx": "TypeScript",
    ".java": "Java", ".c": "CFamily", ".cpp": "CFamily", ".h": "CFamily", ".hpp": "CFamily", ".cs": "CSharp",
    ".go": "Go", ".rs": "Rust", ".rb": "Ruby", ".php": "PHP", ".swift": "CFamily", ".kt": "Java",
    ".sh": "Bash", ".bash": "Bash", ".zsh": "Bash", ".sql": "SQL", ".html": "HTML", ".htm": "HTML",
    ".css": "CSS", ".scss": "SCSS", ".json": "JSON", ".yaml": "YAML", ".yml": "YAML",
    ".md": "Markdown", ".txt": "Text", ".lua": "Lua", ".dart": "Dart", ".r": "R", ".m": "MATLAB",
}

AUDIO_SAMPLE_RATE: int = 48000

EXPORT_FORMATS: Dict[str, dict] = {
    "YouTube (16:9)": {
        "resolutions": OrderedDict([("1920x1080", (1920, 1080)), ("1280x720", (1280, 720)), ("3840x2160", (3840, 2160))]),
        "orientation": "landscape",
    },
    "YouTube Shorts (9:16)": {
        "resolutions": OrderedDict([("1080x1920", (1080, 1920)), ("720x1280", (720, 1280))]),
        "orientation": "portrait",
    },
    "Both (YT + Shorts)": {
        "resolutions": OrderedDict([("1920x1080", (1920, 1080)), ("1080x1920", (1080, 1920))]),
        "orientation": "both",
    },
}

ENCODERS: Dict[str, dict] = {
    "YouTube Pro (H.264/AAC)": {
        "base": ["-c:v", "libx264", "-preset", "slow", "-crf", "17", "-profile:v", "high", "-pix_fmt", "yuv420p"],
        "use_dynamic_vbv": True, "use_dynamic_gop": True, "color_tags": True,
    },
    "x264 (CPU, Fast)": {
        "base": ["-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p"],
        "use_dynamic_gop": True, "color_tags": True,
    },
    "NVENC (NVIDIA)": {
        "base": ["-c:v", "h264_nvenc", "-preset", "p5", "-rc", "vbr", "-cq", "19", "-b:v", "0", "-pix_fmt", "yuv420p"],
        "use_dynamic_gop": True, "color_tags": True,
    },
    "QSV (Intel)": {
        "base": ["-c:v", "h264_qsv", "-preset", "medium", "-global_quality", "19", "-pix_fmt", "yuv420p"],
        "use_dynamic_gop": True, "color_tags": True,
    },
    "AMF (AMD)": {
        "base": ["-c:v", "h264_amf", "-preset", "speed", "-rc", "cqp", "-qp_i", "19", "-qp_p", "19", "-pix_fmt", "yuv420p"],
        "use_dynamic_gop": True, "color_tags": True,
    },
}

class StudioError(Exception): pass
class RenderingError(StudioError): pass
class AudioGenerationError(StudioError): pass
class ExportError(StudioError): pass
class FFmpegError(ExportError): pass

log = logging.getLogger("CodeTypingStudio")
log.setLevel(logging.DEBUG)
_fh = logging.FileHandler("studio.log", mode="w", encoding="utf-8")
_fh.setLevel(logging.DEBUG)
_fh.setFormatter(logging.Formatter("%(asctime)s | %(levelname)-7s | %(threadName)-20s | %(message)s", datefmt="%H:%M:%S"))
_sh = logging.StreamHandler()
_sh.setLevel(logging.WARNING)
log.addHandler(_fh); log.addHandler(_sh)

def _format_eta(s: float) -> str:
    if s is None or s < 0 or not np.isfinite(s): return "N/A"
    if s < 1: return "< 1s"
    if s < 60: return f"{int(s)}s"
    m, sc = divmod(int(s), 60)
    if m < 60: return f"{m}m {sc}s"
    h, m = divmod(m, 60)
    return f"{h}h {m}m {sc}s"

def _subprocess_startup_info() -> Optional[subprocess.STARTUPINFO]:
    if platform.system() == "Windows":
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        si.wShowWindow = subprocess.SW_HIDE
        return si
    return None

@contextmanager
def temp_directory(prefix: str = "export_"):
    tmp = tempfile.mkdtemp(dir=str(TEMP_DIR), prefix=prefix)
    try:
        yield tmp
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
