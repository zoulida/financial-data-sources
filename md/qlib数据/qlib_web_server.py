import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from qlib_reader import dataframe_to_records, get_calendar, get_features, get_instruments
from qlib_tasks import (
    create_download_sample_task,
    current_status,
    get_task,
    get_download_command,
    list_tasks,
    read_task_log,
)


INDEX_HTML = r"""
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Qlib 数据下载工具</title>
  <style>
    body { margin: 0; font-family: Arial, "Microsoft YaHei", sans-serif; background: #f5f7fb; color: #1f2937; }
    header { background: linear-gradient(135deg, #111827, #2563eb); color: white; padding: 28px 36px; }
    main { max-width: 1180px; margin: 24px auto; padding: 0 18px; }
    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 16px; }
    .card { background: white; border-radius: 14px; padding: 18px; box-shadow: 0 8px 24px rgba(15, 23, 42, 0.08); }
    button { border: 0; border-radius: 10px; background: #2563eb; color: white; padding: 10px 14px; cursor: pointer; margin: 4px 6px 4px 0; }
    button.secondary { background: #475569; }
    button.danger { background: #dc2626; }
    button.big { font-size: 20px; padding: 18px 32px; border-radius: 14px; box-shadow: 0 8px 20px rgba(37, 99, 235, 0.35); }
    button.big:disabled { background: #94a3b8; box-shadow: none; cursor: not-allowed; }
    input, textarea { width: 100%; box-sizing: border-box; border: 1px solid #cbd5e1; border-radius: 10px; padding: 10px; font-family: Consolas, monospace; }
    pre { background: #0f172a; color: #d1fae5; padding: 14px; border-radius: 12px; overflow: auto; max-height: 460px; }
    table { width: 100%; border-collapse: collapse; }
    th, td { border-bottom: 1px solid #e5e7eb; text-align: left; padding: 8px; font-size: 13px; }
    .ok { color: #059669; font-weight: bold; }
    .bad { color: #dc2626; font-weight: bold; }
    .cmd { background: #111827; color: #e5e7eb; padding: 12px; border-radius: 10px; word-break: break-all; font-family: Consolas, monospace; }
    .bar { height: 18px; background: #e5e7eb; border-radius: 999px; overflow: hidden; }
    .bar-inner { height: 100%; width: 0%; background: linear-gradient(90deg, #2563eb, #22c55e); transition: width .3s; }
    .result { font-size: 16px; font-weight: bold; }
  </style>
</head>
<body>
  <header>
    <h1>Qlib 数据下载工具</h1>
    <p>点击下载后，只显示当前这一次任务的进度、实时日志和最终结论。</p>
  </header>
  <main>
    <section class="grid">
      <div class="card">
        <h2>下载状态</h2>
        <div id="status">加载中...</div>
        <button onclick="refreshAll()">刷新状态</button>
      </div>
      <div class="card">
        <h2>一键下载</h2>
        <p>普通下载：已有完整数据则不重复下载。</p>
        <button id="downloadButton" class="big" onclick="startDownload(false)">⬇ 下载 Qlib 数据</button>
        <p>强制更新：删除旧数据后重新下载最新数据。</p>
        <button id="forceButton" class="big danger" onclick="startDownload(true)">🔄 强制更新最新数据</button>
      </div>
    </section>

    <section class="card" style="margin-top:16px;">
      <h2>下载命令</h2>
      <p>当前默认数据源：chenditc/investment_data GitHub Release 镜像。</p>
      <p>建议直接运行这个镜像下载命令，它会输出进度并在最后告诉你是否成功：</p>
      <div class="cmd" id="localCommand">加载中...</div>
      <p>备用：Qlib 官方演示数据命令（只到 2020）：</p>
      <div class="cmd" id="officialCommand">加载中...</div>
    </section>

    <section class="card" style="margin-top:16px;">
      <h2>当前进度</h2>
      <div class="bar"><div class="bar-inner" id="progressBar"></div></div>
      <p id="progressText">等待下载</p>
      <p class="result" id="resultText">暂无下载结论</p>
    </section>

    <section class="card" style="margin-top:16px;">
      <h2>当前下载日志</h2>
      <pre id="log">尚未开始下载。点击“开始下载 Qlib 数据”后，这里只显示当前任务日志。</pre>
    </section>
  </main>
<script>
async function api(path, options = {}) {
  const resp = await fetch(path, options);
  return await resp.json();
}
function mark(v) { return v ? '<span class="ok">是</span>' : '<span class="bad">否</span>'; }
let activeTaskId = null;
let activeTaskFinished = false;

async function refreshStatus() {
  const data = await api('/api/status');
  document.getElementById('localCommand').textContent = data.download_command.mirror_command;
  document.getElementById('officialCommand').textContent = data.download_command.official_command;
  document.getElementById('status').innerHTML = `
    <p>pyqlib 已安装：${mark(data.qlib_installed)}</p>
    <p>数据目录：<code>${data.provider_uri}</code></p>
    <p>数据目录存在：${mark(data.provider_exists)}</p>
    <p>当前数据最新日期：<strong>${data.latest_calendar_date || '暂无数据'}</strong></p>
    <p>镜像最新 release：<strong>${data.mirror_release && data.mirror_release.tag_name ? data.mirror_release.tag_name : '读取中/读取失败'}</strong></p>
    <p>本地数据文件数：${data.qlib_verify ? data.qlib_verify.files_count : 0}</p>
    <p>当前任务：${activeTaskId ? activeTaskId : '尚未开始'}</p>`;
}

function renderTask(task) {
  document.getElementById('progressBar').style.width = (task.progress_percent || 0) + '%';
  document.getElementById('progressText').textContent = `进度 ${task.progress_percent || 0}%：${task.progress_text || task.status}`;
  document.getElementById('resultText').textContent = task.result_message || '当前任务运行中，暂无最终结论';
  document.getElementById('resultText').className = task.success === true ? 'result ok' : (task.success === false ? 'result bad' : 'result');
  activeTaskFinished = ['success', 'failed'].includes(task.status);
  document.getElementById('downloadButton').disabled = !activeTaskFinished;
  document.getElementById('forceButton').disabled = !activeTaskFinished;
}

async function refreshActiveTask() {
  if (!activeTaskId) {
    return;
  }
  const taskData = await api('/api/tasks/' + activeTaskId);
  if (taskData.ok && taskData.task) {
    renderTask(taskData.task);
  }
  const logData = await api('/api/tasks/' + activeTaskId + '/log');
  document.getElementById('log').textContent = logData.log || '当前任务暂无日志。';
}

async function refreshAll() {
  await refreshStatus();
  await refreshActiveTask();
}

async function startDownload(force) {
  activeTaskId = null;
  activeTaskFinished = false;
  document.getElementById('downloadButton').disabled = true;
  document.getElementById('forceButton').disabled = true;
  document.getElementById('progressBar').style.width = '0%';
  document.getElementById('progressText').textContent = force ? '准备启动强制更新任务...' : '准备启动下载任务...';
  document.getElementById('resultText').textContent = '当前任务运行中，暂无最终结论';
  document.getElementById('resultText').className = 'result';
  document.getElementById('log').textContent = force ? '正在启动强制更新任务...' : '正在启动当前下载任务...';
  const path = force ? '/api/tasks/force-update' : '/api/tasks/download-sample';
  const data = await api(path, {method: 'POST'});
  if (!data.ok) {
    document.getElementById('downloadButton').disabled = false;
    document.getElementById('forceButton').disabled = false;
    document.getElementById('resultText').textContent = data.error || '启动下载任务失败';
    document.getElementById('resultText').className = 'result bad';
    return;
  }
  activeTaskId = data.task.task_id;
  document.getElementById('log').textContent = '当前任务已启动，正在等待日志输出...';
  await refreshStatus();
  await refreshActiveTask();
}

refreshAll();
setInterval(refreshAll, 2000);
</script>
</body>
</html>
"""


class QlibRequestHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        return

    def _send_json(self, payload: dict, status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, html: str) -> None:
        body = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0") or 0)
        if length <= 0:
            return {}
        raw = self.rfile.read(length).decode("utf-8")
        return json.loads(raw or "{}")

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)
        try:
            if path == "/":
                self._send_html(INDEX_HTML)
            elif path == "/api/status":
                self._send_json({"ok": True, **current_status()})
            elif path == "/api/download-command":
                self._send_json({"ok": True, **get_download_command()})
            elif path == "/api/tasks":
                self._send_json({"ok": True, "tasks": list_tasks()})
            elif path.startswith("/api/tasks/") and path.endswith("/log"):
                task_id = path.split("/")[3]
                self._send_json({"ok": True, "task_id": task_id, "log": read_task_log(task_id)})
            elif path.startswith("/api/tasks/"):
                task_id = path.split("/")[3]
                task = get_task(task_id)
                if task:
                    self._send_json({"ok": True, "task": task})
                else:
                    self._send_json({"ok": False, "error": "任务不存在"}, 404)
            elif path == "/api/qlib/calendar":
                freq = query.get("freq", ["day"])[0]
                self._send_json({"ok": True, "data": get_calendar(freq=freq)})
            elif path == "/api/qlib/instruments":
                market = query.get("market", ["all"])[0]
                self._send_json({"ok": True, "data": get_instruments(market=market)})
            elif path == "/api/help":
                self._send_json(help_payload())
            else:
                self._send_json({"ok": False, "error": "接口不存在"}, 404)
        except Exception as exc:
            self._send_json({"ok": False, "error": str(exc)}, 500)

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        try:
            if path == "/api/tasks/download-sample":
                self._send_json({"ok": True, "task": create_download_sample_task()})
            elif path == "/api/tasks/force-update":
                self._send_json({"ok": True, "task": create_download_sample_task(force=True)})
            elif path == "/api/qlib/features":
                payload = self._read_json()
                df = get_features(
                    instruments=payload.get("instruments", []),
                    fields=payload.get("fields", []),
                    start_time=payload.get("start_time"),
                    end_time=payload.get("end_time"),
                    freq=payload.get("freq", "day"),
                )
                self._send_json({"ok": True, "data": dataframe_to_records(df)})
            else:
                self._send_json({"ok": False, "error": "接口不存在"}, 404)
        except Exception as exc:
            self._send_json({"ok": False, "error": str(exc)}, 500)


def help_payload() -> dict:
    return {
        "ok": True,
        "endpoints": {
            "GET /": "Web 控制台",
            "GET /api/status": "服务和数据目录状态",
            "GET /api/download-command": "获取本地包装下载命令和实际 Qlib 官方下载命令",
            "GET /api/tasks": "任务列表",
            "GET /api/tasks/{task_id}": "当前任务状态",
            "GET /api/tasks/{task_id}/log": "任务日志",
            "POST /api/tasks/download-sample": "启动 Qlib 数据下载任务，任务对象含 progress_percent、progress_text、result_message",
            "POST /api/tasks/force-update": "强制删除旧 Qlib 数据并重新下载",
            "GET /api/qlib/calendar?freq=day": "读取交易日历",
            "GET /api/qlib/instruments?market=all": "读取股票列表",
            "POST /api/qlib/features": "读取特征数据，body: {instruments, fields, start_time, end_time, freq}",
        },
    }


def run_server(host: str, port: int) -> None:
    server = ThreadingHTTPServer((host, port), QlibRequestHandler)
    print(f"服务地址: http://{host}:{port}")
    server.serve_forever()
