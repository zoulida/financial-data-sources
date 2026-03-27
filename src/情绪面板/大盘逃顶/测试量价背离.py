"""
测试量价背离数据获取
诊断为什么没有显示得分
"""

def test_xtquant():
    """测试 XtQuant 数据源"""
    print("=" * 70)
    print("测试 XtQuant - 量价背离数据获取")
    print("=" * 70)
    
    try:
        from xtquant import xtdata
        print("\n[1/3] ✓ XtQuant 已安装")
        
        # 上证指数代码
        index_code = '000001.SH'
        
        print(f"\n[2/3] 正在获取上证指数数据 ({index_code})...")
        
        # 获取最近6个交易日的行情数据
        data = xtdata.get_market_data_ex(
            field_list=['close', 'volume'],
            stock_list=[index_code],
            period='1d',
            count=6
        )
        
        if data and 'close' in data and 'volume' in data:
            print(f"  ✓ 数据获取成功")
            
            close_prices = data['close'][index_code]
            volumes = data['volume'][index_code]
            
            print(f"\n[3/3] 数据解析:")
            print(f"  收盘价数据点数: {len(close_prices)}")
            print(f"  成交量数据点数: {len(volumes)}")
            
            if len(close_prices) >= 6 and len(volumes) >= 6:
                print(f"\n  最近6日数据:")
                print(f"  {'日期':>12s} | {'收盘价':>10s} | {'成交量(万手)':>15s} | {'涨跌':>8s} | {'量变':>8s}")
                print("-" * 70)
                
                for i in range(-6, 0):
                    idx = len(close_prices) + i
                    close = close_prices.iloc[idx]
                    volume = volumes.iloc[idx] / 10000  # 转换为万手
                    date = close_prices.index[idx].strftime('%Y-%m-%d')
                    
                    if idx > 0:
                        price_change = (close - close_prices.iloc[idx-1]) / close_prices.iloc[idx-1] * 100
                        volume_change = (volume - volumes.iloc[idx-1]/10000) / (volumes.iloc[idx-1]/10000) * 100
                        print(f"  {date} | {close:>10.2f} | {volume:>15.2f} | {price_change:>+7.2f}% | {volume_change:>+7.2f}%")
                    else:
                        print(f"  {date} | {close:>10.2f} | {volume:>15.2f} | {'--':>8s} | {'--':>8s}")
                
                # 检查量价背离
                print(f"\n  量价背离检测（最近5日）:")
                print(f"  {'日期':>12s} | {'收盘涨':>8s} | {'量萎缩≥20%':>12s} | {'量价背离':>10s}")
                print("-" * 60)
                
                divergence_days = 0
                for i in range(1, 6):
                    idx = -(i)
                    date = close_prices.index[idx].strftime('%Y-%m-%d')
                    
                    # 当日收盘价涨
                    price_up = close_prices.iloc[-i] > close_prices.iloc[-(i+1)]
                    
                    # 成交量较前日萎缩≥20%
                    volume_shrink_rate = (volumes.iloc[-(i+1)] - volumes.iloc[-i]) / volumes.iloc[-(i+1)]
                    volume_shrink = volume_shrink_rate >= 0.20
                    
                    is_divergence = price_up and volume_shrink
                    if is_divergence:
                        divergence_days += 1
                    
                    print(f"  {date} | {'✓' if price_up else '✗':>8s} | {f'{volume_shrink_rate*100:+.1f}%' if price_up else '--':>12s} | {'✓ 是' if is_divergence else '✗ 否':>10s}")
                
                # 计算得分
                score = 0.0
                if divergence_days == 1:
                    score = 1.0
                elif divergence_days >= 2:
                    score = 1.0 + (divergence_days - 1) * 0.5
                
                print(f"\n  量价背离天数: {divergence_days}")
                print(f"  得分: {score:.2f}")
                
                print("\n✅ XtQuant 数据源测试完成！")
            else:
                print(f"  ✗ 数据不足：需要至少6个交易日数据")
        else:
            print(f"  ✗ 数据获取失败或格式错误")
            
    except ImportError:
        print(f"\n✗ XtQuant 未安装")
        print(f"  提示：请安装 XtQuant 库")
    except Exception as e:
        print(f"\n✗ XtQuant 测试失败: {e}")
        import traceback
        traceback.print_exc()


def test_akshare():
    """测试 akshare 数据源"""
    print("\n" + "=" * 70)
    print("测试 akshare - 量价背离数据获取")
    print("=" * 70)
    
    try:
        import akshare as ak
        print("\n[1/3] ✓ akshare 已安装")
        
        print(f"\n[2/3] 正在获取上证指数数据...")
        
        # 获取上证指数历史数据
        df = ak.stock_zh_index_daily(symbol="sh000001")
        
        if df is not None and len(df) >= 6:
            print(f"  ✓ 数据获取成功")
            
            df = df.sort_values('date', ascending=False).head(6)
            df = df.sort_values('date', ascending=True)
            
            print(f"\n[3/3] 数据解析:")
            print(f"  数据点数: {len(df)}")
            
            print(f"\n  最近6日数据:")
            print(f"  {'日期':>12s} | {'收盘价':>10s} | {'成交量(万手)':>15s} | {'涨跌':>8s} | {'量变':>8s}")
            print("-" * 70)
            
            for i in range(len(df)):
                row = df.iloc[i]
                date = row['date'].strftime('%Y-%m-%d') if hasattr(row['date'], 'strftime') else str(row['date'])
                close = row['close']
                volume = row['volume'] / 10000
                
                if i > 0:
                    prev = df.iloc[i-1]
                    price_change = (close - prev['close']) / prev['close'] * 100
                    volume_change = (volume - prev['volume']/10000) / (prev['volume']/10000) * 100
                    print(f"  {date} | {close:>10.2f} | {volume:>15.2f} | {price_change:>+7.2f}% | {volume_change:>+7.2f}%")
                else:
                    print(f"  {date} | {close:>10.2f} | {volume:>15.2f} | {'--':>8s} | {'--':>8s}")
            
            # 检查量价背离
            print(f"\n  量价背离检测（最近5日）:")
            print(f"  {'日期':>12s} | {'收盘涨':>8s} | {'量萎缩≥20%':>12s} | {'量价背离':>10s}")
            print("-" * 60)
            
            divergence_days = 0
            for i in range(1, 6):
                row = df.iloc[i]
                prev = df.iloc[i-1]
                date = row['date'].strftime('%Y-%m-%d') if hasattr(row['date'], 'strftime') else str(row['date'])
                
                # 当日收盘价涨
                price_up = row['close'] > prev['close']
                
                # 成交量萎缩≥20%
                volume_shrink_rate = (prev['volume'] - row['volume']) / prev['volume']
                volume_shrink = volume_shrink_rate >= 0.20
                
                is_divergence = price_up and volume_shrink
                if is_divergence:
                    divergence_days += 1
                
                print(f"  {date} | {'✓' if price_up else '✗':>8s} | {f'{volume_shrink_rate*100:+.1f}%' if price_up else '--':>12s} | {'✓ 是' if is_divergence else '✗ 否':>10s}")
            
            # 计算得分
            score = 0.0
            if divergence_days == 1:
                score = 1.0
            elif divergence_days >= 2:
                score = 1.0 + (divergence_days - 1) * 0.5
            
            print(f"\n  量价背离天数: {divergence_days}")
            print(f"  得分: {score:.2f}")
            
            print("\n✅ akshare 数据源测试完成！")
        else:
            print(f"  ✗ 数据不足：需要至少6个交易日数据")
            
    except ImportError:
        print(f"\n✗ akshare 未安装")
        print(f"  提示：pip install akshare")
    except Exception as e:
        print(f"\n✗ akshare 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("\n量价背离数据源测试")
    print("=" * 70)
    print("用于诊断为什么没有显示得分")
    print("=" * 70)
    
    # 测试 XtQuant
    test_xtquant()
    
    # 测试 akshare
    test_akshare()
    
    print("\n" + "=" * 70)
    print("测试完成！")
    print("=" * 70)
    print("\n提示:")
    print("  1. 如果 XtQuant 测试失败，会自动使用 akshare")
    print("  2. 如果两者都失败，将返回 0 分")
    print("  3. 最新版本(v1.0.5)已修复：数据获取失败时也会显示得分")

