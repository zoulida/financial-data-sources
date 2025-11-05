"""
配对交易全市场扫描系统 - 配置文件

定义所有系统参数，包括数据筛选阈值、协整检验参数、OU模型参数等。
"""

# ==================== Wind API 配置 ====================
# Wind API 会自动使用已登录的终端，无需Token

# ==================== 数据筛选配置 ====================
class DataFilterConfig:
    """数据筛选相关配置
    
    注意：所有金额单位均为元（人民币）
    Wind API返回的数据单位为亿元，在data_fetcher中已自动转换为元
    """
    
    # 股票筛选
    STOCK_TOP_N = 2000  # 按市值排序取前N只股票
    
    # ETF筛选
    ETF_MIN_AVG_AMOUNT = 10000000  # ETF日均成交额最小值（元，即1000万元 = 0.1亿元）
    
    # 可转债筛选
    CONVERTIBLE_BOND_MIN_SIZE = 500000000  # 可转债剩余规模最小值（元，即5亿元）
    CONVERTIBLE_BOND_MIN_AMOUNT = 10000000  # 可转债日均成交额最小值（元，即1000万元 = 0.1亿元）
    
    # 通用成交额门槛
    MIN_AVG_AMOUNT = 10000000  # 日均成交额最小值（元，即1000万元 = 0.1亿元）


# ==================== 历史数据配置 ====================
class HistoricalDataConfig:
    """历史数据获取相关配置"""
    
    LOOKBACK_DAYS = 240  # 历史数据回溯天数
    DIVIDEND_TYPE = 'front'  # 复权类型：front=前复权, back=后复权, none=不复权
    
    # 日期模式配置
    DATE_MODE = 'manual'  # 日期模式：'auto'=自动模式（使用get_date_range）, 'manual'=手动模式（使用配置的日期）
    START_DATE = '20241101'  # 手动模式下的开始日期（YYYYMMDD格式）
    END_DATE = '20251103'  # 手动模式下的结束日期（YYYYMMDD格式）


# ==================== 配对初筛配置 ====================
class PairScreenConfig:
    """配对初筛相关配置"""
    
    MIN_CORRELATION = 0.85  # Pearson相关系数最小值
    MAX_SPREAD_VOLATILITY = 0.25  # 价差年化波动率最大值（25%）
    MIN_DATA_POINTS = 200  # 最少有效数据点数


# ==================== 协整检验配置 ====================
class CointegrationConfig:
    """协整检验相关配置"""
    
    MAX_P_VALUE = 0.05  # 协整检验p值最大值
    METHOD = 'Engle-Granger'  # 协整检验方法


# ==================== OU模型配置 ====================
class OUModelConfig:
    """OU（Ornstein-Uhlenbeck）模型相关配置"""
    
    MAX_HALF_LIFE = 100000000000  # 半衰期最大值（交易日）
    MIN_HALF_LIFE = 0   # 半衰期最小值（交易日），太短可能是误判
    OPTIMAL_HALF_LIFE_MIN = 15  # 优选半衰期最小值
    OPTIMAL_HALF_LIFE_MAX = 40  # 优选半衰期最大值
    
    # Kalman Filter参数
    KF_OBSERVATION_COVARIANCE = 1.0
    KF_TRANSITION_COVARIANCE = 0.01


# ==================== 评分配置 ====================
class ScoringConfig:
    """评分排序相关配置"""
    
    P_VALUE_WEIGHT = 100  # p值权重
    HALF_LIFE_WEIGHT = 50  # 半衰期权重
    TOP_N = 100  # 输出前N名配对


# ==================== 进度管理配置 ====================
class ProgressConfig:
    """进度管理相关配置"""
    
    BATCH_SIZE = 1000  # 每批处理的配对数量
    PROGRESS_FILE = 'cache/progress.pkl'  # 进度文件路径
    SAVE_INTERVAL = 5  # 每处理N批保存一次进度


# ==================== 缓存配置 ====================
class CacheConfig:
    """缓存相关配置"""
    
    CACHE_DAYS = 7  # 缓存有效期（天）
    CACHE_DIR = 'cache'  # 缓存目录
    USE_SHELVE = True  # 是否使用shelve装饰器缓存


# ==================== 输出配置 ====================
class OutputConfig:
    """输出相关配置"""
    
    RESULT_FILE = 'pairs_result_top100.csv'  # 结果文件名
    SUMMARY_FILE = 'summary_report.txt'  # 汇总报告文件名
    LOG_FILE = 'pairs_trading.log'  # 日志文件名
    
    # CSV输出列
    OUTPUT_COLUMNS = [
        'symbol_A', 'symbol_B', 'name_A', 'name_B', 
        'beta', 'score', 'half_life', 'p_value', 
        'correlation', 'spread_volatility', 'data_points'
    ]


# ==================== 系统配置 ====================
class SystemConfig:
    """系统运行相关配置"""
    
    LOG_LEVEL = 'INFO'  # 日志级别：DEBUG, INFO, WARNING, ERROR
    SHOW_PROGRESS_BAR = True  # 是否显示进度条
    MAX_WORKERS = 1  # 最大并行工作线程数（暂时使用单线程）
    ERROR_RETRY_TIMES = 3  # 错误重试次数
    ERROR_RETRY_DELAY = 2  # 错误重试延迟（秒）
    
    # 调试模式配置
    DEBUG_MODE = True  # 是否启用调试模式（采样配对）
    DEBUG_SAMPLE_RATIO = 1  # 调试采样比例（0.01表示只处理1%的配对，0.1表示10%，1.0表示全部）
    DEBUG_SAMPLE_SEED = 42  # 随机采样种子（固定种子保证可重复）


# ==================== 所有配置导出 ====================
class Config:
    """统一配置类"""
    
    DataFilter = DataFilterConfig
    HistoricalData = HistoricalDataConfig
    PairScreen = PairScreenConfig
    Cointegration = CointegrationConfig
    OUModel = OUModelConfig
    Scoring = ScoringConfig
    Progress = ProgressConfig
    Cache = CacheConfig
    Output = OutputConfig
    System = SystemConfig


# 默认配置实例
config = Config()


if __name__ == '__main__':
    """配置测试"""
    print("="*80)
    print("配对交易全市场扫描系统 - 配置信息")
    print("="*80)
    
    print("\n数据筛选配置:")
    print(f"  股票池: 按市值前 {Config.DataFilter.STOCK_TOP_N} 只")
    print(f"  ETF日均成交额: >= {Config.DataFilter.ETF_MIN_AVG_AMOUNT/1e7:.0f} 亿")
    print(f"  可转债剩余规模: >= {Config.DataFilter.CONVERTIBLE_BOND_MIN_SIZE/1e8:.1f} 亿")
    
    print("\n历史数据配置:")
    print(f"  回溯天数: {Config.HistoricalData.LOOKBACK_DAYS} 天")
    print(f"  复权类型: {Config.HistoricalData.DIVIDEND_TYPE}")
    print(f"  日期模式: {Config.HistoricalData.DATE_MODE}")
    if Config.HistoricalData.DATE_MODE == 'manual':
        print(f"  开始日期: {Config.HistoricalData.START_DATE}")
        print(f"  结束日期: {Config.HistoricalData.END_DATE}")
    
    print("\n配对初筛配置:")
    print(f"  相关系数: >= {Config.PairScreen.MIN_CORRELATION}")
    print(f"  价差波动率: <= {Config.PairScreen.MAX_SPREAD_VOLATILITY*100:.0f}%")
    
    print("\n协整检验配置:")
    print(f"  p值阈值: < {Config.Cointegration.MAX_P_VALUE}")
    print(f"  检验方法: {Config.Cointegration.METHOD}")
    
    print("\nOU模型配置:")
    print(f"  半衰期范围: {Config.OUModel.MIN_HALF_LIFE}-{Config.OUModel.MAX_HALF_LIFE} 天")
    print(f"  优选范围: {Config.OUModel.OPTIMAL_HALF_LIFE_MIN}-{Config.OUModel.OPTIMAL_HALF_LIFE_MAX} 天")
    
    print("\n评分配置:")
    print(f"  Score公式: {Config.Scoring.P_VALUE_WEIGHT}×(1-p) + {Config.Scoring.HALF_LIFE_WEIGHT}×(1-H/60)")
    print(f"  输出数量: 前 {Config.Scoring.TOP_N} 名")
    
    print("\n进度管理配置:")
    print(f"  批处理大小: {Config.Progress.BATCH_SIZE} 对/批")
    print(f"  保存间隔: 每 {Config.Progress.SAVE_INTERVAL} 批")
    
    print("\n系统配置:")
    print(f"  日志级别: {Config.System.LOG_LEVEL}")
    print(f"  调试模式: {'启用' if Config.System.DEBUG_MODE else '禁用'}")
    if Config.System.DEBUG_MODE:
        print(f"  采样比例: {Config.System.DEBUG_SAMPLE_RATIO*100:.1f}%")
        print(f"  随机种子: {Config.System.DEBUG_SAMPLE_SEED}")
    
    print("="*80)

