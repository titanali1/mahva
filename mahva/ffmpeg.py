"""Thin ffmpeg wrapper: process runner, filter-graph helper and step builders."""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import time
import wave
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable, Sequence

LOG_TAIL = 40
_DURATION_RE = re.compile(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)")


def find_ffmpeg() -> str:
    """Locate a usable ffmpeg binary (env override -> PATH -> bundled wheel)."""
    env = os.environ.get("FFMPEG") or os.environ.get("FFMPEG_BINARY")
    if env and Path(env).exists():
        return env
    which = shutil.which("ffmpeg")
    if which:
        return which
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception as exc:  # pragma: no cover
        raise RuntimeError(
            "ffmpeg پیدا نشد. یا ffmpeg را نصب کنید یا بستهٔ imageio-ffmpeg را نصب کنید."
        ) from exc


ProgressFn = Callable[[float, str], None]
LogFn = Callable[[str], None]
CancelFn = Callable[[], bool]


class Cancelled(RuntimeError):
    pass


@dataclass
class FFmpeg:
    exe: str = field(default_factory=find_ffmpeg)
    threads: int = max(1, (os.cpu_count() or 2) - 1)

    def probe_duration(self, path: str | os.PathLike[str]) -> float:
        return probe_duration(path, self.exe)

    def run(self, args: Sequence[str], *, total: float | None = None, step: str = "render",
            on_progress: ProgressFn | None = None, log: LogFn | None = None,
            cancel: CancelFn | None = None) -> None:
        cmd = [self.exe, "-hide_banner", "-nostdin", "-y", "-loglevel", "error",
               "-progress", "pipe:1", "-nostats", *args]
        if log:
            log(f"[{step}] {' '.join(_short(c) for c in cmd)}")
        proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            universal_newlines=True, bufsize=1, start_new_session=True,
        )
        tail: list[str] = []
        try:
            assert proc.stdout is not None
            for line in proc.stdout:
                line = line.strip()
                if line.startswith("out_time_us=") or line.startswith("out_time_ms="):
                    try:
                        value = float(line.split("=", 1)[1])
                    except ValueError:
                        continue
                    seconds = value / 1_000_000 if line.startswith("out_time_us=") else value / 1_000_000
                    if total and on_progress:
                        on_progress(min(0.999, max(0.0, seconds / total)), step)
                elif line.startswith("progress=end") and on_progress:
                    on_progress(1.0, step)
                if cancel and cancel():
                    proc.terminate()
                    raise Cancelled(f"کار در مرحلهٔ {step} لغو شد")
            assert proc.stderr is not None
            for line in proc.stderr:
                tail.append(line.rstrip())
                if len(tail) > LOG_TAIL:
                    tail.pop(0)
        finally:
            if proc.poll() is None:
                proc.wait()
        if proc.returncode != 0:
            detail = "\n".join(tail[-12:])
            raise RuntimeError(f"ffmpeg در مرحلهٔ «{step}» خطا داد (کد {proc.returncode}):\n{detail}")


def _short(token: str) -> str:
    if len(token) > 220 and ("," in token and "filter" in token.lower() or "=" in token and ";" in token):
        return token[:200] + "…"
    return token


def probe_duration(path: str | os.PathLike[str], exe: str | None = None) -> float:
    p = Path(path)
    if p.suffix.lower() == ".wav":
        try:
            with wave.open(str(p), "rb") as f:
                frames = f.getnframes()
                rate = f.getframerate() or 1
                return frames / float(rate)
        except Exception:
            pass
    exe = exe or find_ffmpeg()
    try:
        proc = subprocess.run([exe, "-hide_banner", "-i", str(p)], capture_output=True, text=True)
        m = _DURATION_RE.search(proc.stderr or "")
        if m:
            h, mnt, sec = int(m.group(1)), int(m.group(2)), float(m.group(3))
            return h * 3600 + mnt * 60 + sec
    except Exception:
        pass
    return 0.0


class Graph:
    """Helper that keeps input indices and filter labels straight."""

    def __init__(self) -> None:
        self.inputs: list[list[str]] = []
        self.filters: list[str] = []
        self._counter = 0

    def add_input(self, args: Iterable[str]) -> int:
        self.inputs.append(list(args))
        return len(self.inputs) - 1

    def new_label(self, prefix: str) -> str:
        self._counter += 1
        return f"{prefix}{self._counter}"

    def add(self, *filters: str) -> None:
        for f in filters:
            if f:
                self.filters.append(f.strip())

    def chain(self, source: str, *filters: str, out: str | None = None) -> str:
        label = out or self.new_label("v")
        self.add("".join(f"[{source}]") + ",".join(filters) + f"[{label}]")
        return label

    def filter_complex(self) -> str:
        return ";".join(self.filters)

    def args(self) -> list[str]:
        out: list[str] = []
        for i in self.inputs:
            out += i
        if self.filters:
            out += ["-filter_complex", self.filter_complex()]
        return out


def xfade_pair(a: str, b: str, transition: str, duration: float, offset: float, out: str) -> str:
    return (f"[{a}][{b}]xfade=transition={transition}:duration={duration:.3f}"
            f":offset={offset:.3f}[{out}]")


def escape_path(path: str) -> str:
    """Escape a path for use inside a filtergraph (subtitles, movie=)."""
    return path.replace("\\", "/").replace(":", "\\:").replace("'", "\\'")


def concat_files(paths: Sequence[str | os.PathLike[str]], out: Path) -> Path:
    """Write an ffmpeg concat demuxer list."""
    lines = []
    for p in paths:
        safe = str(p).replace("'", "'\\''")
        lines.append(f"file '{safe}'")
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


def wait_for_file(path: Path, timeout: float = 5.0, min_bytes: int = 1) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if path.exists() and path.stat().st_size >= min_bytes:
            return True
        time.sleep(0.05)
    return path.exists() and path.stat().st_size >= min_bytes


def platform_exe(name: str) -> str | None:
    return shutil.which(name)


def log_environment(log: LogFn | None = None) -> dict[str, str]:
    info = {
        "ffmpeg": find_ffmpeg(),
        "python": sys.version.split()[0],
        "platform": sys.platform,
        "cpu": str(os.cpu_count() or 1),
    }
    if log:
        log(" · ".join(f"{k}={v}" for k, v in info.items()))
    return info
