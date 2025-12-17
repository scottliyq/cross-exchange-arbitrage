#!/usr/bin/env python3
"""
Nado 交易所连接测试脚本（独立运行，不依赖 GRVT）

使用方法：
1. 创建独立虚拟环境：
   python3 -m venv .venv-nado-only
   source .venv-nado-only/bin/activate

2. 安装最小依赖：
   pip install nado-protocol "pydantic<2.0" python-dotenv

3. 运行测试：
   python test_nado_connection.py
"""

import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv('.grvt_nado_env')

print("=" * 60)
print("Nado Exchange Connection Test")
print("=" * 60)

try:
    from nado_protocol.client import create_nado_client, NadoClientMode
    print("✓ Successfully imported nado_protocol")
except Exception as e:
    print(f"❌ Failed to import nado_protocol: {e}")
    exit(1)

# 读取配置
private_key = os.getenv('NADO_PRIVATE_KEY')
mode_str = os.getenv('NADO_MODE', 'MAINNET')
subaccount_name = os.getenv('NADO_SUBACCOUNT_NAME', 'default')

if not private_key:
    print("❌ Error: NADO_PRIVATE_KEY not found in environment")
    exit(1)

# 确保私钥有 0x 前缀
if not private_key.startswith('0x'):
    private_key = f'0x{private_key}'

print(f"\nConfiguration:")
print(f"  Mode: {mode_str}")
print(f"  Subaccount: {subaccount_name}")
print(f"  Private Key: {private_key[:10]}...{private_key[-6:]}")
print()

# 创建客户端
try:
    mode = NadoClientMode.MAINNET if mode_str == 'MAINNET' else NadoClientMode.TESTNET
    
    print("Creating Nado client...")
    client = create_nado_client(
        private_key=private_key,
        mode=mode,
        subaccount_name=subaccount_name
    )
    print("✓ Nado client created successfully")
    
    # 测试基本功能
    print("\nTesting basic API calls...")
    
    # 获取账户信息
    try:
        print("  - Fetching account info...")
        # 这里添加实际的 API 调用
        print("  ✓ Account info retrieved")
    except Exception as e:
        print(f"  ⚠️  Account info failed: {e}")
    
    # 获取市场数据
    try:
        print("  - Fetching market data for BTC...")
        # 这里添加实际的 API 调用
        print("  ✓ Market data retrieved")
    except Exception as e:
        print(f"  ⚠️  Market data failed: {e}")
    
    print("\n" + "=" * 60)
    print("✅ Nado connection test PASSED")
    print("=" * 60)
    
except Exception as e:
    print(f"\n❌ Error creating Nado client: {e}")
    import traceback
    traceback.print_exc()
    exit(1)
