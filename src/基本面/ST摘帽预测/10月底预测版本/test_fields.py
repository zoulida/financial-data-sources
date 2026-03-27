"""
测试Wind API字段获取

测试所有需要的字段，看哪些能正常获取
"""

from WindPy import w
import pandas as pd
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')


def test_fields():
    """测试字段获取"""
    w.start()
    print("Wind API已启动\n")
    
    # 测试用的股票代码（ST股票）
    test_codes = ["000504.SZ", "000536.SZ", "600086.SH"]  # 几个ST股票作为测试
    
    current_year = datetime.now().year
    q3_date = f"{current_year}0930"
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y%m%d')
    
    print("=" * 80)
    print("测试字段获取情况")
    print("=" * 80)
    
    # 1. 测试1-3季度累计数据字段
    print("\n【1】测试1-3季度累计数据字段（Q3报告期）")
    print("-" * 80)
    
    fields_quarterly = {
        "np_belongto_parcomsh": "归属母公司股东的净利润（累计）",
        "deductedprofit_ttm2": "扣除非经常性损益后归属母公司股东的净利润（TTM）",
        "oper_rev": "营业收入（累计）",
        "grossprofitmargin": "销售毛利率",
        "expensetosales": "销售期间费用率",
        "fin_exp_is": "财务费用",
        "eqy_belongto_parcomsh": "归属母公司股东的权益（净资产）",
        "div_aualcashdividend": "年度现金分红总额（公告）",
        "fa_nrgl": "非经常性损益",
    }
    
    for field, desc in fields_quarterly.items():
        try:
            data = w.wss(
                test_codes,
                field,
                f"rptDate={q3_date};unit=1;currencyType="
            )
            if data.ErrorCode == 0:
                print(f"[OK] {desc} ({field}): 成功")
                if len(data.Data) > 0 and len(data.Data[0]) > 0:
                    sample_value = data.Data[0][0]
                    if sample_value is not None:
                        print(f"  示例值: {sample_value}")
                    else:
                        print(f"  示例值: None (数据为空)")
            else:
                print(f"[FAIL] {desc} ({field}): 失败 - ErrorCode={data.ErrorCode}")
        except Exception as e:
            print(f"[ERROR] {desc} ({field}): 异常 - {str(e)}")
    
    # 2. 测试Q3单季相关字段
    print("\n【2】测试Q3单季数据字段")
    print("-" * 80)
    
    # Q3单季营收需要计算（Q3累计 - Q2累计），这里测试获取Q2和Q3累计营收
    print("测试：Q3累计营收 (oper_rev)")
    try:
        data_q3 = w.wss(test_codes, "oper_rev", f"rptDate={q3_date};unit=1;currencyType=")
        if data_q3.ErrorCode == 0:
            print("[OK] Q3累计营收: 成功")
        else:
            print(f"[FAIL] Q3累计营收: 失败 - ErrorCode={data_q3.ErrorCode}")
    except Exception as e:
        print(f"[ERROR] Q3累计营收: 异常 - {str(e)}")
    
    q2_date = f"{current_year}0630"
    print("测试：Q2累计营收 (oper_rev)")
    try:
        data_q2 = w.wss(test_codes, "oper_rev", f"rptDate={q2_date};unit=1;currencyType=")
        if data_q2.ErrorCode == 0:
            print("[OK] Q2累计营收: 成功")
        else:
            print(f"[FAIL] Q2累计营收: 失败 - ErrorCode={data_q2.ErrorCode}")
    except Exception as e:
        print(f"[ERROR] Q2累计营收: 异常 - {str(e)}")
    
    # 3. 测试总市值
    print("\n【3】测试总市值字段")
    print("-" * 80)
    
    market_cap_fields = {
        "mkt_cap_ard": "总市值",
        "val_mv_ARD": "总市值（备用字段）",
    }
    
    for field, desc in market_cap_fields.items():
        try:
            data = w.wss(
                test_codes,
                field,
                f"unit=1;tradeDate={yesterday}"
            )
            if data.ErrorCode == 0:
                print(f"[OK] {desc} ({field}): 成功")
                if len(data.Data) > 0 and len(data.Data[0]) > 0:
                    sample_value = data.Data[0][0]
                    if sample_value is not None:
                        print(f"  示例值: {sample_value}")
                    else:
                        print(f"  示例值: None")
            else:
                print(f"[FAIL] {desc} ({field}): 失败 - ErrorCode={data.ErrorCode}")
        except Exception as e:
            print(f"[ERROR] {desc} ({field}): 异常 - {str(e)}")
    
    # 4. 测试其他数据字段
    print("\n【4】测试其他数据字段")
    print("-" * 80)
    
    other_fields = {
        "stmnote_audit_category": "审计意见类型（字符串）",
        "net_cash_flows_oper_act": "经营活动产生的现金流量净额",
    }
    
    for field, desc in other_fields.items():
        try:
            data = w.wss(
                test_codes,
                field,
                f"rptDate={q3_date};unit=1;currencyType="
            )
            if data.ErrorCode == 0:
                print(f"[OK] {desc} ({field}): 成功")
                if len(data.Data) > 0 and len(data.Data[0]) > 0:
                    sample_value = data.Data[0][0]
                    if sample_value is not None:
                        print(f"  示例值: {sample_value}")
                    else:
                        print(f"  示例值: None")
            else:
                print(f"[FAIL] {desc} ({field}): 失败 - ErrorCode={data.ErrorCode}")
                # 尝试查找替代字段
                print(f"  尝试查找替代字段...")
        except Exception as e:
            print(f"[ERROR] {desc} ({field}): 异常 - {str(e)}")
    
    # 测试审计意见的其他字段（备用）
    print("\n测试审计意见其他字段（备用）...")
    audit_alternatives = [
        "auditor",  # 审计机构
    ]
    for field in audit_alternatives:
        try:
            data = w.wss(test_codes, field, f"rptDate={q3_date}")
            if data.ErrorCode == 0:
                print(f"  备用字段 {field}: 可用（审计机构名称）")
            else:
                print(f"  备用字段 {field}: 失败 - ErrorCode={data.ErrorCode}")
        except:
            pass
    
    # 5. 测试扣非净利润的累计值（不是TTM）
    print("\n【5】测试扣非净利润累计值字段（查找替代）")
    print("-" * 80)
    
    # 查找可能的扣非净利润累计值字段
    deducted_fields = [
        "deductedprofit_ttm2",  # 已测试
        # 可能需要查找其他字段
    ]
    
    # 尝试从利润表中获取扣非净利润累计值
    # 可能需要使用w.wsd获取季度数据
    print("尝试：使用w.wsd获取扣非净利润季度数据...")
    try:
        # 获取Q3累计扣非净利润，可能需要从利润表中计算
        # 这里先测试能否获取到数据
        data = w.wsd(
            ",".join(test_codes),
            "deductedprofit_ttm2",  # 暂时还是用TTM
            f"{current_year}0101",
            q3_date,
            "Period=Q;rptType=1"
        )
        if data.ErrorCode == 0:
            print("[OK] w.wsd获取季度数据: 成功")
        else:
            print(f"[FAIL] w.wsd获取季度数据: 失败 - ErrorCode={data.ErrorCode}")
    except Exception as e:
        print(f"[ERROR] w.wsd获取季度数据: 异常 - {str(e)}")
    
    # 6. 测试违规处罚次数字段
    print("\n【6】测试违规处罚次数字段")
    print("-" * 80)
    
    # 测试违规处罚次数字段
    start_date = f"{current_year}0101"
    end_date = datetime.now().strftime('%Y%m%d')
    
    print(f"测试字段: cac_illegalitynum")
    print(f"日期范围: {start_date} 至 {end_date}")
    try:
        data = w.wss(
            test_codes,
            "cac_illegalitynum",
            f"startDate={start_date};endDate={end_date}"
        )
        if data.ErrorCode == 0:
            print(f"[OK] cac_illegalitynum: 成功")
            if len(data.Data) > 0 and len(data.Data[0]) > 0:
                for idx, code in enumerate(data.Codes):
                    if idx < len(data.Data[0]):
                        sample_value = data.Data[0][idx]
                        print(f"  {code}: {sample_value} (类型: {type(sample_value).__name__})")
        else:
            print(f"[FAIL] cac_illegalitynum: 失败 - ErrorCode={data.ErrorCode}")
    except Exception as e:
        print(f"[ERROR] cac_illegalitynum: 异常 - {str(e)}")
    
    # 测试其他相关字段（备用）
    print("\n测试其他相关字段（备用）...")
    violation_fields = [
        "riskwarning",  # 是否属于风险警示板
        "riskadmonition_date",  # 戴帽摘帽时间
    ]
    
    for field in violation_fields:
        try:
            data = w.wss(test_codes, field, "")
            if data.ErrorCode == 0:
                print(f"  备用字段 {field}: 可用")
            else:
                print(f"  备用字段 {field}: 失败 - ErrorCode={data.ErrorCode}")
        except Exception as e:
            print(f"  备用字段 {field}: 异常 - {str(e)}")
    
    # 7. 测试预告披露日
    print("\n【7】测试预告披露日字段")
    print("-" * 80)
    print("注意：预告披露日可能不在w.wss中，可能需要使用w.wset或其他接口")
    
    forecast_fields = [
        "forecast_date",  # 可能的字段名
        "earnings_forecast_date",  # 可能的字段名
    ]
    
    for field in forecast_fields:
        try:
            data = w.wss(test_codes, field, "")
            if data.ErrorCode == 0:
                print(f"[OK] {field}: 成功")
            else:
                print(f"[FAIL] {field}: 失败 - ErrorCode={data.ErrorCode}")
        except Exception as e:
            print(f"[ERROR] {field}: 异常 - {str(e)}")
    
    # 尝试使用w.wset获取业绩预告数据
    print("\n尝试使用w.wset获取业绩预告...")
    try:
        today = datetime.now().strftime('%Y-%m-%d')
        # 尝试获取业绩预告数据
        data = w.wset("performanceforecast", f"date={today}")
        if data.ErrorCode == 0:
            print("[OK] w.wset('performanceforecast'): 成功")
            print(f"  获取到 {len(data.Data[0]) if len(data.Data) > 0 else 0} 条预告数据")
        else:
            print(f"[FAIL] w.wset('performanceforecast'): 失败 - ErrorCode={data.ErrorCode}")
    except Exception as e:
        print(f"[ERROR] w.wset('performanceforecast'): 异常 - {str(e)}")
    
    print("\n" + "=" * 80)
    print("测试完成")
    print("=" * 80)
    print("\n【总结】")
    print("-" * 80)
    print("如果某些字段获取失败，请参考 md/winds/merged_fields_fixed.txt")
    print("查找替代字段名称。")
    print("=" * 80)
    
    w.stop()


if __name__ == "__main__":
    from datetime import timedelta
    test_fields()

