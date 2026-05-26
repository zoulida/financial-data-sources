---
title: Wind Excel 插件取数与代码生成说明
updated: 2026-05-25
---

# Wind Excel 插件取数与代码生成说明

本文档用于规范本项目中通过 **Wind Excel 插件**获取数据的流程。

核心原则：**每次写 Wind 取数代码前，必须先在字段汇总文件中查字段，再根据字段生成 Excel 公式和 Python 代码。**

## 1. 相关文件

- **字段汇总文件**：`md/winds/merged_fields_fixed.txt`
- **Excel 插件封装**：`md/winds/通过excel插件/wind_client.py`
- **示例目录**：`md/winds/通过excel插件`

## 2. 标准流程

### 第一步：明确取数需求

先确认以下信息：

- **证券代码**：例如 `600519.SH`、`000001.SZ`、`881001.WI`
- **数据类型**：时间序列、截面数据、基础资料
- **中文字段含义**：例如“证券简称”“市盈率”“主力净流入金额”
- **日期参数**：起始日期、结束日期或交易日
- **输出格式**：单只股票 DataFrame、多只股票 dict、CSV、Web API 等

### 第二步：在字段汇总文件中查字段

字段汇总文件格式通常是：

```text
中文字段名 -> wind字段名
```

例如：

```text
证券简称 -> sec_name
Wind代码 -> windcode
所属概念板块 -> concept
```

查找字段时，应优先搜索中文含义。如果中文含义不确定，再搜索可能的英文关键字。

#### 推荐查找方式

在 IDE 中打开：

```text
md/winds/merged_fields_fixed.txt
```

然后搜索中文字段名，例如：

```text
市盈率
主力净流入
证券简称
所属概念
```

也可以用 PowerShell 搜索：

```powershell
Select-String -Path "md\winds\merged_fields_fixed.txt" -Pattern "证券简称"
```

### 第三步：确认 Wind 字段名

从字段汇总文件中得到字段名后，必须使用 `->` 右侧的 Wind 字段名。

例如：

```text
证券简称 -> sec_name
```

生成代码时应使用：

```python
fields = ["sec_name"]
```

不能直接把中文字段名写进 Wind 公式。

## 3. 选择 WSD、WSS 或原始公式

### WSD：时间序列数据

适用于：

- PE、PB、收盘价、成交额等历史序列
- 资金流向历史序列
- 指数历史估值

公式格式：

```text
=WSD("证券代码","字段1,字段2","开始日期","结束日期","参数1","参数2")
```

示例：

```text
=WSD("881001.WI","pe","2021-01-01","2026-05-25","ruleType=10","TradingCalendar=SSE","ShowParams=Y","cols=1;rows=1500")
```

### WSS：截面数据

适用于：

- 某个交易日多只股票的静态数据
- 基础资料
- 当前估值、行业、概念、证券简称等

公式格式：

```text
=WSS("代码1,代码2","字段1,字段2","参数")
```

示例：

```text
=WSS("600519.SH,000001.SZ","sec_name,windcode","tradeDate=20260525")
```

### 原始公式调试

当封装函数无法直接满足需求时，可以直接调用：

```python
from md.winds.通过excel插件.wind_client import fetch_wind_formula

raw_df = fetch_wind_formula(
    '=WSD("881001.WI","pe","2021-01-01","2026-05-25","ruleType=10","TradingCalendar=SSE","ShowParams=Y","cols=1;rows=1500")',
    timeout=120,
    interval=0.5,
    visible=False,
)
print(raw_df)
```

## 4. 现有封装函数

### 4.1 执行任意 Wind Excel 公式

```python
from md.winds.通过excel插件.wind_client import fetch_wind_formula

raw_df = fetch_wind_formula(
    formula='=WSD("600519.SH","close","2026-01-01","2026-05-25","TradingCalendar=SSE","ShowParams=Y","cols=1;rows=120")',
    timeout=120,
    interval=0.5,
    visible=False,
)
```

适合：

- 调试新字段
- 处理特殊参数
- 手动控制 `cols` 和 `rows`

### 4.2 多股票、多字段 WSD

```python
from md.winds.通过excel插件.wind_client import fetch_multi_fields_wsd

result = fetch_multi_fields_wsd(
    codes=["600519.SH", "000001.SZ"],
    fields=["mfd_netbuyamt", "mfd_inflowproportion_a"],
    start_date="2026-03-21",
    end_date="2026-05-25",
    timeout=120,
)

for code, df in result.items():
    print(code)
    print(df.tail())
```

返回格式：

```python
{
    "600519.SH": DataFrame,
    "000001.SZ": DataFrame,
}
```

### 4.3 检查环境是否可用

```python
from md.winds.通过excel插件.wind_client import is_wind_available

if not is_wind_available():
    raise RuntimeError("Wind Excel 插件不可用，或当前环境缺少 win32com/pythoncom")
```

## 5. 自动生成代码的标准模板

当需要新增一个 Wind Excel 取数脚本时，建议按下面模板生成。

```python
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from md.winds.通过excel插件.wind_client import fetch_wind_formula, is_wind_available


def build_wsd_formula(code, fields, start_date, end_date, rows):
    """构造 Wind Excel WSD 公式。"""
    field_text = ",".join(fields)
    return (
        f'=WSD("{code}","{field_text}","{start_date}","{end_date}",'
        f'"TradingCalendar=SSE","ShowParams=Y","cols={len(fields)};rows={rows}")'
    )


def parse_numeric_wsd(raw_df, fields, start_date):
    """解析 Wind Excel 返回的数值矩阵。"""
    if raw_df is None or raw_df.empty:
        return pd.DataFrame(columns=["date"] + fields)

    numeric_df = raw_df.apply(lambda col: pd.to_numeric(col, errors="coerce"))
    numeric_df = numeric_df.dropna(how="all").reset_index(drop=True)
    numeric_df = numeric_df.iloc[:, :len(fields)].copy()
    numeric_df.columns = fields[:numeric_df.shape[1]]

    date_index = pd.bdate_range(start=pd.to_datetime(start_date), periods=len(numeric_df))
    return pd.concat([pd.DataFrame({"date": date_index}), numeric_df], axis=1)


def fetch_data():
    """通过 Wind Excel 插件获取数据。"""
    if not is_wind_available():
        raise RuntimeError("Wind Excel 插件不可用，或当前环境缺少 win32com/pythoncom")

    code = "600519.SH"
    fields = ["close"]
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
    rows = 300

    formula = build_wsd_formula(code, fields, start_date, end_date, rows)
    raw_df = fetch_wind_formula(formula, timeout=120, interval=0.5, visible=False)
    return parse_numeric_wsd(raw_df, fields, start_date)


if __name__ == "__main__":
    df = fetch_data()
    print(df.tail())
```

## 6. AI 自动生成代码时必须遵守的规则

当用户要求“用 Wind Excel 插件获取某个数据”时，AI 必须按以下顺序执行：

1. **先读取或搜索字段汇总文件**：`md/winds/merged_fields_fixed.txt`
2. **根据中文含义确认 Wind 字段名**：只使用 `->` 右侧字段
3. **判断使用 WSD 还是 WSS**：历史序列用 WSD，截面/基础资料用 WSS
4. **生成 Excel 公式**：明确 `code`、`fields`、日期、参数、`cols`、`rows`
5. **优先复用封装**：优先用 `wind_client.py` 中的 `fetch_wind_formula` 或 `fetch_multi_fields_wsd`
6. **解析返回结果**：兼容日期列和纯数值矩阵两种情况
7. **做最小验证**：至少 `py_compile`，如环境允许再真实运行一次

## 7. 给 AI 的提示词模板

以后可以这样要求 AI 自动生成代码：

```text
请通过 Wind Excel 插件获取【数据需求】。
要求：
1. 先在 md/winds/merged_fields_fixed.txt 中查找对应 Wind 字段；
2. 再参考 md/winds/通过excel插件/wind_client.py 生成取数代码；
3. 不要使用 WindPy；
4. 用 Excel WSD/WSS 公式获取数据；
5. 代码要包含字段确认、公式构造、取数、解析和简单验证。
```

示例：

```text
请通过 Wind Excel 插件获取贵州茅台近 1 年收盘价和 PE。
要求先查 md/winds/merged_fields_fixed.txt 的字段，再生成 Python 脚本。
```

## 8. 常见参数

### 时间序列常用参数

```text
TradingCalendar=SSE
ShowParams=Y
cols=字段数量;rows=预计行数
```

### 估值类常用参数

```text
ruleType=10
TradingCalendar=SSE
ShowParams=Y
```

### 资金流向类常用参数

```text
unit=1
traderType=1
TradingCalendar=SSE
rptType=1
Version=1
ShowParams=Y
UnitMask=9
```

## 9. 注意事项

- 不要再使用 `WindPy`，当前项目优先使用 Wind Excel 插件。
- Windows 环境需要安装 `pywin32`，并且 Excel 能正常加载 Wind 插件。
- Wind 终端需要已启动并登录。
- 如果控制台出现中文乱码，通常不影响取数结果，可优先检查返回 DataFrame。
- WSD 返回结果有时是纯数值矩阵，没有日期列，需要按起始日期补交易日或工作日。
- `cols` 应等于字段数量，`rows` 应大于预计返回行数。
- 新字段首次使用时，建议先用 `fetch_wind_formula` 打印原始 `raw_df`，确认返回结构后再写解析逻辑。

## 10. 本项目已验证示例

### Wind 全A指数 PE

- **代码**：`881001.WI`
- **字段**：`pe`
- **用途**：大盘逃顶估值百分位
- **公式示例**：

```text
=WSD("881001.WI","pe","2021-04-26","2026-05-25","ruleType=10","TradingCalendar=SSE","ShowParams=Y","cols=1;rows=1500")
```

已验证可以通过 `fetch_wind_formula` 获取数据，并解析为 PE 时间序列。
