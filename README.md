# 数据源项目

## 📋 项目概述

这是一个金融数据获取项目，支持多种数据源，包括XtQuant和Wind API。

## 🚀 快速开始

### 1. 虚拟环境配置

项目已配置好虚拟环境，点击运行三角时会自动使用虚拟环境。

**手动激活虚拟环境：**
```bash
# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### 2. 依赖安装

所有依赖包已自动安装，包括：
- pandas, numpy, matplotlib, seaborn
- scipy, scikit-learn, statsmodels
- plotly, bokeh, jupyter
- WindPy, xtquant (需要手动安装对应终端)

### 3. 测试环境

运行测试脚本验证环境配置：
```bash
python test_environment.py
```

## 📊 数据源配置

### 数据获取优先级规则

根据 `.cursorrules` 配置：

1. **行情数据**: 优先使用 XtQuant (xtdata)
2. **财务数据**: 使用 Wind API
3. **备选方案**: 当XtQuant无法满足时使用Wind API

### 外部模块配置

项目已配置支持导入外部模块：

- **firstBan 模块**: `D:\pythonProject\firstBan` 已添加到 Python 路径
- **自动导入**: 在 Cursor 中可直接使用 `from firstban import your_module`
- **配置位置**: `.vscode/settings.json` 中的 `python.analysis.extraPaths`

### 参考文档

- **XtQuant**: `md/xtdata/xtdata_api_guide.md`
- **Wind API**: `md/winds/Wind数据获取完整指南.md`
- **完整字段**: `md/winds/merged_fields_fixed.txt`

## 🛠️ 开发环境

### VS Code 配置

项目包含 `.vscode/settings.json` 和 `.vscode/launch.json` 配置：

- 自动使用虚拟环境Python解释器
- 支持调试和运行配置
- 集成终端自动激活环境

### 代码规范

- 使用 black 进行代码格式化
- 使用 flake8 进行代码检查
- 支持 Jupyter Notebook 开发

## 📁 项目结构

```
数据源/
├── .vscode/                    # VS Code 配置
│   ├── settings.json          # 编辑器设置
│   └── launch.json            # 调试配置
├── venv/                      # 虚拟环境
├── md/                        # 文档目录
│   ├── xtdata/               # XtQuant 文档
│   └── winds/                # Wind API 文档
├── src/                       # 源代码
├── .cursorrules              # Cursor AI 规则
├── requirements.txt          # 依赖包列表
├── test_environment.py       # 环境测试脚本
└── README.md                 # 项目说明
```

## 🔧 使用说明

### 1. 运行Python脚本

直接点击VS Code中的运行三角按钮，会自动使用虚拟环境。

### 2. 数据获取示例

**XtQuant 示例：**
```python
from xtquant import xtdata
import pandas as pd

# 初始化
xtdata.set_token('your_token_here')

# 获取行情数据
data = xtdata.get_market_data_ex(
    field_list=['open', 'high', 'low', 'close', 'volume', 'amount'],
    stock_list=['000001.SZ'],
    period='1d',
    count=100
)
```

**Wind API 示例：**
```python
import WindPy as w
import pandas as pd

# 初始化
w.start()

# 获取财务数据
data = w.wss("000001.SZ", "pe_ttm,pb_lf,roe,roa", "tradeDate=20231231")
df = pd.DataFrame(data.Data, columns=data.Fields, index=data.Codes)

# 关闭
w.stop()
```

## ⚠️ 注意事项

1. **数据权限**: 确保有相应的数据源权限
2. **环境隔离**: 始终使用虚拟环境运行代码
3. **错误处理**: 检查数据获取的ErrorCode
4. **资源管理**: 使用完毕后关闭数据接口

## 📞 技术支持

如遇到问题，请检查：
1. 虚拟环境是否正确激活
2. 依赖包是否完整安装
3. 数据源权限是否正常
4. 网络连接是否稳定

---

**配置完成！** 现在可以开始使用项目进行金融数据获取和分析了。
