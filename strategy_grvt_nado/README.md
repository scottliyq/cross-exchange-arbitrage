# GRVT-Nado 价差套利策略

这是一个在 GRVT 和 Nado 交易所之间进行价差套利的自动化交易策略。

## 策略说明

- **Maker 交易所**: GRVT (使用 post-only 订单)
- **Taker 交易所**: Nado (使用 post-only 订单，因为 Nado 不支持纯 market 订单)
- **交易逻辑**: 
  - 当 Nado 的买价高于 GRVT 的买价达到阈值时，在 GRVT 上买入，在 Nado 上卖出
  - 当 GRVT 的卖价高于 Nado 的卖价达到阈值时，在 GRVT 上卖出，在 Nado 上买入

## 目录结构

```
strategy_grvt_nado/
├── __init__.py              # 包初始化文件
├── grvt_nado_arb.py         # 主策略逻辑
├── order_manager.py         # 订单管理器
├── order_book_manager.py    # 订单簿管理器
├── position_tracker.py      # 仓位跟踪器
├── websocket_manager.py     # WebSocket 管理器
└── data_logger.py           # 数据记录器
```

## 环境变量配置

在 `.grvt_nado_env` 文件中需要设置以下环境变量:

### GRVT 配置
```
GRVT_TRADING_ACCOUNT_ID=your_trading_account_id
GRVT_PRIVATE_KEY=your_private_key
GRVT_API_KEY=your_api_key
GRVT_ENVIRONMENT=prod  # 或 testnet, staging, dev
```

### Nado 配置
```
NADO_PRIVATE_KEY=your_private_key
NADO_MODE=MAINNET  # 或 DEVNET
NADO_SUBACCOUNT_NAME=default
```

### 交易参数
```
TICKER=BTC                      # 交易标的
ORDER_QUANTITY=0.01             # 每次交易数量
MAX_POSITION=0.1                # 最大持仓限制
LONG_GRVT_THRESHOLD=10          # 做多阈值(价差)
SHORT_GRVT_THRESHOLD=10         # 做空阈值(价差)
```

## 使用方法

1. 安装依赖:
```bash
uv sync
uv pip install nado-protocol
```

2. 配置环境变量:
```bash
# 创建 .grvt_nado_env 文件，填入你的 API 密钥
```

3. 运行策略:
```bash
python main_grvt_nado_arb.py
```

## 核心模块说明

### GrvtNadoArb (grvt_nado_arb.py)
主策略类，负责:
- 初始化交易所客户端
- 监控价差
- 执行套利交易
- 管理仓位

### OrderManager (order_manager.py)
订单管理器，负责:
- 在 GRVT 上下 post-only 订单
- 在 Nado 上下订单（使用 REST API）
- 监控订单状态

### PositionTracker (position_tracker.py)
仓位跟踪器，负责:
- 跟踪 GRVT 和 Nado 的持仓
- 计算净持仓
- 更新持仓状态

### OrderBookManager (order_book_manager.py)
订单簿管理器，负责:
- 管理 GRVT 的订单簿数据（WebSocket）
- 管理 Nado 的订单簿数据（REST API）
- 提供 BBO (最优买卖价) 查询

### WebSocketManager (websocket_manager.py)
WebSocket 管理器，负责:
- 管理 GRVT 的 WebSocket 连接
- Nado 使用 REST API 轮询（无 WebSocket）

### DataLogger (data_logger.py)
数据记录器，负责:
- 记录交易日志到 CSV
- 记录 BBO 数据到 CSV
- 用于后续分析

## 注意事项

### Nado 特殊性
1. **Nado 不支持纯 market 订单**，所有订单都需要指定价格
2. **Nado 使用 REST API 获取 BBO**，没有 WebSocket 订单簿订阅
3. **Nado 使用 subaccount 体系**，需要配置 subaccount_name
4. **Nado 订单成交确认可能有延迟**，需要轮询订单状态

### 与 GRVT-Aster 策略的区别
1. Aster 使用 market 订单快速成交，Nado 使用 post-only 订单等待成交
2. Aster 有 WebSocket 订单簿，Nado 使用 REST API 轮询
3. 成交速度：Aster > Nado，但 Nado 可能获得更好的价格
