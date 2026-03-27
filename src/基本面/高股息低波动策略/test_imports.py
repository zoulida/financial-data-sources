"""测试脚本 - 验证所有模块是否可以正确导入."""

import sys
from pathlib import Path


def test_imports() -> bool:
    """测试所有模块导入."""
    print("=" * 80)
    print("模块导入测试")
    print("=" * 80)
    
    success = True
    
    # 测试Wind
    try:
        from WindPy import w
        print("✓ WindPy 导入成功")
    except ImportError as e:
        print(f"✗ WindPy 导入失败: {e}")
        success = False
    
    # 测试基础库
    try:
        import pandas as pd
        import numpy as np
        from tqdm import tqdm
        print("✓ pandas, numpy, tqdm 导入成功")
    except ImportError as e:
        print(f"✗ 基础库导入失败: {e}")
        success = False
    
    # 测试本地模块
    try:
        from config import Config
        print("✓ config 模块导入成功")
    except ImportError as e:
        print(f"✗ config 模块导入失败: {e}")
        success = False
    
    try:
        from wind_data_fetcher import WindDataFetcher
        print("✓ wind_data_fetcher 模块导入成功")
    except ImportError as e:
        print(f"✗ wind_data_fetcher 模块导入失败: {e}")
        success = False
    
    try:
        from market_data_fetcher import MarketDataFetcher
        print("✓ market_data_fetcher 模块导入成功")
    except ImportError as e:
        print(f"✗ market_data_fetcher 模块导入失败: {e}")
        print("  提示: 请检查合并下载数据模块路径")
        # 这个失败是可以接受的，因为依赖外部模块
    
    try:
        from stock_filter import StockFilter
        print("✓ stock_filter 模块导入成功")
    except ImportError as e:
        print(f"✗ stock_filter 模块导入失败: {e}")
        success = False
    
    try:
        from scoring import StockScorer
        print("✓ scoring 模块导入成功")
    except ImportError as e:
        print(f"✗ scoring 模块导入失败: {e}")
        success = False
    
    try:
        from main import HighDividendLowVolatilitySelector
        print("✓ main 模块导入成功")
    except ImportError as e:
        print(f"✗ main 模块导入失败: {e}")
        success = False
    
    print("\n" + "=" * 80)
    if success:
        print("✓ 所有核心模块导入成功！")
    else:
        print("✗ 部分模块导入失败，请检查依赖安装")
    print("=" * 80)
    
    return success


def test_wind_connection() -> bool:
    """测试Wind连接."""
    print("\n" + "=" * 80)
    print("Wind连接测试")
    print("=" * 80)
    
    try:
        from WindPy import w
        w.start()
        if w.isconnected():
            print("✓ Wind已连接")
            w.stop()
            return True
        else:
            print("✗ Wind未连接，请启动Wind终端并登录")
            return False
    except Exception as e:
        print(f"✗ Wind测试失败: {e}")
        return False


def test_config() -> bool:
    """测试配置."""
    print("\n" + "=" * 80)
    print("配置测试")
    print("=" * 80)
    
    try:
        from config import Config
        config = Config()
        config.print_config()
        print("\n✓ 配置加载成功")
        return True
    except Exception as e:
        print(f"✗ 配置测试失败: {e}")
        return False


def main() -> None:
    """运行所有测试."""
    print("\n" + "=" * 80)
    print("高股息低波动股票筛选系统 - 环境测试")
    print("=" * 80)
    print()
    
    results = []
    
    # 测试导入
    results.append(("模块导入", test_imports()))
    
    # 测试Wind连接
    results.append(("Wind连接", test_wind_connection()))
    
    # 测试配置
    results.append(("配置加载", test_config()))
    
    # 总结
    print("\n" + "=" * 80)
    print("测试总结")
    print("=" * 80)
    for name, result in results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"{name}: {status}")
    
    all_passed = all(r for _, r in results)
    print("\n" + "=" * 80)
    if all_passed:
        print("✓ 所有测试通过！系统已就绪。")
        print("\n可以运行以下命令开始使用:")
        print("  python main.py")
        print("  python run.py")
    else:
        print("✗ 部分测试失败，请解决问题后再运行系统。")
        print("\n常见问题:")
        print("1. 安装依赖: pip install -r requirements.txt")
        print("2. 启动Wind终端并登录")
        print("3. 配置XtQuant（参考文档）")
    print("=" * 80)


if __name__ == "__main__":
    main()

