import re
import subprocess
import sys
from pathlib import Path
from typing import Callable

from qlib_config import BASE_DIR, DEFAULT_QLIB_PROVIDER_URI, DEFAULT_REGION, check_pyqlib_installed

DownloadEventHandler = Callable[[dict], None]
_PROGRESS_PATTERN = re.compile(r"(\d{1,3})%")


def build_official_download_args(provider_uri: str | Path | None = None, region: str = DEFAULT_REGION) -> list[str]:
    target_dir = Path(provider_uri or DEFAULT_QLIB_PROVIDER_URI).resolve()
    script = BASE_DIR / "scripts" / "get_data.py"
    return [
        sys.executable,
        "-u",
        str(script),
        "qlib_data",
        "--target_dir",
        str(target_dir),
        "--region",
        region,
    ]


def build_official_download_command(provider_uri: str | Path | None = None, region: str = DEFAULT_REGION) -> str:
    return subprocess.list2cmdline(build_official_download_args(provider_uri, region))


def build_local_download_command() -> str:
    script = BASE_DIR / "download_qlib_data.py"
    return subprocess.list2cmdline([sys.executable, str(script)])


def verify_qlib_data(provider_uri: str | Path | None = None) -> dict:
    provider = Path(provider_uri or DEFAULT_QLIB_PROVIDER_URI).resolve()
    calendars_dir = provider / "calendars"
    features_dir = provider / "features"
    instruments_dir = provider / "instruments"
    files_count = 0
    if provider.exists():
        files_count = sum(1 for item in provider.rglob("*") if item.is_file())
    ok = provider.exists() and calendars_dir.exists() and features_dir.exists() and instruments_dir.exists() and files_count > 0
    missing = []
    if not provider.exists():
        missing.append("数据根目录")
    if not calendars_dir.exists():
        missing.append("calendars")
    if not features_dir.exists():
        missing.append("features")
    if not instruments_dir.exists():
        missing.append("instruments")
    if files_count <= 0:
        missing.append("数据文件")
    return {
        "ok": ok,
        "provider_uri": str(provider),
        "files_count": files_count,
        "missing": missing,
        "message": "Qlib 数据下载并校验成功" if ok else "Qlib 数据校验失败，缺少: " + "、".join(missing),
    }


def _emit(handler: DownloadEventHandler | None, event: dict) -> None:
    if handler:
        handler(event)


def _progress_from_line(line: str) -> int | None:
    values = []
    for match in _PROGRESS_PATTERN.findall(line):
        value = int(match)
        if 0 <= value <= 100:
            values.append(value)
    if not values:
        return None
    return max(values)


def _stage_progress(line: str, current_progress: int) -> tuple[int, str] | None:
    lower = line.lower()
    percent = _progress_from_line(line)
    if percent is not None:
        mapped = min(92, max(10, 10 + int(percent * 0.82)))
        return max(current_progress, mapped), f"下载中：{percent}%"
    if any(word in lower for word in ["download", "downloading", "开始下载", "下载"]):
        return max(current_progress, 20), "正在下载数据包"
    if any(word in lower for word in ["extract", "unzip", "decompress", "解压"]):
        return max(current_progress, 82), "正在解压数据包"
    if any(word in lower for word in ["finish", "finished", "complete", "completed", "完成"]):
        return max(current_progress, 92), "下载命令已完成，准备校验"
    return None


def run_qlib_download(
    provider_uri: str | Path | None = None,
    region: str = DEFAULT_REGION,
    on_event: DownloadEventHandler | None = None,
) -> dict:
    provider = Path(provider_uri or DEFAULT_QLIB_PROVIDER_URI).resolve()
    command = build_official_download_command(provider, region)
    progress = 0
    _emit(on_event, {"type": "progress", "progress_percent": progress, "message": "准备检查 pyqlib 环境"})

    installed, install_message = check_pyqlib_installed()
    if not installed:
        result = {
            "success": False,
            "return_code": -1,
            "command": command,
            "provider_uri": str(provider),
            "progress_percent": 100,
            "message": f"下载失败：未安装 pyqlib。请先执行 pip install pyqlib。原始错误: {install_message}",
            "verify": verify_qlib_data(provider),
        }
        _emit(on_event, {"type": "result", **result})
        return result

    provider.parent.mkdir(parents=True, exist_ok=True)
    progress = 8
    _emit(on_event, {"type": "progress", "progress_percent": progress, "message": "环境检查通过，准备启动下载命令"})
    _emit(on_event, {"type": "output", "line": f"下载命令: {command}"})

    try:
        process = subprocess.Popen(
            build_official_download_args(provider, region),
            cwd=str(BASE_DIR),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )
    except Exception as exc:
        result = {
            "success": False,
            "return_code": -1,
            "command": command,
            "provider_uri": str(provider),
            "progress_percent": 100,
            "message": f"下载命令启动失败: {exc}",
            "verify": verify_qlib_data(provider),
        }
        _emit(on_event, {"type": "result", **result})
        return result

    progress = 12
    _emit(on_event, {"type": "progress", "progress_percent": progress, "message": "下载命令已启动"})

    buffer: list[str] = []
    assert process.stdout is not None
    while True:
        char = process.stdout.read(1)
        if char == "" and process.poll() is not None:
            break
        if char == "":
            continue
        if char in "\r\n":
            line = "".join(buffer).strip()
            buffer.clear()
            if not line:
                continue
            _emit(on_event, {"type": "output", "line": line})
            stage = _stage_progress(line, progress)
            if stage:
                progress, message = stage
                _emit(on_event, {"type": "progress", "progress_percent": progress, "message": message})
        else:
            buffer.append(char)

    if buffer:
        line = "".join(buffer).strip()
        _emit(on_event, {"type": "output", "line": line})
        stage = _stage_progress(line, progress)
        if stage:
            progress, message = stage
            _emit(on_event, {"type": "progress", "progress_percent": progress, "message": message})

    return_code = process.wait()
    _emit(on_event, {"type": "progress", "progress_percent": 95, "message": "下载命令结束，正在校验数据目录"})
    verify = verify_qlib_data(provider)
    success = return_code == 0 and verify["ok"]
    message = "下载成功，Qlib 数据目录校验通过" if success else f"下载失败或数据不完整。退出码: {return_code}；{verify['message']}"
    result = {
        "success": success,
        "return_code": return_code,
        "command": command,
        "provider_uri": str(provider),
        "progress_percent": 100,
        "message": message,
        "verify": verify,
    }
    _emit(on_event, {"type": "result", **result})
    return result
