# 数据获取卡顿问题诊断指南

## 问题描述
在批量获取股票数据时，程序可能会卡在某只股票上，没有报错也不重试。

## 已实施的解决方案

### 1. 超时和重试机制
`get_day_data_with_timeout()` 函数已经实现：
- **超时时间**: 2秒
- **重试次数**: 2次
- **重试间隔**: 1秒

### 2. 详细日志追踪
现在每次数据获取都会输出详细日志：
```
HH:MM:SS - INFO - ===== 处理进度: 1419/3741 - 300390.SZ =====
HH:MM:SS - INFO - [开始] 获取 300390.SZ 数据（尝试 1/2）
HH:MM:SS - INFO - [成功] 300390.SZ 耗时 0.52秒
```

如果超时会显示：
```
HH:MM:SS - WARNING - [超时] 300390.SZ 在 2.00秒后超时
HH:MM:SS - WARNING - [重试] 300390.SZ 将在1秒后重试
HH:MM:SS - ERROR - [失败] 300390.SZ 数据获取超时（2次尝试后放弃）
HH:MM:SS - ERROR - **超时跳过** 300390.SZ: ...
```

## 如何查看日志

### 运行中查看
日志会实时输出到控制台，格式为：
- `[开始]` - 开始获取某只股票
- `[成功]` - 成功获取
- `[超时]` - 发生超时
- `[重试]` - 开始重试
- `[失败]` - 最终失败
- `**超时跳过**` - 跳过该股票继续处理

### 识别卡顿位置
如果程序卡住，查看最后一条日志：
1. 如果看到 `[开始] 获取 XXX.XX` 但没有后续日志 → 说明卡在该股票的 `getDayData` 调用中
2. 如果超时机制没有生效 → 可能是底层C扩展或网络库的阻塞

## 诊断工具

### 测试单个股票
使用 `test_single_stock.py` 测试特定股票：

```bash
# 测试默认股票列表
python test_single_stock.py

# 测试指定股票
python test_single_stock.py 300390.SZ
```

这个脚本会：
- 显示详细的时间戳
- 捕获所有异常
- 打印完整的错误堆栈

## 可能的原因

### 1. 底层阻塞（最可能）
`getDayData` 内部可能调用了：
- XtQuant的C扩展（无法被Python线程超时中断）
- 网络请求阻塞
- 文件I/O阻塞

### 2. 装饰器问题
检查以下装饰器是否导致阻塞：
- `@CSV_data` - CSV文件写入
- `@shelve_me_today` - Shelve缓存操作
- `@lru_cache` - 内存缓存

### 3. 磁盘I/O问题
大量文件读写可能导致：
- 磁盘满
- 权限问题
- 防病毒软件扫描

## 解决建议

### 短期方案
1. **跳过问题股票**: 记录卡顿的股票代码，在后续运行中先跳过
2. **减少并发**: 不使用多线程，确保单线程串行执行
3. **增加超时**: 如果网络慢，可以增加超时时间

### 长期方案
1. **使用进程池**: 进程可以被强制终止（但序列化开销大）
2. **修改底层函数**: 在 `getDayData` 内部添加超时控制
3. **分批处理**: 将大批量分成小批次，每批处理完保存进度

## 修改配置

### 调整超时时间
在 `market_data_fetcher.py` 中修改：
```python
df = get_day_data_with_timeout(
    stock_code=code,
    start_date=start_date,
    end_date=end_date,
    is_download=0,
    dividend_type="front",
    timeout=5,  # 改为5秒
    max_retries=3  # 改为3次
)
```

### 关闭日志（如果输出太多）
在 `market_data_fetcher.py` 开头修改：
```python
logging.basicConfig(
    level=logging.WARNING,  # 改为WARNING只显示警告和错误
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)
```

## 紧急处理

### 如果程序卡住
1. 查看最后一条日志，记录卡住的股票代码
2. 按 `Ctrl+C` 中断程序
3. 将卡住的股票代码加入黑名单
4. 重新运行，在处理前过滤掉黑名单股票

### 创建黑名单
```python
# 在 main.py 或 market_data_fetcher.py 中
BLACKLIST = ['300390.SZ', '600123.SH']  # 卡顿的股票

# 过滤股票列表
filtered_stocks = [s for s in stock_codes if s not in BLACKLIST]
```

## 联系与反馈
如果问题持续存在，请记录：
1. 卡住时的最后日志
2. 卡住的股票代码
3. 系统环境（Windows/Linux, Python版本）
4. XtQuant版本

