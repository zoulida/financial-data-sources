import json
import subprocess
import sys
import threading
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from qlib_config import LOG_DIR, get_data_status
from qlib_downloader import build_local_download_command, build_official_download_command, run_qlib_download


@dataclass
class TaskInfo:
    task_id: str
    name: str
    command: str
    status: str
    return_code: int | None
    started_at: str | None
    finished_at: str | None
    log_file: str
    task_type: str = "command"
    progress_percent: int = 0
    progress_text: str = "等待开始"
    success: bool | None = None
    result_message: str = ""
    provider_uri: str = ""
    verify: dict = field(default_factory=dict)


_TASKS: dict[str, TaskInfo] = {}
_TASK_LOCK = threading.Lock()


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def list_tasks() -> list[dict]:
    with _TASK_LOCK:
        return [asdict(item) for item in sorted(_TASKS.values(), key=lambda x: x.started_at or "", reverse=True)]


def get_task(task_id: str) -> dict | None:
    with _TASK_LOCK:
        task = _TASKS.get(task_id)
        return asdict(task) if task else None


def read_task_log(task_id: str) -> str:
    task = get_task(task_id)
    if not task:
        return "任务不存在"
    log_file = Path(task["log_file"])
    if not log_file.exists():
        return "日志文件不存在"
    return log_file.read_text(encoding="utf-8", errors="replace")


def get_download_command() -> dict:
    return {
        "local_command": build_local_download_command(),
        "official_command": build_official_download_command(),
    }


def _set_task_fields(task_id: str, **kwargs) -> None:
    with _TASK_LOCK:
        task = _TASKS[task_id]
        for key, value in kwargs.items():
            setattr(task, key, value)


def _append_log(log_file: Path, text: str) -> None:
    with log_file.open("a", encoding="utf-8", errors="replace") as log:
        log.write(text)
        if not text.endswith("\n"):
            log.write("\n")
        log.flush()


def _run_task(task_id: str, command: str, cwd: Path | None = None) -> None:
    _set_task_fields(task_id, status="running", started_at=_now(), progress_percent=5, progress_text="命令已启动")

    log_file = Path(_TASKS[task_id].log_file)
    log_file.parent.mkdir(parents=True, exist_ok=True)

    with log_file.open("w", encoding="utf-8", errors="replace") as log:
        log.write(f"开始时间: {_now()}\n")
        log.write(f"执行命令: {command}\n\n")
        log.flush()
        try:
            process = subprocess.Popen(
                command,
                cwd=str(cwd) if cwd else None,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            assert process.stdout is not None
            for line in process.stdout:
                log.write(line)
                log.flush()
            return_code = process.wait()
        except Exception as exc:
            log.write(f"\n执行异常: {exc}\n")
            return_code = -1

        log.write(f"\n结束时间: {_now()}\n")
        log.write(f"退出码: {return_code}\n")

    success = return_code == 0
    _set_task_fields(
        task_id,
        return_code=return_code,
        finished_at=_now(),
        status="success" if success else "failed",
        progress_percent=100,
        progress_text="执行成功" if success else "执行失败",
        success=success,
        result_message="命令执行成功" if success else f"命令执行失败，退出码: {return_code}",
    )


def _run_download_task(task_id: str) -> None:
    task = _TASKS[task_id]
    log_file = Path(task.log_file)
    log_file.parent.mkdir(parents=True, exist_ok=True)
    _set_task_fields(task_id, status="running", started_at=_now(), progress_percent=0, progress_text="准备下载")
    log_file.write_text(
        f"开始时间: {_now()}\n"
        f"本地包装命令: {build_local_download_command()}\n"
        f"实际下载命令: {build_official_download_command()}\n\n",
        encoding="utf-8",
        errors="replace",
    )

    def on_event(event: dict) -> None:
        event_type = event.get("type")
        if event_type == "progress":
            percent = int(event.get("progress_percent", 0))
            message = str(event.get("message", ""))
            _set_task_fields(task_id, progress_percent=percent, progress_text=message)
            _append_log(log_file, f"[进度 {percent}%] {message}")
        elif event_type == "output":
            _append_log(log_file, str(event.get("line", "")))
        elif event_type == "result":
            success = bool(event.get("success"))
            return_code = event.get("return_code")
            message = str(event.get("message", ""))
            verify = event.get("verify", {})
            _append_log(log_file, "")
            _append_log(log_file, f"[最终结论] {message}")
            _append_log(log_file, json.dumps(verify, ensure_ascii=False, indent=2))
            _set_task_fields(
                task_id,
                return_code=return_code,
                status="success" if success else "failed",
                progress_percent=100,
                progress_text="下载成功" if success else "下载失败",
                success=success,
                result_message=message,
                provider_uri=str(event.get("provider_uri", "")),
                verify=verify,
            )

    result = run_qlib_download(on_event=on_event)
    _set_task_fields(
        task_id,
        finished_at=_now(),
        return_code=result.get("return_code"),
        status="success" if result.get("success") else "failed",
        progress_percent=100,
        progress_text="下载成功" if result.get("success") else "下载失败",
        success=bool(result.get("success")),
        result_message=str(result.get("message", "")),
        provider_uri=str(result.get("provider_uri", "")),
        verify=result.get("verify", {}),
    )
    _append_log(log_file, f"\n结束时间: {_now()}")


def create_command_task(name: str, command: str, cwd: Path | None = None) -> dict:
    task_id = datetime.now().strftime("%Y%m%d_%H%M%S_") + uuid4().hex[:8]
    log_file = LOG_DIR / f"{task_id}.log"
    task = TaskInfo(
        task_id=task_id,
        name=name,
        command=command,
        status="pending",
        return_code=None,
        started_at=None,
        finished_at=None,
        log_file=str(log_file),
    )
    with _TASK_LOCK:
        _TASKS[task_id] = task
    thread = threading.Thread(target=_run_task, args=(task_id, command, cwd), daemon=True)
    thread.start()
    return asdict(task)


def create_check_env_task() -> dict:
    lines = [
        "import json, sys",
        "from pathlib import Path",
        "from qlib_config import get_data_status",
        "print('Python:', sys.version)",
        "print(json.dumps(get_data_status(), ensure_ascii=False, indent=2))",
    ]
    command = f"{sys.executable} -c \"{'; '.join(lines).replace(chr(34), chr(39))}\""
    return create_command_task("检查 Qlib 环境", command, Path(__file__).resolve().parent)


def create_download_sample_task() -> dict:
    task_id = datetime.now().strftime("%Y%m%d_%H%M%S_") + uuid4().hex[:8]
    log_file = LOG_DIR / f"{task_id}.log"
    task = TaskInfo(
        task_id=task_id,
        name="下载 Qlib 中国市场数据",
        command=build_local_download_command(),
        status="pending",
        return_code=None,
        started_at=None,
        finished_at=None,
        log_file=str(log_file),
        task_type="download",
        progress_text="等待下载",
    )
    with _TASK_LOCK:
        _TASKS[task_id] = task
    thread = threading.Thread(target=_run_download_task, args=(task_id,), daemon=True)
    thread.start()
    return asdict(task)


def current_status() -> dict:
    status = get_data_status()
    tasks = list_tasks()
    status.update(
        {
            "download_command": get_download_command(),
            "tasks_count": len(tasks),
            "running_tasks_count": len([item for item in tasks if item["status"] == "running"]),
            "latest_task": tasks[0] if tasks else None,
        }
    )
    return status
