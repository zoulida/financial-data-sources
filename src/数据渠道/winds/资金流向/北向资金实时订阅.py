"""
北向资金实时订阅脚本
功能：订阅HK999999.SH的北向净买入和剩余额度，每10秒打印一次
依赖：仅需WindPy
注意：Wind终端必须已开通"陆股通Level-2"权限，否则字段返回空
"""

from WindPy import w
import time
import threading

class NorthboundMonitor:
    """北向资金监控类"""
    
    def __init__(self):
        self.data_count = 0
        self.total_net_inflow = 0
        self.is_running = False
        self.callback_data = []
        
    def callback(self, data):
        """实时数据回调函数"""
        try:
            if data.ErrorCode == 0:
                # 解析数据
                codes = data.Codes
                fields = data.Fields
                times = data.Times
                values = data.Data
                
                # 获取北向净买入和剩余额度
                net_inflow = values[0][0] if len(values) > 0 and len(values[0]) > 0 else None
                quota_balance = values[1][0] if len(values) > 1 and len(values[1]) > 0 else None
                
                if net_inflow is not None:
                    self.callback_data.append({
                        'time': times[0] if times else 'N/A',
                        'net_inflow': net_inflow,
                        'quota_balance': quota_balance
                    })
                    
                    print(f"[{self.data_count + 1}] 时间: {times[0] if times else 'N/A'}")
                    print(f"    北向净买入: {net_inflow:.2f} 亿元")
                    print(f"    剩余额度: {quota_balance:.2f} 亿元" if quota_balance else "    剩余额度: N/A")
                    print("-" * 50)
                    
                    self.total_net_inflow += net_inflow
                    self.data_count += 1
                else:
                    print(f"[{self.data_count + 1}] 数据为空，可能未开通'陆股通Level-2'权限")
                    
            elif data.ErrorCode == -40520007:
                print("连接错误，正在重连...")
                w.stop()
                time.sleep(2)
                w.start()
                print("重连完成")
                
            else:
                print(f"数据获取错误，错误码: {data.ErrorCode}")
                
        except Exception as e:
            print(f"回调函数执行出错: {str(e)}")
    
    def start_monitoring(self):
        """开始监控"""
        print("正在初始化WindPy...")
        w.start()
        
        if not w.isconnected():
            print("WindPy连接失败，请检查：")
            print("1. Wind终端是否已启动")
            print("2. 是否已登录Wind账号")
            print("3. 网络连接是否正常")
            return
        
        print("WindPy连接成功")
        print("开始订阅北向资金数据...")
        
        # 订阅北向资金数据
        code = "HK999999.SH"
        fields = "north_net_in,north_quota_balance"
        
        # 设置回调函数
        w.wsq(code, fields, func=self.callback)
        
        self.is_running = True
        
        # 监控1分钟（6次，每10秒一次）
        print("开始监控，将持续1分钟...")
        for i in range(6):
            if not self.is_running:
                break
            time.sleep(10)
        
        # 停止监控
        self.is_running = False
        w.cancelRequest(0)  # 取消订阅
        
        # 计算统计结果
        if self.data_count > 0:
            avg_net_inflow = self.total_net_inflow / self.data_count
            print(f"\n=== 监控结果统计 ===")
            print(f"总监控次数: {self.data_count}")
            print(f"北向分钟均值 = {avg_net_inflow:.2f} 亿元")
            
            # 显示所有数据
            print(f"\n=== 详细数据 ===")
            for i, data in enumerate(self.callback_data):
                print(f"[{i+1}] {data['time']} - 净买入: {data['net_inflow']:.2f}亿, 额度: {data['quota_balance']:.2f}亿" if data['quota_balance'] else f"[{i+1}] {data['time']} - 净买入: {data['net_inflow']:.2f}亿, 额度: N/A")
        else:
            print("未获取到有效数据")
            print("请检查：")
            print("1. 是否开通了'陆股通Level-2'权限")
            print("2. Wind终端是否正常运行")
            print("3. 网络连接是否正常")
        
        # 关闭WindPy连接
        w.stop()
        print("\nWindPy连接已关闭")

def main():
    """主函数"""
    print("=== 北向资金实时监控 ===")
    print("注意：Wind终端必须已开通'陆股通Level-2'权限，否则字段返回空")
    print("=" * 50)
    
    monitor = NorthboundMonitor()
    monitor.start_monitoring()

if __name__ == "__main__":
    main()
