from base_trader import BaseTrader, BaseTraderCallback
import time

def test():
    print("=== XtQuant Base Trader Test ===")
    
    # Create trader instance
    trader = BaseTrader(
        path=r'D:\国金证券QMT交易端\userdata_mini',
        account='8886063599',
        session_id=123456
    )
    
    # Connect
    print("Connecting to trading system...")
    connect_result = trader.connect()
    
    if connect_result != 0:
        print(f"Connection failed, error code: {connect_result}")
        return
    
    # Register callback
    callback = BaseTraderCallback()
    trader.register_callback(callback)
    
    # Subscribe
    subscribe_result = trader.subscribe()
    if subscribe_result != 0:
        print(f"Subscribe failed, error code: {subscribe_result}")
        return
    
    # Query asset
    asset = trader.get_asset()
    if asset:
        print(f"Available cash: {asset['cash']:.2f}")
    
    # Query positions
    positions = trader.get_positions()
    print(f"Found {len(positions)} positions")
    
    # Query orders
    orders = trader.get_orders()
    print(f"Found {len(orders)} orders")
    
    # Query trades
    trades = trader.get_trades()
    print(f"Found {len(trades)} trades")
    
    # Stop
    trader.stop()
    print("Test completed")

if __name__ == "__main__":
    test()
