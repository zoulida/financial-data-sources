import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from qlib_config import ALLOW_CUSTOM_COMMAND
from qlib_reader import dataframe_to_records, get_calendar, get_features, get_instruments
from qlib_tasks import (
    create_check_env_task,
    create_command_task,
    create_download_sample_task,
    current_status,
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
    <p>明确展示下载命令、下载进度、实时日志和最终成功/失败结论。</p>
  </header>
  <main>
    <section class="grid">
      <div class="card">
        <h2>下载状态</h2>
        <div id="status">加载中...</div>
        <button onclick="refreshAll()">刷新状态</button>
        <button class="secondary" onclick="showHelp()">API 说明</button>
      </div>
      <div class="card">
        <h2>一键下载</h2>
        <button onclick="postTask('/api/tasks/check-env')">检查环境</button>
        <button onclick="postTask('/api/tasks/download-sample')">开始下载 Qlib 数据</button>
      </div>
    </section>

    <section class="card" style="margin-top:16px;">
      <h2>下载命令</h2>
      <p>建议直接运行这个包装命令，它会输出进度并在最后告诉你是否成功：</p>
      <div class="cmd" id="localCommand">加载中...</div>
      <p>实际调用的 Qlib 官方下载命令：</p>
      <div class="cmd" id="officialCommand">加载中...</div>
    </section>

    <section class="card" style="margin-top:16px;">
      <h2>当前进度</h2>
      <div class="bar"><div class="bar-inner" id="progressBar"></div></div>
      <p id="progressText">等待下载</p>
      <p class="result" id="resultText">暂无下载结论</p>
    </section>

    <section class="card" style="margin-top:16px;">
      <h2>高级：自定义命令</h2>
      <textarea id="command" rows="3">python -m qlib.run.get_data qlib_data --target_dir ./qlib_data/cn_data --region cn</textarea>
      <button onclick="runCommand()">执行命令</button>
    </section>

    <section class="card" style="margin-top:16px;">
      <h2>任务列表</h2>
      <div id="tasks"></div>
    </section>

    <section class="card" style="margin-top:16px;">
      <h2>日志 / API 输出</h2>
      <pre id="log">请选择任务或点击 API 说明。</pre>
    </section>
  </main>
<script>
async function api(path, options = {}) {
  const resp = await fetch(path, options);
  return await resp.json();
}
function mark(v) { return v ? '<span class="ok">是</span>' : '<span class="bad">否</span>'; }
async function refreshStatus() {
  const data = await api('/api/status');
  document.getElementById('localCommand').textContent = data.download_command.local_command;
  document.getElementById('officialCommand').textContent = data.download_command.official_command;
  const latest = data.latest_task;
  if (latest) {
    document.getElementById('progressBar').style.width = (latest.progress_percent || 0) + '%';
    document.getElementById('progressText').textContent = `进度 ${latest.progress_percent || 0}%：${latest.progress_text || latest.status}`;
    document.getElementById('resultText').textContent = latest.result_message || '任务执行中，暂无最终结论';
    document.getElementById('resultText').className = latest.success === true ? 'result ok' : (latest.success === false ? 'result bad' : 'result');
  }
  document.getElementById('status').innerHTML = `
    <p>pyqlib 已安装：${mark(data.qlib_installed)}</p>
    <p>数据目录：<code>${data.provider_uri}</code></p>
    <p>数据目录存在：${mark(data.provider_exists)}</p>
    <p>运行中任务：${data.running_tasks_count}</p>
    <p>最近任务：${latest ? latest.name + ' / ' + latest.status : '无'}</p>`;
}
async function refreshTasks() {
  const data = await api('/api/tasks');
  const rows = data.tasks.map(t => `<tr><td>${t.task_id}</td><td>${t.name}</td><td>${t.status}</td><td>${t.progress_percent || 0}%</td><td>${t.progress_text || ''}</td><td>${t.result_message || ''}</td><td><button onclick="showLog('${t.task_id}')">日志</button></td></tr>`).join('');
  document.getElementById('tasks').innerHTML = `<table><thead><tr><th>ID</th><th>名称</th><th>状态</th><th>进度</th><th>阶段</th><th>结论</th><th>操作</th></tr></thead><tbody>${rows}</tbody></table>`;
}
async function refreshAll() { await refreshStatus(); await refreshTasks(); }
async function postTask(path) {
  const data = await api(path, {method: 'POST'});
  document.getElementById('log').textContent = JSON.stringify(data, null, 2);
  await refreshAll();
}
async function runCommand() {
  const command = document.getElementById('command').value;
  const data = await api('/api/tasks/run-command', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({command})});
  document.getElementById('log').textContent = JSON.stringify(data, null, 2);
  await refreshAll();
}
async function showLog(taskId) {
  const data = await api('/api/tasks/' + taskId + '/log');
  document.getElementById('log').textContent = data.log || JSON.stringify(data, null, 2);
}
async function showHelp() {
  const data = await api('/api/help');
  document.getElementById('log').textContent = JSON.stringify(data, null, 2);
}
refreshAll();
setInterval(refreshAll, 5000);
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
            if path == "/api/tasks/check-env":
                self._send_json({"ok": True, "task": create_check_env_task()})
            elif path == "/api/tasks/download-sample":
                self._send_json({"ok": True, "task": create_download_sample_task()})
            elif path == "/api/tasks/run-command":
                if not ALLOW_CUSTOM_COMMAND:
                    self._send_json({"ok": False, "error": "自定义命令已关闭"}, 403)
                    return
                payload = self._read_json()
                command = str(payload.get("command", "")).strip()
                if not command:
                    self._send_json({"ok": False, "error": "命令不能为空"}, 400)
                    return
                self._send_json({"ok": True, "task": create_command_task("自定义命令", command)})
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
            "GET /api/tasks/{task_id}/log": "任务日志",
            "POST /api/tasks/check-env": "检查环境",
            "POST /api/tasks/download-sample": "启动 Qlib 数据下载任务，任务对象含 progress_percent、progress_text、result_message",
            "POST /api/tasks/run-command": "执行自定义命令，body: {command}",
            "GET /api/qlib/calendar?freq=day": "读取交易日历",
            "GET /api/qlib/instruments?market=all": "读取股票列表",
            "POST /api/qlib/features": "读取特征数据，body: {instruments, fields, start_time, end_time, freq}",
        },
    }


def run_server(host: str, port: int) -> None:
    server = ThreadingHTTPServer((host, port), QlibRequestHandler)
    print(f"服务地址: http://{host}:{port}")
    server.serve_forever()
