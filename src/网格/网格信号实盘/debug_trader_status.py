#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试trader状态脚本
"""

import sys
import os
# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, project_root)

from src.网格.网格信号实盘.strategy_manager import GridStrategyManager

def debug_trader_status():
    """调试trader状态"""
    print("开始调试trader状态...")
    
    try:
        # 创建策略管理器
        manager = GridStrategyManager(
            stock_code="513030.SH",
            simulate=False,
            strategy_params={
                "qmt_path": r"D:\国金证券QMT交易端\userdata_mini",
                "qmt_account": "8886063599",
                "qmt_account_type": "STOCK",
                "qmt_session_id": 123456,
            }
        )
        
        print("1. 策略管理器创建成功")
        
        # 初始化trader
        manager._init_qmt_trader()
        print("2. 调用_init_qmt_trader完成")
        
        # 检查trader状态
        print(f"3. manager.trader: {manager.trader}")
        if manager.trader:
            print(f"4. trader类型: {type(manager.trader)}")
            print(f"5. trader._connected: {getattr(manager.trader, '_connected', 'No _connected attr')}")
        else:
            print("4. trader为None")
        
        # 创建策略
        setting = {"out_dir": "data/grid", "simulate_mode": False}
        manager.create_strategy("test_strategy", setting)
        print("6. 策略创建完成")
        
        # 检查策略中的manager引用
        if manager.strategy:
            print(f"7. 策略manager引用: {manager.strategy.manager}")
            print(f"8. manager == strategy.manager: {manager == manager.strategy.manager}")
            
            # 检查策略中访问trader的条件
            has_manager = hasattr(manager.strategy, 'manager') and manager.strategy.manager
            has_trader_attr = has_manager and hasattr(manager.strategy.manager, 'trader')
            has_trader = has_trader_attr and manager.strategy.manager.trader
            
            print(f"9. has_manager: {has_manager}")
            print(f"10. has_trader_attr: {has_trader_attr}")
            print(f"11. has_trader: {has_trader}")
            
            if has_trader:
                print("✅ 策略可以正常访问trader")
            else:
                print("❌ 策略无法访问trader")
        
    except Exception as e:
        print(f"调试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_trader_status()
