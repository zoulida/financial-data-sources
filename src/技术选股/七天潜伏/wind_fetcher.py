from typing import List, Dict
import pandas as pd

try:
    from WindPy import w
except ImportError:
    raise ImportError("缺少 WindPy 依赖")

# Wind数据侧接口，专为七天潜伏策略三因子（@说明.md“筹码因子”）获取市值、龙虎榜及5日换手。
# mkt_cap_float = 流通市值（对应“流通盘30–200亿”筛选标准）
# abnormaltrade_netbuy = 龙虎榜净买入（对应“龙虎榜有机构/游资净买入≥2000万”标准）
# turn = 5日换手（筹码沉淀）
# None常为数据缺失或无龙虎榜当日
def fetch_mv_lhb_turn(codes: List[str], trade_date: str) -> Dict[str, dict]:
    """
    输入股票列表和日期(格式'20241029'或'2024-10-29')，返回dict[code]={'float_mv':xx, 'lhb_net':xx, 'turn_5':[v1..v5]}
    保证key格式和输入codes严格一致（全部大写），未查到填None。
    """
    if not codes:
        return {}
    codes_upper = [c.upper() for c in codes]
    w.start()
    tdate = trade_date.replace('-', '') if '-' in trade_date else trade_date
    # 使用 mkt_cap_float 字段 + 必要参数 options
    wss_fields = 'mkt_cap_float,abnormaltrade_netbuy'
    wss_options = f"unit=1;tradeDate={tdate};currencyType="
    data = w.wss(codes_upper, wss_fields, wss_options)
    if data.ErrorCode != 0 or not data.Codes:
        print(f"Wind wss错误:{data.ErrorCode}, Codes:{data.Codes}")
        mv_list, lhb_list, code_list = [], [], []
    else:
        mv_list, lhb_list = data.Data[0], data.Data[1]
        code_list = [c.upper() for c in data.Codes]
    # 获取近5日换手（wsd）
    import pandas as pd
    try:
        dt_pd = pd.to_datetime(tdate)
        end = dt_pd.strftime('%Y-%m-%d')
        start = (dt_pd - pd.Timedelta(days=15)).strftime('%Y-%m-%d')
        d2 = w.wsd(codes_upper, 'turn', start, end, 'Days=Trading')
    except Exception as e:
        print(f"Wind wsd异常: {e}")
        d2 = type('d2', (object,), { 'ErrorCode':-1, 'Codes':[], 'Data':[]})()
    if getattr(d2, 'ErrorCode', 0) != 0:
        print(f"Wind wsd错误:{getattr(d2, 'ErrorCode', 0)}")
        turn_map = {}
        d2_codes = []
    else:
        d2_codes = [c.upper() for c in getattr(d2, 'Codes', [])]
        turn_map = {}
        for i, code in enumerate(d2_codes):
            arr = list(d2.Data[i][-5:]) if len(d2.Data[i])>=5 else list(d2.Data[i])
            turn_map[code] = arr
    result = {}
    for i, code in enumerate(codes_upper):
        mv = None
        lhb = None
        turn5 = []
        if code in code_list:
            idx = code_list.index(code)
            mv = mv_list[idx] if idx < len(mv_list) else None
            lhb = lhb_list[idx] if idx < len(lhb_list) else None
        if code in turn_map:
            turn5 = turn_map[code]
        result[code] = {
            'float_mv': mv,
            'lhb_net': lhb,
            'turn_5': turn5
        }
    w.stop()
    return result

# === 简易本地测试 ===
if __name__ == "__main__":
    # 测试股票代码格式
    test_codes = ["000001.SZ", "600000.SH", "000002.SZ"]
    test_date = "20241029"
    # 请确保WindPy已安装并开启Wind终端
    data = fetch_mv_lhb_turn(test_codes, test_date)
    print("测试fetch_mv_lhb_turn返回:")
    for k, v in data.items():
        print(f"{k}", v)
