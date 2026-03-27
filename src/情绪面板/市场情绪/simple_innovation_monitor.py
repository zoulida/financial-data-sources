#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化版创新高创新低监控程序
直接使用Wind API获取创新高和创新低的股票数量

作者: AI Assistant
创建时间: 2025-01-29
"""

import sys
import os
import pandas as pd

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(project_root)

try:
    from WindPy import w
    WIND_AVAILABLE = True
except ImportError:
    WIND_AVAILABLE = False
    print("警告: WindPy 未安装")

def get_innovation_high_low_count(date=None):
    """
    获取指定日期的创新高和创新低股票数量
    
    Args:
        date: 日期，格式: '2025-10-29'，如果为None则使用今天
        
    Returns:
        dict: 包含创新高和创新低数量的字典
    """
    if not WIND_AVAILABLE:
        print("WindPy未安装，无法获取数据")
        return None
    
    if date is None:
        from datetime import datetime
        date = datetime.now().strftime('%Y-%m-%d')
    
    try:
        # 初始化Wind
        w.start()
        print(f"正在获取 {date} 的创新高创新低数据...")
        
        # 获取全市场A股股票池（沪深主板+创业板+科创板）
        stock_list = w.wset("sectorconstituent", f"date={date};sectorid=a001010100000000")
        
        if stock_list.ErrorCode != 0:
            print(f"获取股票池失败，错误代码: {stock_list.ErrorCode}")
            return None
        
        if not stock_list.Data or len(stock_list.Data) < 2:
            print("股票池数据为空")
            return None
        
        codes = stock_list.Data[1]  # 股票代码列表
        print(f"成功获取 {len(codes)} 只股票")
        
        # 批量获取创新高/创新低状态
        result = w.wsd(codes, "new_high,new_low", date, date, "")
        
        if result.ErrorCode != 0:
            print(f"获取创新高创新低数据失败，错误代码: {result.ErrorCode}")
            print("可能的原因：")
            print("1. 字段名不正确")
            print("2. 数据权限不足")
            print("3. 日期格式问题")
            return None
        
        if not result.Data or len(result.Data) < 2:
            print("创新高创新低数据为空")
            return None
        
        # 构建DataFrame
        df = pd.DataFrame({
            '代码': result.Codes,
            '创新高': result.Data[0],
            '创新低': result.Data[1]
        }).dropna()
        
        # 统计数量
        new_high_count = df[df['创新高'] == 1].shape[0]
        new_low_count = df[df['创新低'] == 1].shape[0]
        total_stocks = len(df)
        
        # 计算比例
        new_high_ratio = new_high_count / total_stocks * 100
        new_low_ratio = new_low_count / total_stocks * 100
        
        # 创新高创新低同时发生的股票
        both_high_low = df[(df['创新高'] == 1) & (df['创新低'] == 1)].shape[0]
        
        result_data = {
            '日期': date,
            '总股票数': total_stocks,
            '创新高数量': new_high_count,
            '创新低数量': new_low_count,
            '创新高比例': round(new_high_ratio, 2),
            '创新低比例': round(new_low_ratio, 2),
            '同时创新高创新低': both_high_low,
            '创新高股票': df[df['创新高'] == 1]['代码'].tolist()[:10],  # 最多显示10只
            '创新低股票': df[df['创新低'] == 1]['代码'].tolist()[:10]   # 最多显示10只
        }
        
        return result_data
        
    except Exception as e:
        print(f"获取数据时发生错误: {e}")
        return None
    
    finally:
        try:
            w.stop()
        except:
            pass

def main():
    """主函数"""
    print("=" * 60)
    print("创新高创新低监控程序（简化版）")
    print("=" * 60)
    
    # 获取今日数据
    result = get_innovation_high_low_count()
    
    if result:
        print(f"\n📊 {result['日期']} 创新高创新低统计")
        print("-" * 40)
        print(f"总股票数: {result['总股票数']:,} 只")
        print(f"创新高数量: {result['创新高数量']:,} 只 ({result['创新高比例']}%)")
        print(f"创新低数量: {result['创新低数量']:,} 只 ({result['创新低比例']}%)")
        print(f"同时创新高创新低: {result['同时创新高创新低']} 只")
        
        # 市场情绪判断
        if result['创新高比例'] > 10:
            sentiment = "极度乐观"
        elif result['创新高比例'] > 5:
            sentiment = "乐观"
        elif result['创新低比例'] > 10:
            sentiment = "极度悲观"
        elif result['创新低比例'] > 5:
            sentiment = "悲观"
        else:
            sentiment = "中性"
        
        print(f"\n市场情绪: {sentiment}")
        
        # 显示创新高股票
        if result['创新高数量'] > 0:
            print(f"\n创新高股票（前10只）:")
            for i, code in enumerate(result['创新高股票'], 1):
                print(f"  {i:2d}. {code}")
        
        # 显示创新低股票
        if result['创新低数量'] > 0:
            print(f"\n创新低股票（前10只）:")
            for i, code in enumerate(result['创新低股票'], 1):
                print(f"  {i:2d}. {code}")
        
        # 保存数据
        try:
            save_dir = os.path.join(project_root, 'data')
            os.makedirs(save_dir, exist_ok=True)
            
            # 创建DataFrame用于保存
            df = pd.DataFrame([result])
            filepath = os.path.join(save_dir, f"innovation_high_low_{result['日期'].replace('-', '')}.csv")
            df.to_csv(filepath, encoding='utf-8-sig', index=False)
            print(f"\n数据已保存到: {filepath}")
        except Exception as e:
            print(f"保存数据失败: {e}")
    
    else:
        print("未能获取到创新高创新低数据")

if __name__ == "__main__":
    main()
