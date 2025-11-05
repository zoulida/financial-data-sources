"""
测试oper_rev字段获取
"""

from WindPy import w
from datetime import datetime
import pandas as pd
import warnings
warnings.filterwarnings('ignore')


def test_oper_rev():
    """测试营业收入字段获取"""
    w.start()
    print("Wind API已启动\n")
    
    # 测试用的ST股票
    test_codes = ["000004.SZ", "000504.SZ", "000536.SZ"]
    
    # 测试2024年Q3数据
    q3_date = "20240930"
    yesterday = (datetime.now() - pd.Timedelta(days=1)).strftime('%Y%m%d')
    
    print("=" * 80)
    print("测试oper_rev字段获取")
    print("=" * 80)
    
    # 测试1：使用rptDate
    print("\n测试1：使用rptDate参数")
    print(f"  codes: {test_codes}")
    print(f"  field: oper_rev")
    print(f"  options: rptDate={q3_date};unit=1;currencyType=")
    data1 = w.wss(test_codes, "oper_rev", f"rptDate={q3_date};unit=1;currencyType=")
    print(f"  ErrorCode: {data1.ErrorCode}")
    if data1.ErrorCode == 0:
        print(f"  返回数据: {data1.Data[0] if len(data1.Data) > 0 else []}")
    
    # 测试2：移除unit参数
    print("\n测试2：移除unit参数")
    print(f"  options: rptDate={q3_date}")
    data2 = w.wss(test_codes, "oper_rev", f"rptDate={q3_date}")
    print(f"  ErrorCode: {data2.ErrorCode}")
    if data2.ErrorCode == 0:
        print(f"  返回数据: {data2.Data[0] if len(data2.Data) > 0 else []}")
    
    # 测试3：使用tradeDate
    print("\n测试3：使用tradeDate参数")
    print(f"  options: tradeDate={yesterday};rptDate={q3_date}")
    data3 = w.wss(test_codes, "oper_rev", f"tradeDate={yesterday};rptDate={q3_date}")
    print(f"  ErrorCode: {data3.ErrorCode}")
    if data3.ErrorCode == 0:
        print(f"  返回数据: {data3.Data[0] if len(data3.Data) > 0 else []}")
    
    # 测试4：只使用tradeDate，不使用rptDate
    print("\n测试4：只使用tradeDate")
    print(f"  options: tradeDate={yesterday}")
    data4 = w.wss(test_codes, "oper_rev", f"tradeDate={yesterday}")
    print(f"  ErrorCode: {data4.ErrorCode}")
    if data4.ErrorCode == 0:
        print(f"  返回数据: {data4.Data[0] if len(data4.Data) > 0 else []}")
    
    # 测试5：使用w.wsd获取时间序列数据
    print("\n测试5：使用w.wsd获取时间序列数据")
    print(f"  beginTime: 20240901")
    print(f"  endTime: {q3_date}")
    data5 = w.wsd(
        ",".join(test_codes),
        "oper_rev",
        "20240901",
        q3_date,
        "Period=Q;rptType=1"
    )
    print(f"  ErrorCode: {data5.ErrorCode}")
    if data5.ErrorCode == 0:
        print(f"  数据结构分析:")
        print(f"    Data长度: {len(data5.Data)}")
        if len(data5.Data) > 0:
            print(f"    Data[0]类型: {type(data5.Data[0])}")
            print(f"    Data[0]长度: {len(data5.Data[0]) if hasattr(data5.Data[0], '__len__') else 'N/A'}")
            if len(data5.Data[0]) > 0:
                print(f"    Data[0][0]类型: {type(data5.Data[0][0])}")
                print(f"    Data[0][0]值: {data5.Data[0][0]}")
        print(f"  时间: {data5.Times if hasattr(data5, 'Times') else 'N/A'}")
        if hasattr(data5, 'Times') and len(data5.Times) > 0:
            print(f"  Times[0]: {data5.Times[0]}")
    
    # 测试6：使用w.wsd获取单个日期
    print("\n测试6：使用w.wsd获取单个日期")
    print(f"  beginTime: {q3_date}")
    print(f"  endTime: {q3_date}")
    data6 = w.wsd(
        ",".join(test_codes),
        "oper_rev",
        q3_date,
        q3_date,
        "Period=Q;rptType=1;unit=1"
    )
    print(f"  ErrorCode: {data6.ErrorCode}")
    if data6.ErrorCode == 0:
        print(f"  数据结构分析:")
        print(f"    Data长度: {len(data6.Data)}")
        if len(data6.Data) > 0:
            print(f"    Data[0]类型: {type(data6.Data[0])}")
            print(f"    Data[0]长度: {len(data6.Data[0]) if hasattr(data6.Data[0], '__len__') else 'N/A'}")
            if len(data6.Data[0]) > 0:
                print(f"    Data[0][0]类型: {type(data6.Data[0][0])}")
                if isinstance(data6.Data[0][0], (list, tuple)):
                    print(f"    Data[0][0]是列表，长度: {len(data6.Data[0][0])}")
                    print(f"    Data[0][0]值: {data6.Data[0][0]}")
                else:
                    print(f"    Data[0][0]值: {data6.Data[0][0]}")
        print(f"  时间: {data6.Times if hasattr(data6, 'Times') else 'N/A'}")
        if hasattr(data6, 'Times') and len(data6.Times) > 0:
            print(f"  Times[0]: {data6.Times[0]}")
            print(f"  Times长度: {len(data6.Times)}")
    
    print("\n" + "=" * 80)
    w.stop()


if __name__ == "__main__":
    test_oper_rev()

