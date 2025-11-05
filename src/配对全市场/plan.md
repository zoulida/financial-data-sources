# A股配对交易全市场扫描框架

## 核心要求
- **协整显著性**: Engle-Granger p < 0.05
- **回归速度**: OU半衰期 < 60个交易日
- **评分公式**: Score = 100×(1-p) + 50×(1-H/60)
- **输出范围**: Score前100名的配对

## 实施步骤

### 1. 创建项目结构
在 `src/配对全市场/` 目录下创建完整的项目结构：
```
src/配对全市场/
├── config.py              # 配置文件
├── data_fetcher.py        # 数据获取模块
├── cache_manager.py       # 缓存管理模块
├── pair_screener.py       # 配对初筛模块
├── cointegration.py       # 协整检验模块
├── ou_estimator.py        # OU半衰期估计模块
├── scoring.py             # 评分排序模块
├── progress_manager.py    # 进度管理模块
├── main.py                # 主程序入口
├── README.md              # 项目说明文档
└── cache/                 # 缓存目录
```

### 2. 配置模块 (config.py)
定义系统配置参数：
- Wind Token配置
- 数据筛选阈值（市值前2000、成交量>1000万、剩余规模>5亿）
- 协整检验参数（p值阈值0.05）
- OU模型参数（半衰期阈值60天）
- 初筛参数（相关系数≥0.85、价差波动率<25%）
- 缓存设置（缓存周期7天）
- 输出配置（前100名）

### 3. 数据获取模块 (data_fetcher.py)
实现三类资产的数据获取：

**股票数据**:
- 从`中证全指成分股_20251028.csv`读取股票列表
- 使用Wind API `w.wss()`获取总市值字段`mkt_cap_ard`
- 按市值排序取前2000只
- 使用Wind API `w.wsd()`获取250日收盘价（后复权）

**ETF数据**:
- 使用Wind API `w.wset("sectorconstituent")`获取ETF列表
- 通过`w.wss()`获取日均成交额字段`avg_amount_20d`
- 筛选日均成交额>1000万的ETF
- 获取250日收盘价

**可转债数据**:
- 使用Wind API `w.wset("convertiblebondswap")`获取可转债列表
- 通过`w.wss()`获取剩余规模字段`carryingvalue`和日均成交额
- 筛选剩余规模>5亿且成交>1000万的可转债
- 获取250日收盘价

### 4. 缓存管理模块 (cache_manager.py)
使用`shelve`或`pickle`实现数据缓存：
- 保存股票/ETF/可转债列表（有效期7天）
- 保存价格数据（有效期7天）
- 检查缓存时效性，过期自动刷新
- 缓存键格式：`stock_universe_20251103`、`price_data_000001.SZ_20251103`

### 5. 配对初筛模块 (pair_screener.py)
快速筛选候选配对（减少90%计算量）：
- 计算两两组合的250日Pearson相关系数
- 要求 ρ ≥ 0.85
- 计算价差 = log(P1) - log(P2)
- 计算价差年化波动率，要求 < 25%
- 检查双方日均成交额均 > 1000万
- 返回通过初筛的配对列表

### 6. 协整检验模块 (cointegration.py)
实现Engle-Granger两步法：
```python
from statsmodels.tsa.stattools import coint

def test_cointegration(x, y):
    # x, y为对数收盘价
    score, p_value, _ = coint(y, x)
    # 计算β系数
    beta = np.linalg.lstsq(x[:,None], y, rcond=None)[0][0]
    # 构造价差
    spread = y - beta * x
    return p_value, beta, spread
```
- 要求 p_value < 0.05
- 返回β系数和价差序列

### 7. OU半衰期估计模块 (ou_estimator.py)
使用Kalman Filter估计OU参数：
```python
from pykalman import KalmanFilter

def calculate_half_life(spread):
    # Kalman Filter平滑
    kf = KalmanFilter(
        transition_matrices=[[1]],
        observation_matrices=[[1]],
        initial_state_mean=0,
        initial_state_covariance=1,
        observation_covariance=1,
        transition_covariance=0.01
    )
    z_filt, _ = kf.filter(spread.values)
    z_filt = z_filt.flatten()
    
    # OLS求φ
    x = z_filt[:-1]
    y = z_filt[1:]
    phi = np.linalg.lstsq(x[:,None], y, rcond=None)[0][0]
    
    # 计算半衰期
    if abs(phi) >= 1:
        return np.inf
    half_life = -np.log(2) / np.log(abs(phi))
    return half_life
```
- 要求半衰期 < 60交易日
- 返回半衰期值

### 8. 评分排序模块 (scoring.py)
计算配对得分并排序：
```python
def calculate_score(p_value, half_life):
    score = 100 * max(0, 1 - p_value) + 50 * max(0, 1 - half_life/60)
    return score
```
- 对所有通过检验的配对计算Score
- 按Score降序排列
- 取前100名

### 9. 进度管理模块 (progress_manager.py)
实现批量处理和进度保存：
- 将所有候选配对分批处理（每批1000对）
- 每批完成后保存中间结果到`progress.pkl`
- 保存已完成的配对ID列表
- 启动时检查是否有未完成的任务
- 支持从上次中断处继续运行
- 最终合并所有批次结果

### 10. 主程序入口 (main.py)
整合所有模块的执行流程：
1. 加载配置
2. 检查缓存并获取股票/ETF/可转债池
3. 合并为统一池子（N个标的）
4. 生成C(N,2)个候选配对
5. 初筛（相关性+波动率+成交量）
6. 检查进度文件，确定待处理配对
7. 批量处理：
   - 协整检验
   - OU半衰期计算
   - 评分
8. 保存进度
9. 输出前100名配对到CSV文件
10. 生成统计报告

### 11. 依赖安装
在`requirements.txt`中添加必要的依赖：
- WindPy
- pandas
- numpy
- statsmodels
- pykalman
- tqdm（进度条显示）

### 12. 项目文档 (README.md)
编写完整的使用文档：
- 项目简介
- 快速开始指南
- 配置说明
- 运行示例
- 输出文件说明
- 常见问题

## 关键技术点

1. **数据获取**: 使用Wind API的`w.wss()`和`w.wsd()`接口
2. **缓存策略**: shelve模块存储，7天有效期
3. **协整检验**: statsmodels的`coint()`函数
4. **OU估计**: pykalman的KalmanFilter + OLS回归
5. **进度管理**: pickle保存中间状态，支持断点续传
6. **批量处理**: 分批次处理，避免内存溢出

## 预期输出

### pairs_result_top100.csv
| 标的A | 标的B | Beta | Score | 半衰期 | p_value | 相关系数 |
|-------|-------|------|-------|--------|---------|----------|
| 000001.SZ | 000002.SZ | 1.23 | 98.5 | 25.3 | 0.002 | 0.92 |
| ... | ... | ... | ... | ... | ... | ... |

### summary_report.txt
- 初始池子规模
- 初筛通过数量
- 协整通过数量
- 半衰期通过数量
- 最终配对数量
- 处理时间统计

