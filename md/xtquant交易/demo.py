"""
Base Trader Usage Example
=========================

Demo based on XtQuant API documentation
"""

from base_trader_zld import BaseTrader, BaseTraderCallback
import time


def main():
    """Main function - Complete trading demo"""
    
    print("=== XtQuant Base Trader Demo ===")
    
    # 1. Create trader instance
    trader = BaseTrader(
        path=r'D:\国金证券QMT交易端\userdata_mini',
        account='8886063599',
        session_id=123456
    )
    
    # 2. Connect to trading system
    print("\n1. Connecting to trading system...")
    connect_result = trader.connect()
    
    if connect_result != 0:
        print(f"Connection failed, error code: {connect_result}")
        return
    
    # 3. Create and register callback
    print("\n2. Register trading callback...")
    callback = BaseTraderCallback()
    trader.register_callback(callback)
    
    # 4. Subscribe account information
    print("\n3. Subscribe account information...")
    subscribe_result = trader.subscribe()
    
    if subscribe_result != 0:
        print(f"Subscribe failed, error code: {subscribe_result}")
        return
    
    # 5. Query account assets
    print("\n4. Query account assets...")
    asset = trader.get_asset()
    if asset:
        print(f"Available cash: {asset['cash']:.2f}")
        print(f"Total asset: {asset['total_asset']:.2f}")
    
    # 6. Query positions
    print("\n5. Query current positions...")
    positions = trader.get_positions()
    if positions:
        print("Current positions:")
        for pos in positions:
            print(f"  {pos['stock_code']}: Volume={pos['volume']} Available={pos['can_use_volume']} MarketValue={pos['market_value']:.2f}")
    else:
        print("No current positions")
    
    # 7. Query today's orders
    print("\n6. Query today's orders...")
    orders = trader.get_orders()
    if orders:
        print("Today's orders:")
        for order in orders[-5:]:  # Show last 5 orders
            print(f"  {order['stock_code']}: {order['order_volume']} shares@{order['price']:.3f} Status={order['order_status']}")
    else:
        print("No order records today")
    
    # 8. Query today's trades
    print("\n7. Query today's trades...")
    trades = trader.get_trades()
    if trades:
        print("Today's trades:")
        for trade in trades[-5:]:  # Show last 5 trades
            print(f"  {trade['stock_code']}: {trade['traded_volume']} shares@{trade['traded_price']:.3f}")
    else:
        print("No trade records today")
    
    # 9. Trading example (use with caution, confirm parameters are correct)
    print("\n8. Trading example...")
    print("Note: Trading code below is commented to avoid accidental operation")
    
    # Buy example
    stock_code = "512710.SH"  # Defense ETF
    buy_volume = 100
    buy_price = 0.661
    
    print(f"Buy example: {stock_code} {buy_volume} shares Price:{buy_price}")
    # order_id = trader.buy(stock_code, buy_volume, buy_price)
    # if order_id > 0:
    #     print(f"Buy order successful, Order ID: {order_id}")
    #     
    #     # Wait and cancel order
    #     time.sleep(2)
    #     cancel_result = trader.cancel_order(order_id)
    #     if cancel_result == 0:
    #         print(f"Cancel successful, Order ID: {order_id}")
    # else:
    #     print("Buy order failed")
    
    # 10. Monitor mode
    print("\n9. Monitor mode...")
    print("Keep running, receiving trading push...")
    print("Press Ctrl+C to exit")
    
    try:
        # Add strategy logic here
        for i in range(10):  # Demo 10 seconds then exit
            time.sleep(1)
            print(f"Monitoring... {i+1}/10")
            
            # Example: Check specific stock position
            if i == 5:
                position = trader.get_position(stock_code)
                if position:
                    print(f"  {stock_code} Position: {position['volume']} shares")
                else:
                    print(f"  {stock_code} No position")
                    
    except KeyboardInterrupt:
        print("\nUser interrupted program")
    
    # 11. Stop trading
    print("\n10. Stop trading...")
    trader.stop()
    print("Program ended")


def demo_simple_trading():
    """Simple trading demo"""
    print("=== Simple Trading Demo ===")
    
    trader = BaseTrader(
        path=r'D:\国金证券QMT交易端\userdata_mini',
        account='8886063599',
        session_id=123456
    )
    
    # Connect
    if trader.connect() != 0:
        print("Connection failed")
        return
    
    # Register callback
    callback = BaseTraderCallback()
    trader.register_callback(callback)
    
    # Subscribe
    trader.subscribe()
    
    # Query cash
    asset = trader.get_asset()
    if asset:
        print(f"Available cash: {asset['cash']:.2f}")
    
    # Simulate trading (commented to avoid accidental operation)
    stock_code = "512710.SH"
    
    # Buy
    print(f"Simulated buy: {stock_code}")
    # order_id = trader.buy(stock_code, 100, 0.661)
    
    # Query order status
    orders = trader.get_orders()
    if orders:
        print(f"Latest order: {orders[-1]['stock_code']} Status={orders[-1]['order_status']}")
    
    trader.stop()


def demo_position_management():
    """Position management demo"""
    print("=== Position Management Demo ===")
    
    trader = BaseTrader(
        path=r'D:\国金证券QMT交易端\userdata_mini',
        account='8886063599',
        session_id=123456
    )
    
    if trader.connect() != 0:
        print("Connection failed")
        return
    
    # Get positions
    positions = trader.get_positions()
    
    if positions:
        print("Current position details:")
        for pos in positions:
            stock_code = pos['stock_code']
            volume = pos['volume']
            can_use = pos['can_use_volume']
            market_value = pos['market_value']
            
            print(f"\nStock: {stock_code}")
            print(f"  Total position: {volume} shares")
            print(f"  Available: {can_use} shares")
            print(f"  Market value: {market_value:.2f}")
            
            # Can decide whether to operate based on strategy
            # if market_value > 10000:  # Market value over 10000
            #     current_price = market_value / volume
            #     print(f"  Strategy: Market value over 10000, consider selling")
            #     # trader.sell(stock_code, can_use, current_price)
    else:
        print("No current positions")
    
    trader.stop()


def demo_order_management():
    """Order management demo"""
    print("=== Order Management Demo ===")
    
    trader = BaseTrader(
        path=r'D:\国金证券QMT交易端\userdata_mini',
        account='8886063599',
        session_id=123456
    )
    
    if trader.connect() != 0:
        print("Connection failed")
        return
    
    # Query today's orders
    orders = trader.get_orders()
    
    if orders:
        print("Today's order list:")
        for i, order in enumerate(orders, 1):
            status_map = {
                0: "Fully filled",
                1: "Partially filled", 
                2: "Unfilled",
                3: "Cancelled",
                4: "Rejected",
                5: "Partially cancelled"
            }
            
            status = status_map.get(order['order_status'], f"Unknown({order['order_status']})")
            
            print(f"{i}. {order['stock_code']} "
                  f"{order['order_volume']} shares@{order['price']:.3f} "
                  f"Filled:{order['traded_volume']} Status:{status}")
            
            # Can decide whether to cancel based on status
            # if order['order_status'] == 2:  # Unfilled
            #     print(f"  Strategy: Unfilled order, consider cancelling")
            #     # trader.cancel_order(order['order_id'])
    else:
        print("No order records today")
    
    # Query today's trades
    trades = trader.get_trades()
    
    if trades:
        print("\nToday's trade list:")
        for i, trade in enumerate(trades, 1):
            print(f"{i}. {trade['stock_code']} {trade['traded_volume']} shares@{trade['traded_price']:.3f}")
    
    trader.stop()


def demo_unfilled_orders():
    """Unfilled orders demo"""
    print("=== Unfilled Orders Demo ===")
    
    trader = BaseTrader(
        path=r'D:\国金证券QMT交易端\userdata_mini',
        account='8886063599',
        session_id=123456
    )
    
    if trader.connect() != 0:
        print("Connection failed")
        return
    
    # Register callback
    callback = BaseTraderCallback()
    trader.register_callback(callback)
    
    # Subscribe
    trader.subscribe()
    
    # Get unfilled orders
    unfilled_orders = trader.get_unfilled_orders()
    
    if unfilled_orders:
        print("Unfilled orders:")
        for i, order in enumerate(unfilled_orders, 1):
            print(f"{i}. {order['stock_code']} {order['order_volume']} shares@{order['price']:.3f} Status: {order['status_desc']}")
            
        # Show total unfilled value
        total_value = sum(order['order_volume'] * order['price'] for order in unfilled_orders)
        print(f"\nTotal unfilled value: {total_value:.2f}")
        
        # Option to cancel all unfilled orders
        print("\nOptions:")
        print("1. Keep unfilled orders")
        print("2. Cancel all unfilled orders")
        
        try:
            choice = input("Enter choice (1-2): ").strip()
            if choice == "2":
                print("\nCancelling all unfilled orders...")
                for order in unfilled_orders:
                    result = trader.cancel_order(order['order_id'])
                    if result == 0:
                        print(f"  Cancelled: {order['stock_code']} OrderID:{order['order_id']}")
                    else:
                        print(f"  Cancel failed: {order['stock_code']} OrderID:{order['order_id']}")
        except KeyboardInterrupt:
            print("\nCancel operation interrupted")
    else:
        print("No unfilled orders found")
    
    trader.stop()


if __name__ == "__main__":
    print("Select demo mode:")
    print("1. Complete function demo")
    print("2. Simple trading demo")
    print("3. Position management demo")
    print("4. Order management demo")
    print("5. Unfilled orders demo")
    
    try:
        choice = input("Enter choice (1-5): ").strip()
        
        if choice == "1":
            main()
        elif choice == "2":
            demo_simple_trading()
        elif choice == "3":
            demo_position_management()
        elif choice == "4":
            demo_order_management()
        elif choice == "5":
            demo_unfilled_orders()
        else:
            print("Invalid choice, running complete function demo")
            main()
    except KeyboardInterrupt:
        print("\nProgram interrupted by user")
    except Exception as e:
        print(f"Program error: {e}")
        print("Running complete function demo")
        main()
