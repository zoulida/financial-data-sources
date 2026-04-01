"""
网格交易策略 3.0

模块结构：
- config.py          : 配置常量、默认参数、状态码映射
- models.py          : 数据模型定义 (PositionEntry, Trade, GridSpec 等)
- utils.py           : 通用工具函数 (交易所判断、交易时段判断)
- grid_engine.py     : 网格引擎 (层级管理、价格映射、越界检测)
- position_book.py   : 仓位簿 (CRUD、CSV 持久化、线程安全)
- order_manager.py   : 订单管理 (本地挂单状态、订单同步、涨跌停检查)
- broker.py          : 券商接口封装 (QMT 交易器、下单、查询)
- tick_converter.py  : Tick 数据转换 (xtdata → vnpy TickData)
- reporter.py        : 交易报告 (配对逻辑、日终报告)
- grid_strategy.py   : 策略核心逻辑 (网格初始化、tick 处理、买卖决策)
- strategy_manager.py: 策略管理器 (策略创建、行情订阅、成交回调)
- mock_replayer.py   : 模拟回放器 (历史 tick 数据回放)
- run.py             : 统一启动入口
"""
