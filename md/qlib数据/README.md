# Qlib 数据下载工具

这个目录提供一个明确面向下载的 Qlib 数据工具，核心目标是：

- 直接给出下载命令。
- 显示下载进度。
- 显示实时日志。
- 下载结束后告诉你是否成功。
- Python 读取接口：给其他策略程序读取 Qlib 数据。
- HTTP API：给外部程序通过 Web 接口读取数据。

## 安装 Qlib

基础 Web 服务不需要额外 Web 框架。读取 Qlib 数据前需要安装 pyqlib：

```powershell
pip install pyqlib
```

## 启动 Web 控制台

在项目根目录运行：

```powershell
python md/qlib数据/run_web.py
```

浏览器访问：

```text
http://127.0.0.1:8765
```

## 直接下载命令

如果你不想打开 Web，直接运行：

```powershell
python md/qlib数据/download_qlib_data.py
```

这个命令会打印：

- 实际执行的 Qlib 官方下载命令。
- 当前下载进度。
- Qlib 原始下载日志。
- 最终结论：成功或失败。
- 数据目录校验结果。

脚本内部实际调用的 Qlib 官方命令类似：

```powershell
python -u -m qlib.run.get_data qlib_data --target_dir "d:\pythonProject\数据源\md\qlib数据\qlib_data\cn_data" --region cn
```

如果命令退出码为 `0`，并且下载目录下存在：

- `calendars`
- `features`
- `instruments`
- 至少一个数据文件

工具才会判断为下载成功。

## 默认数据目录

默认 Qlib 数据目录为：

```text
md/qlib数据/qlib_data/cn_data
```

可以在 `qlib_config.py` 中修改：

```python
DEFAULT_QLIB_PROVIDER_URI = BASE_DIR / "qlib_data" / "cn_data"
```

## Web 控制台功能

- 检查 pyqlib 是否安装。
- 检查 Qlib 数据目录是否存在。
- 展示本地包装下载命令。
- 展示实际 Qlib 官方下载命令。
- 一键下载 Qlib 中国市场数据。
- 显示下载进度条。
- 显示当前阶段。
- 显示最终成功/失败结论。
- 执行自定义命令。
- 查看任务列表和日志。
- 查看 HTTP API 说明。

## HTTP API

### 获取状态

```http
GET /api/status
```

### 获取任务列表

```http
GET /api/tasks
```

任务对象中重点字段：

```json
{
  "status": "running",
  "progress_percent": 45,
  "progress_text": "正在下载数据包",
  "success": null,
  "result_message": "",
  "verify": {}
}
```

下载结束后：

```json
{
  "status": "success",
  "progress_percent": 100,
  "progress_text": "下载成功",
  "success": true,
  "result_message": "下载成功，Qlib 数据目录校验通过"
}
```

### 查看任务日志

```http
GET /api/tasks/{task_id}/log
```

### 下载示例数据

```http
POST /api/tasks/download-sample
```

返回任务 ID 后，可以用：

```http
GET /api/tasks
```

持续观察 `progress_percent`、`progress_text`、`result_message`。

### 执行自定义命令

```http
POST /api/tasks/run-command
Content-Type: application/json

{
  "command": "python -m qlib.run.get_data qlib_data --target_dir ./qlib_data/cn_data --region cn"
}
```

### 读取交易日历

```http
GET /api/qlib/calendar?freq=day
```

### 读取股票列表

```http
GET /api/qlib/instruments?market=all
```

### 读取特征数据

```http
POST /api/qlib/features
Content-Type: application/json

{
  "instruments": ["SH600519"],
  "fields": ["$close", "$volume"],
  "start_time": "2024-01-01",
  "end_time": "2024-01-31",
  "freq": "day"
}
```

## Python 接口示例

```python
import sys
from pathlib import Path

sys.path.append(str(Path("md/qlib数据").resolve()))

from qlib_reader import get_features, init_qlib

init_qlib()

df = get_features(
    instruments=["SH600519"],
    fields=["$close", "$volume"],
    start_time="2024-01-01",
    end_time="2024-01-31",
)
print(df)
```

## 安全说明

- 服务默认只监听 `127.0.0.1`，仅本机访问。
- 自定义命令默认开启，可在 `qlib_config.py` 关闭：

```python
ALLOW_CUSTOM_COMMAND = False
```

- 下载数据和执行命令会写入 `logs` 目录，方便追踪。
