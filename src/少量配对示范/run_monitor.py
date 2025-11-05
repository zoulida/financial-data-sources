#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
比价监控快速启动脚本
提供简单的命令行界面来运行监控任务
"""

import sys
import os
from datetime import datetime

def print_banner():
    """打印启动横幅"""
    print("=" * 60)
    print("🚀 XtQuant 比价监控系统")
    print("=" * 60)
    print(f"启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

def check_dependencies():
    """检查依赖包"""
    print("🔍 检查依赖包...")
    
    required_packages = ['xtquant', 'pandas', 'numpy', 'statsmodels', 'colorama']
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"✅ {package}")
        except ImportError:
            print(f"❌ {package} - 未安装")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\n⚠️  缺少依赖包: {', '.join(missing_packages)}")
        print("请运行: pip install " + " ".join(missing_packages))
        return False
    
    print("✅ 所有依赖包已安装")
    return True

def check_config():
    """检查配置文件"""
    print("\n🔍 检查配置文件...")
    
    if os.path.exists('config.py'):
        print("✅ 找到配置文件 config.py")
        return True
    else:
        print("⚠️  未找到配置文件 config.py")
        print("请复制 config_example.py 为 config.py 并填入您的配置")
        return False

def run_test():
    """运行测试"""
    print("\n🧪 运行接口测试...")
    try:
        from test_xtdata import main as test_main
        test_main()
        return True
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        return False

def run_monitor():
    """运行监控任务"""
    print("\n📊 启动比价监控...")
    try:
        from monitor_xtdata_ratio import main as monitor_main
        monitor_main()
        return True
    except Exception as e:
        print(f"❌ 监控失败: {str(e)}")
        return False

def main():
    """主函数"""
    print_banner()
    
    # 检查依赖
    if not check_dependencies():
        print("\n❌ 依赖检查失败，请先安装缺少的包")
        return
    
    # 检查配置
    if not check_config():
        print("\n❌ 配置检查失败，请先设置配置文件")
        return
    
    # 显示菜单
    while True:
        print("\n" + "=" * 40)
        print("📋 请选择操作:")
        print("1. 运行接口测试")
        print("2. 运行比价监控")
        print("3. 退出")
        print("=" * 40)
        
        choice = input("请输入选择 (1-3): ").strip()
        
        if choice == '1':
            run_test()
        elif choice == '2':
            run_monitor()
        elif choice == '3':
            print("👋 再见！")
            break
        else:
            print("❌ 无效选择，请重新输入")

if __name__ == "__main__":
    main()
