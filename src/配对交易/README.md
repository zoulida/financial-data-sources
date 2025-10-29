# XtQuant 比价监控脚本

## 功能概述

这是一个基于 XtQuant xtdata 接口的比价监控脚本，用于监控多组金融对子的价差和统计指标。

## 主要功能

- **多对子监控**: 支持指数、ETF、期货等多种金融工具的对子监控
- **统计指标计算**: 自动计算 Z-score、半衰期等统计指标
- **实时警告**: 当价差偏离超过阈值时，在终端显示红色警告
- **数据持久化**: 结果自动保存到 CSV 文件
- **异常处理**: 完善的错误处理和重试机制
- **彩色日志**: 使用 colorama 提供彩色终端输出

## 监控对子

当前配置的监控对子：

1. **000300.SH/000852.SH** - 沪深300指数 vs 中证1000指数 (阈值: 2.0)
2. **000016.SH/399303.SZ** - 上证50指数 vs 创业板指数 (阈值: 2.0)  
3. **510500.SH/000905.SH** - 中证500ETF vs 中证500指数 (阈值: 2.0)
4. **518880.SH/AU0** - 黄金ETF vs 黄金期货主力 (阈值: 1.5)
5. **CU0/CU1** - 铜期货主力 vs 次主力 (阈值: 2.0)
6. **510300.SH/300现货篮** - 沪深300ETF vs 现货篮 (阈值: 1.5)
7. **159949.SZ/创50现货篮** - 创业板50ETF vs 现货篮 (阈值: 1.5)
8. **512880.SH/券商现货篮** - 券商ETF vs 现货篮 (阈值: 1.5)

## 安装依赖

```bash
# 激活虚拟环境
.\venv\Scripts\activate

# 安装依赖
pip install xtquant pandas numpy statsmodels colorama
```

## 使用方法

### 1. 设置 XtQuant Token

在使用前，需要先设置 XtQuant 的 Token：

```python
from xtquant import xtdata
xtdata.set_token('your_token_here')
```

### 2. 运行监控脚本

```bash
# 进入项目目录
cd "D:\pythonProject\数据源"

# 激活虚拟环境
.\venv\Scripts\activate

# 运行监控脚本
python src\配对交易\monitor_xtdata_ratio.py
```

## 输出文件

- **ratio_monitor_xtdata.csv**: 监控结果数据
- **ratio_monitor_xtdata.log**: 详细运行日志

## 输出指标说明

| 字段 | 说明 |
|------|------|
| 对子名 | 监控的对子名称 |
| 最新日期 | 数据的最新日期 |
| Z_score | 40日滚动Z-score |
| 半衰期 | OU模型半衰期（天） |
| 阈值 | 警告触发阈值 |
| 偏离方向 | A贵/B贵 |
| 数据点数 | 有效数据点数量 |

## 警告机制

- 当 |Z-score| >= 阈值时，终端显示红色警告
- 不同对子使用不同的阈值设置
- 所有警告信息同时记录到日志文件

## 技术特点

### 数据获取
- 使用 XtQuant xtdata 接口
- 支持指数、ETF、期货数据
- 自动处理数据格式和列名差异
- 内置重试机制（3次重试，2秒间隔）

### 统计计算
- 40日滚动Z-score计算
- OU模型半衰期估算
- 前向填充处理缺失值
- 数据日期自动对齐

### 错误处理
- 网络请求失败自动重试
- 单个对子失败不影响整体流程
- 详细的错误日志记录
- 优雅的异常处理

## 注意事项

1. **Token设置**: 需要有效的 XtQuant Token 才能使用
2. **数据权限**: 确保有相应的数据权限
3. **网络环境**: 需要稳定的网络连接
4. **数据质量**: 建议定期检查数据质量和完整性

## 故障排除

### 常见问题

1. **Token错误**
   - 检查 Token 是否正确设置
   - 确认 Token 是否有效

2. **数据获取失败**
   - 检查网络连接
   - 确认数据权限
   - 查看详细错误日志

3. **ETF持仓数据问题**
   - 如果无法获取持仓数据，会使用ETF本身作为现货篮
   - 可以手动调整持仓权重

### 日志查看

```bash
# 查看最新日志
tail -f ratio_monitor_xtdata.log

# 查看错误日志
grep "ERROR" ratio_monitor_xtdata.log
```

## 扩展功能

### 添加新的监控对子

在 `PAIRS_CONFIG` 中添加新的对子配置：

```python
PAIRS_CONFIG = {
    # 现有对子...
    "新对子A/新对子B": {"threshold": 2.0, "type": "index"},
}
```

### 修改阈值

根据历史数据和风险偏好调整阈值：

```python
"对子名": {"threshold": 1.5, "type": "etf_index"},  # 更敏感的阈值
"对子名": {"threshold": 3.0, "type": "index"},     # 更宽松的阈值
```

### 支持的对子类型

- `index`: 指数 vs 指数
- `etf_index`: ETF vs 指数
- `etf_futures`: ETF vs 期货
- `futures_spread`: 期货主力 vs 次主力
- `etf_basket`: ETF vs 现货篮

## 版本历史

- **v1.0**: 初始版本，基于 XtQuant xtdata 接口
- 支持8个核心对子监控
- 完整的统计指标计算
- 彩色日志和CSV输出

## 联系信息

如有问题或建议，请查看日志文件或联系开发团队。
