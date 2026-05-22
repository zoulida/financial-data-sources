import re
import shutil
import subprocess
import sys
import tarfile
import urllib.request
import urllib.error
import json
from pathlib import Path
from typing import Callable

from qlib_config import BASE_DIR, DEFAULT_QLIB_PROVIDER_URI, DEFAULT_REGION, check_pyqlib_installed

DownloadEventHandler = Callable[[dict], None]
_PROGRESS_PATTERN = re.compile(r"(\d{1,3})%")
MIRROR_LATEST_RELEASE_API = "https://api.github.com/repos/chenditc/investment_data/releases/latest"
MIRROR_LATEST_DOWNLOAD_URL = "https://github.com/chenditc/investment_data/releases/latest/download/qlib_bin.tar.gz"
MIRROR_ASSET_NAME = "qlib_bin.tar.gz"


def _resolve_mirror_latest_tag() -> str | None:
    request = urllib.request.Request(
        "https://github.com/chenditc/investment_data/releases/latest",
        headers={"User-Agent": "qlib-data-downloader"},
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            final_url = response.geturl().rstrip("/")
    except Exception:
        return None
    marker = "/releases/tag/"
    if marker not in final_url:
        return None
    return final_url.split(marker, 1)[1].strip("/") or None


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


def build_mirror_download_command() -> str:
    script = BASE_DIR / "download_qlib_data.py"
    return subprocess.list2cmdline([sys.executable, str(script), "--source", "mirror"])


def build_local_download_command() -> str:
    script = BASE_DIR / "download_qlib_data.py"
    return subprocess.list2cmdline([sys.executable, str(script)])


def get_mirror_latest_release() -> dict:
    request = urllib.request.Request(MIRROR_LATEST_RELEASE_API, headers={"User-Agent": "qlib-data-downloader"})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        if exc.code == 403:
            tag_name = _resolve_mirror_latest_tag()
            return {
                "tag_name": tag_name,
                "name": tag_name or "latest",
                "published_at": None,
                "asset_name": MIRROR_ASSET_NAME,
                "asset_size": None,
                "download_url": MIRROR_LATEST_DOWNLOAD_URL,
                "html_url": f"https://github.com/chenditc/investment_data/releases/tag/{tag_name}" if tag_name else "https://github.com/chenditc/investment_data/releases/latest",
                "warning": "GitHub API 已限流，使用 latest/download 固定链接下载最新数据",
            }
        raise
    asset = None
    for item in payload.get("assets", []):
        if item.get("name") == MIRROR_ASSET_NAME:
            asset = item
            break
    if not asset:
        raise RuntimeError(f"最新 release 中没有找到 {MIRROR_ASSET_NAME}")
    return {
        "tag_name": payload.get("tag_name"),
        "name": payload.get("name"),
        "published_at": payload.get("published_at"),
        "asset_name": asset.get("name"),
        "asset_size": asset.get("size"),
        "download_url": asset.get("browser_download_url"),
        "html_url": payload.get("html_url"),
    }


def verify_qlib_data(provider_uri: str | Path | None = None) -> dict:
    provider = Path(provider_uri or DEFAULT_QLIB_PROVIDER_URI).resolve()
    calendars_dir = provider / "calendars"
    features_dir = provider / "features"
    instruments_dir = provider / "instruments"
    files_count = 0
    latest_calendar_date = get_latest_calendar_date(provider)
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
        "latest_calendar_date": latest_calendar_date,
        "missing": missing,
        "message": "Qlib 数据下载并校验成功" if ok else "Qlib 数据校验失败，缺少: " + "、".join(missing),
    }


def get_latest_calendar_date(provider_uri: str | Path | None = None, freq: str = "day") -> str | None:
    provider = Path(provider_uri or DEFAULT_QLIB_PROVIDER_URI).resolve()
    calendar_file = provider / "calendars" / f"{freq}.txt"
    if not calendar_file.exists():
        return None
    latest = None
    with calendar_file.open("r", encoding="utf-8", errors="replace") as file:
        for line in file:
            value = line.strip()
            if value:
                latest = value
    return latest


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


def _safe_extract_tar_gz(archive_path: Path, target_dir: Path) -> None:
    target_dir.mkdir(parents=True, exist_ok=True)
    target_root = target_dir.resolve()
    with tarfile.open(archive_path, "r:gz") as tar:
        for member in tar.getmembers():
            member_name = Path(member.name)
            parts = member_name.parts
            relative = Path(*parts[1:]) if len(parts) > 1 else member_name
            if not str(relative) or str(relative) == ".":
                continue
            destination = (target_root / relative).resolve()
            if target_root != destination and target_root not in destination.parents:
                raise RuntimeError(f"压缩包包含非法路径: {member.name}")
            member.name = str(relative).replace("\\", "/")
            tar.extract(member, target_root)


def _download_file_with_progress(url: str, target_path: Path, on_event: DownloadEventHandler | None) -> None:
    request = urllib.request.Request(url, headers={"User-Agent": "qlib-data-downloader"})
    with urllib.request.urlopen(request, timeout=60) as response:
        total = int(response.headers.get("Content-Length") or 0)
        downloaded = 0
        chunk_size = 1024 * 1024
        last_percent = -1
        with target_path.open("wb") as file:
            while True:
                chunk = response.read(chunk_size)
                if not chunk:
                    break
                file.write(chunk)
                downloaded += len(chunk)
                if total > 0:
                    percent = int(downloaded * 100 / total)
                    if percent != last_percent:
                        last_percent = percent
                        mapped = min(85, max(10, 10 + int(percent * 0.75)))
                        _emit(on_event, {"type": "progress", "progress_percent": mapped, "message": f"镜像数据下载中：{percent}%"})
                else:
                    mb = downloaded / 1024 / 1024
                    _emit(on_event, {"type": "progress", "progress_percent": 30, "message": f"镜像数据下载中：{mb:.1f} MB"})


def run_mirror_download(
    provider_uri: str | Path | None = None,
    on_event: DownloadEventHandler | None = None,
    force: bool = False,
) -> dict:
    provider = Path(provider_uri or DEFAULT_QLIB_PROVIDER_URI).resolve()
    _emit(on_event, {"type": "progress", "progress_percent": 0, "message": "准备读取 investment_data 最新 release"})
    release = get_mirror_latest_release()
    existing = verify_qlib_data(provider)

    if existing["ok"] and release.get("tag_name") and existing.get("latest_calendar_date") == release.get("tag_name") and not force:
        result = {
            "success": True,
            "return_code": 0,
            "command": build_mirror_download_command(),
            "provider_uri": str(provider),
            "progress_percent": 100,
            "message": f"本地数据已是镜像最新日期 {release.get('tag_name')}，无需重复下载",
            "verify": existing,
            "release": release,
        }
        _emit(on_event, {"type": "progress", "progress_percent": 100, "message": "本地数据已是最新"})
        _emit(on_event, {"type": "result", **result})
        return result

    if force and provider.exists():
        _emit(on_event, {"type": "progress", "progress_percent": 5, "message": "强制更新：正在删除旧数据目录"})
        shutil.rmtree(provider)
        _emit(on_event, {"type": "output", "line": f"已删除旧数据目录: {provider}"})

    provider.parent.mkdir(parents=True, exist_ok=True)
    archive_path = provider.parent / MIRROR_ASSET_NAME
    _emit(on_event, {"type": "output", "line": f"镜像 release: {release.get('html_url')}"})
    _emit(on_event, {"type": "output", "line": f"镜像数据包: {release.get('download_url')}"})
    _emit(on_event, {"type": "output", "line": f"数据包大小: {release.get('asset_size')} bytes"})
    _download_file_with_progress(release["download_url"], archive_path, on_event)

    if provider.exists():
        _emit(on_event, {"type": "progress", "progress_percent": 86, "message": "正在清理旧数据目录"})
        shutil.rmtree(provider)
    provider.mkdir(parents=True, exist_ok=True)
    _emit(on_event, {"type": "progress", "progress_percent": 90, "message": "正在解压镜像数据包"})
    _safe_extract_tar_gz(archive_path, provider)
    try:
        archive_path.unlink()
    except Exception:
        pass

    _emit(on_event, {"type": "progress", "progress_percent": 96, "message": "正在校验镜像数据"})
    verify = verify_qlib_data(provider)
    success = verify["ok"]
    message = f"镜像数据下载成功，最新日期: {verify.get('latest_calendar_date')}" if success else f"镜像数据下载失败：{verify['message']}"
    result = {
        "success": success,
        "return_code": 0 if success else 1,
        "command": build_mirror_download_command(),
        "provider_uri": str(provider),
        "progress_percent": 100,
        "message": message,
        "verify": verify,
        "release": release,
    }
    _emit(on_event, {"type": "result", **result})
    return result


def run_qlib_download(
    provider_uri: str | Path | None = None,
    region: str = DEFAULT_REGION,
    on_event: DownloadEventHandler | None = None,
    force: bool = False,
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

    existing = verify_qlib_data(provider)
    if existing["ok"] and not force:
        result = {
            "success": True,
            "return_code": 0,
            "command": command,
            "provider_uri": str(provider),
            "progress_percent": 100,
            "message": "Qlib 数据已存在且校验通过，无需重复下载",
            "verify": existing,
        }
        _emit(on_event, {"type": "progress", "progress_percent": 100, "message": "数据已存在，校验通过"})
        _emit(on_event, {"type": "result", **result})
        return result

    if force and provider.exists():
        _emit(on_event, {"type": "progress", "progress_percent": 5, "message": "强制更新：正在删除旧数据目录"})
        shutil.rmtree(provider)
        _emit(on_event, {"type": "output", "line": f"已删除旧数据目录: {provider}"})

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
