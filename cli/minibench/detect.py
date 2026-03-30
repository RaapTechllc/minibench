"""Auto-detect hardware specifications."""
import platform
import subprocess
import re
from typing import Optional

import psutil


def detect_cpu() -> dict:
    """Detect CPU model, cores, threads."""
    info = {
        "cpu_model": platform.processor() or "Unknown",
        "cpu_cores": psutil.cpu_count(logical=False),
        "cpu_threads": psutil.cpu_count(logical=True),
    }

    system = platform.system()

    if system == "Darwin":
        try:
            result = subprocess.run(
                ["sysctl", "-n", "machdep.cpu.brand_string"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0 and result.stdout.strip():
                info["cpu_model"] = result.stdout.strip()
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
    elif system == "Linux":
        try:
            with open("/proc/cpuinfo") as f:
                for line in f:
                    if line.startswith("model name"):
                        info["cpu_model"] = line.split(":")[1].strip()
                        break
        except (FileNotFoundError, PermissionError):
            pass

    return info


def detect_ram() -> dict:
    """Detect total system RAM."""
    mem = psutil.virtual_memory()
    total_gb = round(mem.total / (1024 ** 3), 1)
    return {"total_ram_gb": total_gb}


def detect_gpu() -> dict:
    """Detect GPU model and VRAM."""
    info: dict = {"gpu_model": None, "igpu_model": None, "vram_gb": None}
    system = platform.system()

    # Try nvidia-smi for discrete GPU
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0 and result.stdout.strip():
            parts = result.stdout.strip().split(",")
            info["gpu_model"] = parts[0].strip()
            if len(parts) > 1:
                vram_mb = float(parts[1].strip())
                info["vram_gb"] = round(vram_mb / 1024, 1)
            return info
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    # macOS: system_profiler
    if system == "Darwin":
        try:
            result = subprocess.run(
                ["system_profiler", "SPDisplaysDataType"],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                for line in result.stdout.split("\n"):
                    if "Chipset Model" in line or "Chip Model" in line:
                        info["igpu_model"] = line.split(":")[1].strip()
                        break
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
    elif system == "Linux":
        # Try lspci
        try:
            result = subprocess.run(
                ["lspci"], capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                for line in result.stdout.split("\n"):
                    if "VGA" in line or "3D" in line:
                        # Extract model after the colon
                        match = re.search(r":\s+(.+)$", line)
                        if match:
                            gpu_name = match.group(1).strip()
                            if "NVIDIA" in gpu_name.upper():
                                info["gpu_model"] = gpu_name
                            else:
                                info["igpu_model"] = gpu_name
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

    return info


def detect_os() -> str:
    """Detect operating system."""
    system = platform.system()
    release = platform.release()

    if system == "Darwin":
        try:
            result = subprocess.run(
                ["sw_vers", "-productVersion"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                return f"macOS {result.stdout.strip()}"
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        return f"macOS {release}"
    elif system == "Linux":
        try:
            with open("/etc/os-release") as f:
                for line in f:
                    if line.startswith("PRETTY_NAME="):
                        return line.split("=")[1].strip().strip('"')
        except FileNotFoundError:
            pass
        return f"Linux {release}"
    elif system == "Windows":
        return f"Windows {platform.version()}"
    return f"{system} {release}"


def detect_memory_type() -> Optional[str]:
    """Best-effort memory type detection."""
    system = platform.system()

    if system == "Darwin":
        # Apple Silicon uses unified memory — LPDDR for M-series
        try:
            result = subprocess.run(
                ["sysctl", "-n", "hw.memsize"],
                capture_output=True, text=True, timeout=5
            )
            cpu = platform.processor()
            if "arm" in cpu.lower() or "apple" in cpu.lower():
                return "Unified"
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
    elif system == "Linux":
        try:
            result = subprocess.run(
                ["dmidecode", "-t", "memory"],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                for line in result.stdout.split("\n"):
                    if "Type:" in line and "DDR" in line:
                        return line.split(":")[1].strip()
        except (subprocess.TimeoutExpired, FileNotFoundError, PermissionError):
            pass

    return None


def detect_all() -> dict:
    """Run all detection and return combined dict."""
    hw = {}
    hw.update(detect_cpu())
    hw.update(detect_ram())
    hw.update(detect_gpu())
    hw["os"] = detect_os()
    hw["memory_type"] = detect_memory_type()
    return hw
