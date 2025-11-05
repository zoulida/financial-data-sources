"""
测试审计意见字段 stmnote_audit_category

验证返回的数据格式和内容
"""

from WindPy import w
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')


def test_audit_field():
    """测试审计意见字段"""
    w.start()
    print("Wind API已启动\n")
    
    # 测试用的股票代码（ST股票和普通股票）
    test_codes = ["000504.SZ", "000536.SZ", "600086.SH", "000001.SZ", "600000.SH"]
    
    current_year = datetime.now().year
    last_year = current_year - 1
    
    # 测试当前年份和去年年份的Q3数据
    test_dates = [
        (current_year, f"{current_year}0930", "当年Q3"),
        (last_year, f"{last_year}0930", "去年Q3"),
    ]
    
    for year, q3_date, desc in test_dates:
        print("=" * 80)
        print(f"测试审计意见字段: stmnote_audit_category")
        print(f"报告期: {q3_date} ({desc})")
        print(f"测试股票: {test_codes}")
        print()
        
        # 获取审计意见
        data = w.wss(
            test_codes,
            "stmnote_audit_category",
            f"rptDate={q3_date}"
        )
    
        if data.ErrorCode == 0:
            print(f"[OK] 字段获取成功")
            print(f"返回的股票数量: {len(data.Codes)}")
            print()
            
            print("详细数据：")
            print("-" * 80)
            has_valid_data = False
            for idx, code in enumerate(data.Codes):
                if idx < len(data.Data[0]):
                    audit_opinion = data.Data[0][idx]
                    print(f"{code}: {audit_opinion} (类型: {type(audit_opinion).__name__})")
                    
                    # 检查是否包含"无保留意见"
                    if audit_opinion is not None:
                        has_valid_data = True
                        audit_str = str(audit_opinion)
                        contains_无保留意见 = '无保留意见' in audit_str
                        print(f"  包含'无保留意见': {contains_无保留意见}")
                        if contains_无保留意见:
                            print(f"  -> 硬门槛5得分: 1分")
                        else:
                            print(f"  -> 硬门槛5得分: 0分")
                    else:
                        print(f"  数据为None -> 硬门槛5得分: 0分")
                    print()
            
            if has_valid_data:
                print("找到有效数据，停止测试")
                break
        else:
            print(f"[FAIL] 字段获取失败 - ErrorCode={data.ErrorCode}")
        
        print()
    
    print("=" * 80)
    w.stop()


if __name__ == "__main__":
    test_audit_field()

