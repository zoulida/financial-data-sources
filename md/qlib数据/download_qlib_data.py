import json
import sys

from qlib_downloader import build_mirror_download_command, build_official_download_command, run_mirror_download, run_qlib_download


try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def safe_print(value: object = "", **kwargs) -> None:
    text = str(value)
    try:
        print(text, **kwargs)
    except UnicodeEncodeError:
        encoding = sys.stdout.encoding or "utf-8"
        print(text.encode(encoding, errors="replace").decode(encoding, errors="replace"), **kwargs)


def main() -> int:
    force = "--force" in sys.argv
    source = "official" if "--source" in sys.argv and "official" in sys.argv else "mirror"
    safe_print("Qlib 数据下载工具")
    safe_print(f"下载模式: {'强制更新' if force else '普通下载'}")
    safe_print(f"数据源: {'investment_data 镜像' if source == 'mirror' else 'Qlib 官方演示数据'}")
    safe_print("实际执行的下载命令:")
    safe_print(build_mirror_download_command() if source == "mirror" else build_official_download_command())
    safe_print("-" * 80)

    def on_event(event: dict) -> None:
        event_type = event.get("type")
        if event_type == "progress":
            safe_print(f"[进度 {event.get('progress_percent', 0)}%] {event.get('message', '')}", flush=True)
        elif event_type == "output":
            safe_print(event.get("line", ""), flush=True)
        elif event_type == "result":
            safe_print("-" * 80)
            safe_print(f"[最终结论] {event.get('message', '')}")
            safe_print(json.dumps(event.get("verify", {}), ensure_ascii=False, indent=2))

    if source == "mirror":
        result = run_mirror_download(on_event=on_event, force=force)
    else:
        result = run_qlib_download(on_event=on_event, force=force)
    return 0 if result.get("success") else 1


if __name__ == "__main__":
    raise SystemExit(main())
