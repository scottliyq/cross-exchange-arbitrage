### 问题诊断结果

## 当前问题
`.grvt_nado_env` 中的 Supabase keys 不符合 JWT token 格式要求：
- `SUPABASE_API_KEY`: `sb_publishable_JqVTWXFlGo7V-zMYGJAx-g_0pBi4g6s` (46 chars)
- `SUPABASE_SECRET_KEY`: `sb_secret_oUM7dOTnHvtS_oe5PzqM_g_L8OyWs8P` (41 chars)

## 原因
Supabase Python SDK (v2.3.4) 要求 API keys 必须是有效的 JWT tokens：
- JWT tokens 有 3 部分，用点号分隔：`header.payload.signature`
- 示例：`eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS...`
- 通常长度在 200-300 字符

当前的 keys 缺少点号结构，因此被 SDK 拒绝。

## 代码已实现的功能
`supabase_helper.py` 已正确实现：
1. ✅ 读取两个独立的环境变量：`SUPABASE_API_KEY` 和 `SUPABASE_SECRET_KEY`
2. ✅ 优先使用 `SUPABASE_SECRET_KEY`（service role key）
3. ✅ 回退到 `SUPABASE_API_KEY`（anon/public key）

## 解决方案

### 选项 1：获取正确的 JWT keys（推荐）
1. 登录 Supabase Dashboard: https://supabase.com/dashboard
2. 选择项目：`ofqnecuultvtgyaiyphi`
3. 进入：Settings → API
4. 复制正确的 keys：
   - `anon public` key → `SUPABASE_API_KEY`
   - `service_role` key → `SUPABASE_SECRET_KEY`

### 选项 2：如果使用自定义 Supabase 部署
如果这是自定义的 Supabase 部署（非 supabase.com），可能需要：
1. 确认 API 端点配置
2. 检查是否需要不同的认证方式
3. 联系 Supabase 管理员获取正确的 keys

### 选项 3：降级到不验证 JWT 的旧版本（不推荐）
可以尝试更旧的 supabase SDK 版本，但这不是长期解决方案。

## 测试
运行以下命令验证配置：
```bash
uv run python test_direct_supabase.py
```
