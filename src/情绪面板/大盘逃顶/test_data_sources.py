"""
数据源测试脚本
用于检查各个数据源是否可用
"""

import sys


def test_wind():
    """测试 Wind API"""
    print("\n[测试 Wind API]")
    try:
        from WindPy import w
        w.start()
        
        # 简单测试：获取上证指数最新收盘价
        from datetime import datetime, timedelta
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        
        data = w.wsd("000001.SH", "close", yesterday, yesterday, "")
        
        if data.ErrorCode == 0:
            print("  ✓ Wind API 可用")
            if data.Data and len(data.Data[0]) > 0:
                print(f"  测试数据: 上证指数收盘价 {data.Data[0][0]:.2f}")
            w.stop()
            return True
        else:
            print(f"  ✗ Wind API 错误码: {data.ErrorCode}")
            w.stop()
            return False
            
    except ImportError:
        print("  ✗ WindPy 未安装")
        print("  提示: 需要先安装Wind终端，然后 pip install WindPy")
        return False
    except Exception as e:
        print(f"  ✗ Wind API 异常: {e}")
        return False


def test_xtquant():
    """测试 XtQuant"""
    print("\n[测试 XtQuant]")
    try:
        from xtquant import xtdata
        
        # 测试：获取上证指数最近1日数据
        data = xtdata.get_market_data_ex(
            field_list=['close'],
            stock_list=['000001.SH'],
            period='1d',
            count=1
        )
        
        if data and 'close' in data:
            print("  ✓ XtQuant 可用")
            print(f"  测试数据: {data['close']['000001.SH'].values[-1]:.2f}")
            return True
        else:
            print("  ✗ XtQuant 返回数据为空")
            return False
            
    except ImportError:
        print("  ✗ xtquant 未安装")
        print("  提示: pip install xtquant")
        return False
    except Exception as e:
        print(f"  ✗ XtQuant 异常: {e}")
        print("  提示: 可能需要先设置token: xtdata.set_token('your_token')")
        return False


def test_akshare():
    """测试 akshare"""
    print("\n[测试 akshare]")
    try:
        import akshare as ak
        
        # 测试1: 获取上证指数日线数据
        df = ak.stock_zh_index_daily(symbol="sh000001")
        
        if df is not None and len(df) > 0:
            print("  ✓ akshare 上证指数接口可用")
            print(f"  最新数据日期: {df.iloc[-1]['date']}")
        else:
            print("  ✗ akshare 上证指数接口返回空数据")
            
        # 测试2: 获取新增投资者数据
        try:
            df_account = ak.stock_em_account()
            if df_account is not None and len(df_account) > 0:
                print("  ✓ akshare 开户数接口可用")
            else:
                print("  ! akshare 开户数接口返回空数据")
        except:
            print("  ! akshare 开户数接口暂不可用（可能需要更新版本）")
            
        return True
            
    except ImportError:
        print("  ✗ akshare 未安装")
        print("  提示: pip install akshare")
        return False
    except Exception as e:
        print(f"  ✗ akshare 异常: {e}")
        return False


def test_eastmoney():
    """测试东方财富网API"""
    print("\n[测试东方财富网API]")
    try:
        import requests
        
        url = "https://datacenter-web.eastmoney.com/api/data/v1/get"
        params = {
            'sortColumns': 'TRADE_DATE',
            'sortTypes': '-1',
            'pageSize': '1',
            'pageNumber': '1',
            'reportName': 'RPT_RZRQ_LSHJ',
            'columns': 'ALL',
            'source': 'WEB',
            'client': 'WEB'
        }
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('result') and data['result'].get('data'):
                print("  ✓ 东方财富网API 可用")
                latest = data['result']['data'][0]
                print(f"  最新日期: {latest.get('TRADE_DATE', 'N/A')}")
                return True
            else:
                print("  ✗ 东方财富网API 返回数据格式异常")
                return False
        else:
            print(f"  ✗ 东方财富网API HTTP错误: {response.status_code}")
            return False
            
    except ImportError:
        print("  ✗ requests 库未安装")
        print("  提示: pip install requests")
        return False
    except Exception as e:
        print(f"  ✗ 东方财富网API 异常: {e}")
        return False


def test_all():
    """测试所有数据源"""
    print("="*70)
    print("数据源可用性测试")
    print("="*70)
    
    results = {
        'Wind API': test_wind(),
        'XtQuant': test_xtquant(),
        'akshare': test_akshare(),
        '东方财富网': test_eastmoney()
    }
    
    print("\n" + "="*70)
    print("测试结果汇总")
    print("="*70)
    
    for name, result in results.items():
        status = "✓ 可用" if result else "✗ 不可用"
        print(f"{name:15s} : {status}")
    
    print("\n提示:")
    print("1. Wind API 和 XtQuant 为可选数据源，不影响程序运行")
    print("2. akshare 和东方财富网为必需数据源，建议确保可用")
    print("3. 如果某个数据源不可用，程序会自动切换到备用源")
    print("="*70)


if __name__ == "__main__":
    test_all()

