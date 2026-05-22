from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_QLIB_PROVIDER_URI = BASE_DIR / "qlib_data" / "cn_data"
DEFAULT_REGION = "cn"
WEB_HOST = "127.0.0.1"
WEB_PORT = 8765
ALLOW_CUSTOM_COMMAND = True
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)


def get_provider_uri() -> Path:
    return DEFAULT_QLIB_PROVIDER_URI


def check_pyqlib_installed() -> tuple[bool, str]:
    try:
        import qlib  # noqa: F401
    except Exception as exc:
        return False, str(exc)
    return True, "pyqlib 已安装"


def get_data_status() -> dict:
    provider_uri = get_provider_uri()
    installed, message = check_pyqlib_installed()
    return {
        "qlib_installed": installed,
        "qlib_message": message,
        "provider_uri": str(provider_uri),
        "provider_exists": provider_uri.exists(),
        "calendar_dir_exists": (provider_uri / "calendars").exists(),
        "features_dir_exists": (provider_uri / "features").exists(),
        "instruments_dir_exists": (provider_uri / "instruments").exists(),
    }
