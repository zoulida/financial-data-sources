import webbrowser
from qlib_config import WEB_HOST, WEB_PORT
from qlib_web_server import run_server


if __name__ == "__main__":
    url = f"http://{WEB_HOST}:{WEB_PORT}"
    print(f"Qlib 数据管理 Web 控制台已启动: {url}")
    try:
        webbrowser.open(url)
    except Exception:
        pass
    run_server(WEB_HOST, WEB_PORT)
