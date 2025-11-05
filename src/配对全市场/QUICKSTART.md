# 配对交易全市场扫描 - 快速开始指南

## 一分钟快速启动

### Windows用户

```bash
# 1. 打开命令行，进入项目目录
cd D:\pythonProject\数据源\src\配对全市场

# 2. 双击运行启动脚本
run.bat

# 或使用命令行
.\run.bat
```

### Linux/Mac用户

```bash
# 1. 打开终端，进入项目目录
cd /path/to/数据源/src/配对全市场

# 2. 添加执行权限（仅首次）
chmod +x run.sh

# 3. 运行启动脚本
./run.sh
```

## 运行前检查清单

- [ ] Wind终端已登录
- [ ] 虚拟环境已创建（项目根目录下的venv文件夹）
- [ ] 依赖包已安装（运行脚本会自动检查）
- [ ] 有足够的磁盘空间（至少5GB用于缓存）

## 首次运行

首次运行需要从Wind获取大量数据，预计耗时：

- 数据获取：30-60分钟
- 配对筛选：10-20分钟
- 协整检验：30-60分钟
- **总耗时**：约1-2小时

**建议**：首次运行可以在晚上或周末进行。

## 后续运行

使用缓存后，后续运行速度显著提升：

- 数据获取：5-10分钟（使用缓存）
- 配对筛选：10-20分钟
- 协整检验：30-60分钟
- **总耗时**：约45-90分钟

## 查看结果

运行完成后，查看以下文件：

1. **pairs_result_top100.csv** - Excel打开，查看前100名配对
2. **summary_report.txt** - 记事本打开，查看统计报告
3. **pairs_trading.log** - 查看详细日志（如有问题）

## 中断恢复

如果中途需要中断（Ctrl+C）：

- ✅ 进度会自动保存
- ✅ 下次运行会从中断处继续
- ✅ 已完成的部分不会重复计算

## 常见问题速查

### Q: Wind API报错

**A**: 检查Wind终端是否登录，尝试重启Wind终端。

### Q: 内存不足

**A**: 修改`config.py`中的`BATCH_SIZE`参数（改小），如500。

### Q: 处理太慢

**A**: 这是正常的，首次运行需要大量计算。可以：
- 减小`STOCK_TOP_N`（如改为1000）
- 提高`MIN_CORRELATION`（如改为0.90）

### Q: 结果太少

**A**: 放宽条件，修改`config.py`：
- `MIN_CORRELATION = 0.80`（降低）
- `MAX_SPREAD_VOLATILITY = 0.30`（增大）
- `MAX_HALF_LIFE = 80`（增大）

### Q: 想重新开始

**A**: 删除缓存和进度文件：
```bash
# Windows
del cache\*.pkl
del cache\*.csv

# Linux/Mac
rm cache/*.pkl
rm cache/*.csv
```

## 进阶使用

### 修改筛选条件

编辑 `config.py` 文件：

```python
# 示例：更严格的筛选
class PairScreenConfig:
    MIN_CORRELATION = 0.90  # 提高相关系数要求
    MAX_SPREAD_VOLATILITY = 0.20  # 降低波动率上限

class OUModelConfig:
    MAX_HALF_LIFE = 40  # 缩短半衰期上限
    MIN_HALF_LIFE = 10  # 提高半衰期下限
```

### 单独测试模块

测试数据获取（不运行完整流程）：

```bash
# 激活虚拟环境
.\venv\Scripts\activate

# 测试数据获取
cd src\配对全市场
python data_fetcher.py
```

### 清理缓存

```python
# 在Python中运行
from cache_manager import get_cache_manager

cm = get_cache_manager()
cm.clear_expired()  # 清理过期缓存
cm.clear_all()      # 清空所有缓存
```

## 获取帮助

1. 查看完整文档：`README.md`
2. 查看执行计划：`plan.md`
3. 查看日志文件：`pairs_trading.log`
4. 检查配置文件：`config.py`

## 下一步

运行成功后，建议：

1. 分析前10名配对的特征
2. 查看半衰期分布
3. 根据需求调整筛选条件
4. 定期（每周）重新运行扫描

---

**提示**：首次运行建议在非交易时间进行，避免影响Wind终端的其他使用。

