# GRVT-Aster 价差套利策略

这是一个在 GRVT 和 Aster 交易所之间进行价差套利的自动化交易策略。

## 策略说明

- **Maker 交易所**: GRVT (使用 post-only 订单)
- **Taker 交易所**: Aster (使用 market 订单)
- **交易逻辑**: 
  - 当 Aster 的买价高于 GRVT 的买价达到阈值时，在 GRVT 上买入，在 Aster 上卖出
  - 当 GRVT 的卖价高于 Aster 的卖价达到阈值时，在 GRVT 上卖出，在 Aster 上买入

## 目录结构

```
strategy_grvt/
├── __init__.py              # 包初始化文件
├── grvt_arb.py              # 主策略逻辑
├── order_manager.py         # 订单管理器
├── order_book_manager.py    # 订单簿管理器
├── position_tracker.py      # 仓位跟踪器
└── data_logger.py           # 数据记录器
```

## 环境变量配置

在 `.grvt_aster_env` 文件中需要设置以下环境变量:

### GRVT 配置
```
GRVT_TRADING_ACCOUNT_ID=your_trading_account_id
GRVT_PRIVATE_KEY=your_private_key
GRVT_API_KEY=your_api_key
GRVT_ENVIRONMENT=prod  # 或 testnet, staging, dev
```

### Aster 配置
```
ASTER_API_KEY=your_api_key
ASTER_SECRET_KEY=your_secret_key
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
```

2. 配置环境变量:
```bash
# 编辑 .grvt_aster_env 文件，填入你的 API 密钥
# 该文件已包含所需的配置格式
```

3. 运行策略:
```bash
python main_grvt_arb.py
```

## 核心模块说明

### GrvtArb (grvt_arb.py)
主策略类，负责:
- 初始化交易所客户端
- 监控价差
- 执行套利交易
- 管理仓位

### OrderManager (order_manager.py)
订单管理器，负责:
- 在 GRVT 上下 post-only 订单
- 在 Aster 上下 market 订单
- 监控订单状态

### PositionTracker (position_tracker.py)
仓位跟踪器，负责:
- 跟踪 GRVT 和 Aster 的持仓
- 计算净持仓
- 更新持仓状态

### OrderBookManager (order_book_manager.py)
订单簿管理器，负责:
- 管理 GRVT 和 Aster 的订单簿数据
- 提供 BBO (最优买卖价) 查询

### DataLogger (data_logger.py)
数据记录器，负责:
- 记录交易日志到 CSV
- 记录 BBO 数据到 CSV
- 用于后续分析

## 日志文件

策略运行时会在 `logs/` 目录下生成以下文件:
- `grvt_{TICKER}_log.txt` - 主日志文件
- `grvt_{TICKER}_trades.csv` - 交易记录
- `grvt_{TICKER}_bbo_data.csv` - BBO 数据记录

## 注意事项

1. **风险管理**: 
   - 设置合理的 `MAX_POSITION` 以限制风险敞口
   - 监控净持仓，防止持仓偏离

2. **阈值设置**:
   - `LONG_GRVT_THRESHOLD` 和 `SHORT_GRVT_THRESHOLD` 应该考虑交易费用和滑点
   - 阈值太小可能导致频繁交易，增加成本
   - 阈值太大可能错过套利机会

3. **网络连接**:
   - 确保稳定的网络连接
   - WebSocket 连接会自动重连

4. **API 限制**:
   - 注意交易所的 API 调用频率限制
   - 合理设置查询间隔

## 对比原策略

相比 `strategy/` 目录下的 EdgeX-Lighter 策略:
- GRVT 替代 EdgeX 作为 maker 交易所
- Aster 替代 Lighter 作为 taker 交易所
- API 调用使用各自交易所的官方 SDK 和方法
- 订单簿管理、仓位跟踪等核心逻辑保持一致

## 故障排除

如果遇到问题:
1. 查看日志文件 `logs/grvt_{TICKER}_log.txt`
2. 确认环境变量配置正确
3. 检查 API 密钥权限
4. 验证网络连接
