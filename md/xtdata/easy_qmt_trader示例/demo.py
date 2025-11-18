from easy_qmt_trader import easy_qmt_trader
from xtquant.xttrader import XtQuantTraderCallback

# 1. 继承并实现自己的回调
class MyCallback(XtQuantTraderCallback):
    def on_stock_order(self, order):
        print('[委托]', order.order_id, order.stock_code,
              '状态=', order.order_status, '已成交=', order.traded_volume)

    def on_stock_trade(self, trade):
        print('[成交]', trade.order_id, trade.stock_code,
              '价格=', trade.traded_price, '数量=', trade.traded_volume)

# 2. 正常连接
trader = easy_qmt_trader(path=r'D:\国金证券QMT交易端\userdata_mini',
                         account='8886063599', session_id=123456)
trader.connect()

# 3. 把回调注册进去（只需一次）
callback = MyCallback()
trader.xt_trader.register_callback(callback)   # 关键一句！

# 4. 下单测试
oid = trader.buy('512710.SH', 100, 0.661)
print('已下单，ID=', oid)

# 5. 保持进程别退出，才能收到推送
import time
while True:
    time.sleep(1)