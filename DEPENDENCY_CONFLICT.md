# GRVT + Nado 依赖冲突解决方案

## 问题

`grvt-pysdk` 和 `nado-protocol` 有不兼容的依赖：

- **grvt-pysdk** 需要 `eth-account >= 0.13.4`（使用 `encode_typed_data` 函数）
- **nado-protocol** 需要 `eth-account >= 0.8.0, < 0.9.0`

这两个版本范围不重叠，无法在同一环境中安装。

## 解决方案

### 选项 1：使用单独的虚拟环境（推荐）

为 GRVT 和 Nado 创建独立的环境：

```bash
# Nado 环境（当前）
uv venv .venv-nado
source .venv-nado/bin/activate
uv pip install -r requirements.txt
uv pip install nado-protocol>=0.2.8

# GRVT 环境
uv venv .venv-grvt
source .venv-grvt/bin/activate
uv pip install -r requirements.txt
uv pip install grvt-pysdk>=0.1.0
```

运行时指定环境：
```bash
# 运行 Nado bot
source .venv-nado/bin/activate
python maker_taker_bot.py --config-key xxx --symbol ETH

# 运行 GRVT bot  
source .venv-grvt/bin/activate
python maker_taker_bot.py --config-key xxx --symbol BTC
```

### 选项 2：修改代码避免同时使用

如果必须在同一环境中运行，可以修改代码使 GRVT 和 Nado 不会同时导入。

### 选项 3：等待依赖更新

联系 `grvt-pysdk` 或 `nado-protocol` 维护者，请求他们放宽依赖约束。

## 当前状态

✅ **Supabase**: 已修复，使用 REST API 绕过 JWT 验证
❌ **GRVT + Nado**: 无法在同一环境运行，需要分离

## 推荐做法

对于 `grvt_nado` 策略，建议：
1. 检查是否真的需要同时使用两个交易所
2. 考虑分离为两个独立的 bot
3. 或者使用 REST API 替代 grvt-pysdk
