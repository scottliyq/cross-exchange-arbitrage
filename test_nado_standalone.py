"""独立测试 Nado 连接（不依赖其他交易所）"""
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv('.grvt_nado_env')

# 仅导入 nado
from exchanges.nado import NadoClient

print("✓ 成功导入 NadoClient")

# 测试初始化
try:
    nado = NadoClient()
    print(f"✓ NadoClient 初始化成功")
    print(f"  Mode: {nado.mode}")
    print(f"  Subaccount: {nado.subaccount_name}")
except Exception as e:
    print(f"❌ NadoClient 初始化失败: {e}")
