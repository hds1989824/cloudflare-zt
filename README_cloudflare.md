# Cloudflare Zero Trust 运维脚本说明

> 整理日期：2026-10-09
> 账号 ID：`1c46043a0de66ef8ee9e51ffdac5b61b`
> 用途：接管公司 Cloudflare Zero Trust 账号，日常查询与维护

## 一、文件结构

| 文件 | 作用 |
|---|---|
| `cf_config.py` | 公共配置：Token、账号 ID、maillist 列表 ID、API 地址 |
| `cf_zt.py` | **统一入口脚本**，所有操作走这里（推荐） |
| `cf_users.py` | 单独的用户统计脚本（历史版本，功能已并入 cf_zt.py） |
| `cf_dns.py` | 单独的 DNS 聚合脚本（历史版本，功能已并入 cf_zt.py） |
| `cf_egress.py` | 单独的出口策略脚本（历史版本，功能已并入 cf_zt.py） |

> 日常只需用 `cf_zt.py` 一个脚本即可，其余三个保留作参考。

## 二、环境准备

- Python 3（已验证 3.14）
- 依赖：`requests`（已安装）
- Token 建议用环境变量注入，避免明文留存：

```powershell
$env:CF_API_TOKEN = "你的token"
# 可选：覆盖账号/列表
$env:CF_ACCOUNT_ID = "..."
$env:CF_MAILLIST_ID = "..."
```

不设环境变量时，脚本使用 `cf_config.py` 里的默认值。

## 三、今天的查询诉求 → 对应命令

在本目录下执行（PowerShell 里加 `2>$null` 可屏蔽 requests 的版本警告）：

| 诉求 | 命令 |
|---|---|
| 查看 maillist 全部邮箱 | `python cf_zt.py maillist-show` |
| 向 maillist 增加邮箱（可多个） | `python cf_zt.py maillist-add a@x.com b@x.com` |
| 从 maillist 删除邮箱 | `python cf_zt.py maillist-del a@x.com` |
| 用户登录/操作日志（北京时间，动作含中文） | `python cf_zt.py access-logs` |
| 有多少用户开始使用了（用户统计） | `python cf_zt.py users` |
| DNS 访问聚合报表（全账号，默认7天） | `python cf_zt.py dns-report 7` |
| 出口策略配置（默认 streamax） | `python cf_zt.py egress` 或 `python cf_zt.py egress 名称` |
| 校验 token 是否有效 | `python cf_zt.py verify` |

## 四、各能力的数据来源与边界（重要）

### 1. maillist 邮箱列表（可读写）
- 接口：`GET/PATCH /gateway/lists/{list_id}` 及 `/items`
- 列表名 `maillist`，ID `aa5b54ec-db96-4d16-aa83-ce4b85c2b01c`，类型 EMAIL
- 追加用 `{"append":[{"value":...}]}`，删除用 `{"remove":[...]}`

### 2. Access 认证/登录记录（可读）
- 接口：`GET /access/logs/access_requests`
- 字段：时间、用户邮箱、是否放行、动作（login=认证登录 / warp_enrollment=WARP注册）、应用、来源 IP
- 边界：只保留最近窗口的日志，加过长的 `since`（如 365 天）会返回空；更久历史需 Logpush 留存

### 3. 用户使用情况（可读）
- 接口：`GET /access/users` + 上面的登录日志
- 可统计：创建的用户数、有登录记录的用户数、各用户首次/最近使用时间、来源 IP 数

### 4. DNS 访问聚合（可读，需 Account Analytics: Read 权限）
- 接口：GraphQL `gatewayResolverQueriesAdaptiveGroups`
- **重要边界**：此数据集**无用户维度**（没有 email/userId），**只有查询次数、没有流量字节数**
- 可按：域名(queryName)、分类(categoryNames)、位置(locationName)、决策(resolverDecision)、来源国家等聚合

### 5. 出口策略（可读）
- 接口：`GET /gateway/rules`，筛选 `action=egress`（**不是** `/gateway/egress_policies`，那个是 404）
- `streamax` 策略：匹配 `@streamax.com` 所有用户，走专用出口 IP
  - IPv4 主：`104.30.132.204`，备：`104.30.133.248`
  - IPv6：`2a09:bac0:1000:2d1::/64`

### 查不到的东西（受限）
- **按用户的带宽/流量用量**：拿不到。DNS 聚合无用户维度且无字节数；需走 Logpush 导出 `gateway_http`（含用户邮箱+上下行字节）自行聚合。
- **用户访问域名明细（逐条）**：拿不到。需 Logpush。
- 当前 Token 的 **Logpush / DEX** 接口均为 403，如需上述能力要在后台补 `Logs:Edit` + `Logpush:Edit` 权限。

## 五、安全提示

- 本仓库 `cf_config.py` 默认值里含 Token 明文，**建议改用环境变量**，并把真实 Token 从文件中移除。
- Token 用途广时，用完或泄露后在 Cloudflare 后台 **轮换（Roll）** 该 Token。
- 环境说明：本机 PowerShell 的 `ConvertFrom-Json` 存在兼容性 bug，故所有脚本统一用 Python + requests 实现。

## 六、2026-10-09 操作记录摘要

- maillist 从 8 条扩充到 16 条，新增：owen、rxyu、qlli2、smchen、wpwang、hyzhang1、wyliu、qfliu（均 @streamax.com）
- 确认已激活使用的用户：10 人（liuzhong 最早于 09-16，其余 9 人集中在 10-09 激活）
- 确认 streamax 出口策略配置（见上）
- 确认带宽/逐用户流量因数据集限制+权限不足，暂不可取
