"""Environment checks for the ``tabgen doctor`` command.

Pure functions only: no printing, no CLI framework. Each check returns a
:class:`CheckResult`; :func:`run_checks` aggregates them into a report that
the CLI layer renders.
"""

from __future__ import annotations

import shutil
import sys
from dataclasses import asdict, dataclass, field

#: Approximate disk space needed for the model weights, in bytes (~4 GB).
REQUIRED_DISK_BYTES = 4 * 1024**3

#: Supported Python versions (inclusive range of minor versions on 3.x).
MIN_PYTHON = (3, 10)
MAX_PYTHON = (3, 11)


@dataclass
class CheckResult:
    """Outcome of a single environment check."""

    name: str
    ok: bool
    essential: bool
    detail: str
    data: dict = field(default_factory=dict)


@dataclass
class DoctorReport:
    """Aggregated outcome of all environment checks."""

    checks: list[CheckResult]

    @property
    def ok(self) -> bool:
        """True when every essential check passed."""
        return all(check.ok for check in self.checks if check.essential)

    def to_dict(self) -> dict:
        return {"ok": self.ok, "checks": [asdict(check) for check in self.checks]}


def check_ffmpeg() -> CheckResult:
    """Check that the ffmpeg binary is available on PATH."""
    path = shutil.which("ffmpeg")
    if path:
        return CheckResult(
            name="ffmpeg",
            ok=True,
            essential=True,
            detail=f"found at {path}",
            data={"path": path},
        )
    return CheckResult(
        name="ffmpeg",
        ok=False,
        essential=True,
        detail="not found on PATH (install ffmpeg)",
    )


def check_python_version() -> CheckResult:
    """Check that the running Python is within the supported range."""
    version = sys.version_info[:3]
    ok = MIN_PYTHON <= version[:2] <= MAX_PYTHON
    version_str = ".".join(str(part) for part in version)
    wanted = f"{MIN_PYTHON[0]}.{MIN_PYTHON[1]}-{MAX_PYTHON[0]}.{MAX_PYTHON[1]}"
    detail = f"{version_str} (supported: {wanted})"
    return CheckResult(
        name="python",
        ok=ok,
        essential=True,
        detail=detail,
        data={"version": version_str},
    )


def check_torch_cuda() -> CheckResult:
    """Check that PyTorch is installed and CUDA is available."""
    try:
        import torch
    except ImportError:
        return CheckResult(
            name="torch+cuda",
            ok=False,
            essential=True,
            detail="PyTorch is not installed (pip install torch)",
        )

    torch_version = getattr(torch, "__version__", "unknown")
    if not torch.cuda.is_available():
        return CheckResult(
            name="torch+cuda",
            ok=False,
            essential=True,
            detail=f"PyTorch {torch_version} installed but CUDA is not available",
            data={"torch_version": torch_version, "cuda_available": False},
        )

    device = torch.cuda.current_device()
    gpu_name = torch.cuda.get_device_name(device)
    vram_bytes = torch.cuda.get_device_properties(device).total_memory
    vram_gb = vram_bytes / 1024**3
    return CheckResult(
        name="torch+cuda",
        ok=True,
        essential=True,
        detail=f"PyTorch {torch_version}, CUDA on {gpu_name} ({vram_gb:.1f} GB VRAM)",
        data={
            "torch_version": torch_version,
            "cuda_available": True,
            "gpu_name": gpu_name,
            "vram_bytes": vram_bytes,
        },
    )


def check_disk_space(
    path: str = ".", required_bytes: int = REQUIRED_DISK_BYTES
) -> CheckResult:
    """Check that there is enough free disk space for the model weights."""
    usage = shutil.disk_usage(path)
    free_gb = usage.free / 1024**3
    required_gb = required_bytes / 1024**3
    ok = usage.free >= required_bytes
    return CheckResult(
        name="disk space",
        ok=ok,
        essential=True,
        detail=f"{free_gb:.1f} GB free (need ~{required_gb:.0f} GB for model weights)",
        data={"free_bytes": usage.free, "required_bytes": required_bytes},
    )


def run_checks() -> DoctorReport:
    """Run every environment check and aggregate the results."""
    return DoctorReport(
        checks=[
            check_ffmpeg(),
            check_python_version(),
            check_torch_cuda(),
            check_disk_space(),
        ]
    )
