# GRVT-Aster 价差套利策略实现总结

## 实现概述

已成功在 `strategy_grvt/` 目录下实现了 GRVT 和 Aster 交易所之间的价差套利策略。该策略参考了 `strategy/` 目录下的 EdgeX-Lighter 策略架构。

## 核心替换

| 原策略 (strategy/) | 新策略 (strategy_grvt/) |
|------------------|---------------------|
| EdgeX (Maker)    | GRVT (Maker)        |
| Lighter (Taker)  | Aster (Taker)       |

## 创建的文件

### 1. `__init__.py`
包初始化文件，标识 strategy_grvt 为 Python 包。

### 2. `grvt_arb.py` (主策略文件)
- **类**: `GrvtArb`
- **功能**:
  - 初始化 GRVT 和 Aster 客户端
  - 监控两个交易所的 BBO (最优买卖价)
  - 检测套利机会 (价差超过阈值)
  - 执行套利交易:
    - 做多: GRVT 买入 (post-only) + Aster 卖出 (market)
    - 做空: GRVT 卖出 (post-only) + Aster 买入 (market)
  - 管理仓位和风险控制
  - 记录交易日志

### 3. `order_manager.py` (订单管理器)
- **类**: `OrderManager`
- **功能**:
  - 管理 GRVT 的 post-only 订单
  - 管理 Aster 的 market 订单
  - 获取 BBO 价格
  - 监控订单状态
  - 处理订单更新回调

### 4. `order_book_manager.py` (订单簿管理器)
- **类**: `OrderBookManager`
- **功能**:
  - 维护 GRVT 和 Aster 的订单簿状态
  - 更新订单簿数据
  - 提供 BBO 查询接口
  - 验证订单簿完整性

### 5. `position_tracker.py` (仓位跟踪器)
- **类**: `PositionTracker`
- **功能**:
  - 跟踪 GRVT 持仓
  - 跟踪 Aster 持仓
  - 计算净持仓
  - 更新持仓变化

### 6. `data_logger.py` (数据记录器)
- **类**: `DataLogger`
- **功能**:
  - 记录交易到 CSV
  - 记录 BBO 数据到 CSV
  - 支持后续数据分析

### 7. `README.md` (使用文档)
包含详细的使用说明、配置指南和注意事项。

## 主入口文件

### `main_grvt_arb.py`
位于项目根目录，用于启动策略:
```python
python main_grvt_arb.py
```

## 核心交易逻辑

### 做多套利 (Long GRVT)
**条件**: `Aster 买价 - GRVT 买价 > long_grvt_threshold`

**操作**:
1. 在 GRVT 上下 post-only 买单
2. 订单成交后，在 Aster 上下 market 卖单
3. 赚取价差

### 做空套利 (Short GRVT)
**条件**: `GRVT 卖价 - Aster 卖价 > short_grvt_threshold`

**操作**:
1. 在 GRVT 上下 post-only 卖单
2. 订单成交后，在 Aster 上下 market 买单
3. 赚取价差

## API 调用

### GRVT 客户端 (exchanges/grvt.py)
- `fetch_bbo_prices()` - 获取 BBO 价格
- `place_post_only_order()` - 下 post-only 订单
- `cancel_order()` - 取消订单
- `get_order_info()` - 获取订单信息
- `get_real_position()` - 获取持仓
- `connect()` - 连接 WebSocket
- `setup_order_update_handler()` - 设置订单更新回调

### Aster 客户端 (exchanges/aster.py)
- `fetch_bbo_prices()` - 获取 BBO 价格
- `place_market_order()` - 下 market 订单
- `get_order_info()` - 获取订单信息
- `get_real_position()` - 获取持仓
- `connect()` - 连接 WebSocket

## 环境变量配置

需要在 `.env` 文件中设置:

```bash
# GRVT 配置
GRVT_TRADING_ACCOUNT_ID=your_account_id
GRVT_PRIVATE_KEY=your_private_key
GRVT_API_KEY=your_api_key
GRVT_ENVIRONMENT=prod

# Aster 配置
ASTER_API_KEY=your_api_key
ASTER_SECRET_KEY=your_secret_key

# 交易参数
TICKER=BTC
ORDER_QUANTITY=0.01
MAX_POSITION=0.1
LONG_GRVT_THRESHOLD=10
SHORT_GRVT_THRESHOLD=10
```

## 日志输出

### 日志文件位置
- `logs/grvt_{TICKER}_log.txt` - 主日志
- `logs/grvt_{TICKER}_trades.csv` - 交易记录
- `logs/grvt_{TICKER}_bbo_data.csv` - BBO 数据

### 日志内容
- 初始化信息
- 连接状态
- 价格数据
- 订单状态
- 交易执行
- 持仓变化
- 错误和警告

## 风险控制

1. **最大持仓限制**: `MAX_POSITION` 参数
2. **仓位偏离检查**: 净持仓不能超过 `order_quantity * 2`
3. **订单超时**: 5 秒后取消未成交的 post-only 订单
4. **异常处理**: 完善的错误捕获和恢复机制
5. **优雅退出**: 信号处理和资源清理

## 与原策略的差异

### 相同点
- 整体架构和模块划分
- 订单簿管理逻辑
- 仓位跟踪机制
- 数据记录格式

### 不同点
- 使用 GRVT SDK 替代 EdgeX SDK
- 使用 Aster REST API 替代 Lighter SDK
- WebSocket 连接和订单更新处理适配各自交易所
- 订单下单参数和返回格式适配

## 测试建议

1. **模拟环境测试**:
   - 设置 `GRVT_ENVIRONMENT=testnet`
   - 使用测试账号和小额资金

2. **参数调优**:
   - 先用较大的阈值测试
   - 观察套利机会频率
   - 逐步调整到合适的阈值

3. **监控指标**:
   - 交易频率
   - 平均价差
   - 成交率
   - 滑点成本
   - 净持仓变化

## 已知限制

1. **类型检查警告**: 代码中存在一些类型检查警告，但不影响实际运行
2. **网络延迟**: WebSocket 连接质量影响套利效率
3. **订单簿深度**: 需要足够的流动性支持套利交易

## 后续优化建议

1. **动态阈值**: 根据市场波动率自动调整套利阈值
2. **多币种支持**: 扩展到多个交易对
3. **风险监控**: 添加实时风控告警
4. **性能优化**: 减少 API 调用延迟
5. **回测系统**: 基于历史数据回测策略表现

## 使用流程

1. 配置环境变量
2. 运行策略: `python main_grvt_arb.py`
3. 监控日志输出
4. 查看交易记录和数据分析
5. 根据需要调整参数

## 技术栈

- **Python 3.10+**
- **asyncio** - 异步编程
- **GRVT SDK** - GRVT 交易所接口
- **Aster REST API** - Aster 交易所接口
- **WebSocket** - 实时数据订阅
- **CSV** - 数据记录
- **Logging** - 日志系统
