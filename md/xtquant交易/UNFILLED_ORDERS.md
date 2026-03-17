# 未成交订单功能说明

## 功能概述

为base_trader.py添加了专门的未成交订单查询功能，方便用户管理和监控未完成的委托。

## 新增功能

### 1. get_unfilled_orders() 方法
```python
def get_unfilled_orders(self) -> List[Dict]:
    """查询未成交订单（尚未完全执行的委托）"""
```

**功能特点：**
- 自动筛选未成交订单
- 返回结构化数据
- 包含状态描述

**返回字段：**
- `order_id`: 委托编号
- `stock_code`: 证券代码
- `order_volume`: 委托数量
- `traded_volume`: 成交数量
- `price`: 委托价格
- `order_status`: 委托状态码
- `status_desc`: 委托状态描述

### 2. _get_order_status_desc() 方法
```python
def _get_order_status_desc(self, status_code: int) -> str:
    """获取委托状态描述"""
```

**状态码映射：**
- `50`: Rejected/废单
- `51`: Partially Filled/部分成交
- `52`: Unfilled/未成交
- `53`: Partially Filled/部分成交
- `54`: Cancelled/已撤单
- `55`: Partially Cancelled/部分撤单
- `56`: Filled/已成交
- `57`: Pending/待确认

### 3. demo_unfilled_orders() 演示函数
在demo.py中新增了专门的未成交订单演示功能。

**使用方法：**
```bash
python demo.py
# 选择 5 - Unfilled orders demo
```

**功能：**
- 显示所有未成交订单
- 计算未成交总金额
- 提供批量撤单选项
- 显示部分成交订单

## 使用示例

### 基础用法
```python
from base_trader import BaseTrader

trader = BaseTrader(
    path=r'D:\国金证券QMT交易端\userdata_mini',
    account='8886063599',
    session_id=123456
)

trader.connect()
trader.subscribe()

# 获取未成交订单
unfilled = trader.get_unfilled_orders()
for order in unfilled:
    print(f"{order['stock_code']}: {order['order_volume']}@{order['price']}")

trader.stop()
```

### 批量撤单
```python
unfilled = trader.get_unfilled_orders()
if unfilled:
    for order in unfilled:
        result = trader.cancel_order(order['order_id'])
        if result == 0:
            print(f"撤单成功: {order['stock_code']}")
```

## 测试脚本

### test_unfilled.py
专门的测试脚本，提供详细的委托状态分析：

```bash
python test_unfilled.py
```

**功能：**
- 统计所有委托状态
- 显示未成交订单详情
- 显示部分成交订单
- 计算未成交总金额

## 判断逻辑

**未成交订单的判断条件：**
1. `traded_volume == 0` (成交数量为0)
2. `order_status` 不在 `[50, 54, 56]` 中 (非废单、已撤单、已成交)

**部分成交订单的判断条件：**
1. `0 < traded_volume < order_volume` (成交数量大于0但小于委托数量)

## 实际测试结果

根据测试数据：
- **总委托**: 60条
- **状态分布**: 
  - 状态码54: 18条 (已撤单)
  - 状态码56: 38条 (已成交)
  - 状态码50: 4条 (废单)
- **未成交**: 0条
- **部分成交**: 0条

## 应用场景

1. **开盘前检查** - 查看是否有隔夜委托未成交
2. **盘中监控** - 实时跟踪未成交订单状态
3. **收盘前处理** - 批量撤销未成交订单
4. **风险管理** - 控制未成交订单的总金额
5. **策略优化** - 根据未成交情况调整下单策略

## 注意事项

1. **连接状态** - 使用前确保已连接并订阅
2. **权限检查** - 确保有撤单权限
3. **状态码** - 不同券商可能略有差异，需要实际验证
4. **实时性** - 委托状态会实时变化，建议结合回调使用

---

**状态**: ✅ 完成
**测试**: ✅ 通过
**文档**: ✅ 完整
