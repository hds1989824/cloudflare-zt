# Cloudflare Zero Trust 运维脚本

> 更新日期：2026-10-14
> 用途：Cloudflare Zero Trust 日常查询与维护

---

## 一、文件结构

| 文件 | 作用 |
|---|---|
| `cf_config.py` | 公共配置：API 地址、列表 ID 等（敏感信息通过环境变量注入） |
| `cf_zt.py` | **统一入口脚本**，所有操作走这里 |

---

## 二、环境准备

- Python 3
- 依赖：`requests`
- 敏感配置通过 `.env` 文件或环境变量注入

### 配置方式

**方式1：.env 文件（推荐）**

创建 `.env` 文件：

```
CF_ACCOUNT_ID=your_account_id
CF_API_TOKEN=your_api_token
```

**方式2：环境变量**

```powershell
$env:CF_ACCOUNT_ID = "your_account_id"
$env:CF_API_TOKEN = "your_api_token"
```

**方式3：直接修改 `cf_config.py`**

```python
ACCOUNT_ID = os.environ.get("CF_ACCOUNT_ID", "your_account_id")
API_TOKEN = os.environ.get("CF_API_TOKEN", "your_api_token")
```

---

## 三、命令列表

### 拆分隧道管理

| 命令 | 说明 |
|---|---|
| `python cf_zt.py split-tunnel-show` | 查询拆分隧道 Include 列表 |
| `python cf_zt.py split-tunnel-update [域名1] [域名2] ...` | 更新拆分隧道 Include 列表 |
| `python cf_zt.py split-tunnel-clear` | 清空拆分隧道 Include 列表 |

### Egress 策略

| 命令 | 说明 |
|---|---|
| `python cf_zt.py egress` | 查看所有 Egress 策略 |
| `python cf_zt.py egress-update [规则ID] [列表ID]` | 更新策略引用的列表 |
| `python cf_zt.py egress-toggle [规则ID] [true/false]` | 启用/禁用策略 |

### 列表管理

| 命令 | 说明 |
|---|---|
| `python cf_zt.py list-show [列表ID]` | 查看列表内容 |
| `python cf_zt.py list-add [列表ID] [域名1] [域名2] ...` | 追加域名 |
| `python cf_zt.py list-del [列表ID] [域名1] [域名2] ...` | 删除域名 |
| `python cf_zt.py maillist-show/add/del` | 邮箱列表快捷操作 |

### 日志查询

| 命令 | 说明 |
|---|---|
| `python cf_zt.py access-logs` | Access 认证/登录记录 |
| `python cf_zt.py dns-report [天数]` | DNS 聚合报表（默认7天） |
| `python cf_zt.py users` | 用户使用情况统计 |
| `python cf_zt.py verify` | 校验 Token 是否有效 |

---

## 四、分流逻辑

```
用户访问域名
    │
    ▼
拆分隧道（Include 模式，API 配置）
    │
    ├─ 在拆分隧道列表中 → 走 WARP 隧道
    │       │
    │       ▼
    │   Egress 策略
    │       │
    │       ├─ 匹配 atlassian-usa-egress → 美国出口 IP
    │       │
    │       └─ 不匹配 → WARP 默认出口（海外 IP）
    │
    └─ 不在列表中 → 绕过 WARP，走本地网络出口
```

---

## 五、关键发现

### 拆分隧道 API

拆分隧道支持通过 API 配置，无需在仪表板中手动逐个添加：

```
GET  /accounts/{account_id}/devices/policy/include   # 查询 Include 列表
PUT  /accounts/{account_id}/devices/policy/include   # 更新 Include 列表
```

请求体格式：`[{"host": "example.com"}, ...]`

### DNS 解析行为

| 场景 | DNS 解析 | 说明 |
|------|---------|------|
| 拆分隧道 Include 列表中域名 | Gateway DNS | Cloudflare 解析 |
| 不在列表中的域名 | 本地 DNS | 系统 DNS 解析 |
| Cloudflare 基础设施域名 | 本地 DNS | WARP 客户端强制本地解析 |

### WARP 客户端日志

```
C:\ProgramData\Cloudflare\snapshots\*.log
```

---

## 六、安全提示

- **Token 必须通过环境变量或 `.env` 文件注入，不要硬编码在代码中**
- `.env` 文件已加入 `.gitignore`，不会被提交到 Git
- Token 泄露后在 Cloudflare 后台**轮换（Roll）**该 Token
- 建议定期更换 API Token

---

## 七、踩坑记录

1. **拆分隧道不支持引用可重用列表** — 通过API 添加域名（或web仪表板）
2. **拆分隧道 Include 模式下 DNS 本地解析** — 可能导致 Egress 策略的 `net.fqdn.host` 匹配失效
3. **URL 列表 vs Hostname 列表** — 拆分隧道只支持 DOMAIN 类型列表

