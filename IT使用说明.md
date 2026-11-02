# Cloudflare Zero Trust 运维脚本使用说明

> ## ⚠ 当前服务状态（2026-10-24）
> Cloudflare WARP 试用已到期，当前 WARP 客户端、拆分隧道和 WARP Egress 出口能力均**不可用**。在 IT 完成续费、授权恢复或确认替代方案前，请勿将 WARP 视为可用网络通道，也不要执行拆分隧道、Egress 策略等生产变更。
>
> 本仓库脚本仅可在 API Token 仍有效时用于查询现有配置；文档中的 WARP 测试结果均为历史记录，不代表当前可用状态。请等待 IT 通知恢复后再重新验证。

## 环境准备

1. 安装 Python 3
2. 安装依赖：`pip install requests`
3. 配置环境变量（二选一）：

**方式A：设置环境变量**
```powershell
$env:CF_ACCOUNT_ID = "你的账号ID"
$env:CF_API_TOKEN = "你的API Token"
```

**方式B：使用 .env 文件**
```
# 在项目目录创建 .env 文件
CF_ACCOUNT_ID=你的账号ID
CF_API_TOKEN=你的API Token
```

加载 .env：
```powershell
Get-Content .env | ForEach-Object { $name, $value = $_ -split '=', 2; if ($name -and $name -notmatch '^#') { Set-Item -Path "env:$name" -Value $value } }
```

---

## 常用命令

### 用户管理

```powershell
# 查看所有用户
python cf_zt.py users

# 查看 Access 登录日志
python cf_zt.py access-logs
```

### 邮箱列表管理

```powershell
# 查看邮箱列表
python cf_zt.py maillist-show

# 添加邮箱
python cf_zt.py maillist-add 邮箱1 邮箱2

# 删除邮箱
python cf_zt.py maillist-del 邮箱
```

### 拆分隧道管理

```powershell
# 查看当前列表
python cf_zt.py split-tunnel-show

# 更新域名列表（完整替换）
python cf_zt.py split-tunnel-update 域名1 域名2 域名3

# 清空列表
python cf_zt.py split-tunnel-clear
```

### DNS 报表

```powershell
# 查看最近 7 天 DNS 查询 Top 域名
python cf_zt.py dns-report 7

# 查看最近 1 天
python cf_zt.py dns-report 1
```

### 出口策略

```powershell
# 查看 Egress 策略配置
python cf_zt.py egress

# 查看指定策略
python cf_zt.py egress 策略名称
```

### 可重用列表

```powershell
# 查看列表内容
python cf_zt.py list-show 列表ID

# 追加域名
python cf_zt.py list-add 列表ID 域名1 域名2

# 删除域名
python cf_zt.py list-del 列表ID 域名1
```

---

## 常见问题

**Q: 提示 "环境变量 CF_ACCOUNT_ID 未设置"**
A: 需要先设置环境变量，参考上面的配置方式。

**Q: 提示 "Authentication error"**
A: Token 权限不足，需要在 Cloudflare 后台给 Token 添加 Zero Trust: Read 和 Lists: Edit 权限。

**Q: 提示 "Connection was reset"**
A: 网络问题，配置 Git 代理：
```powershell
git config --global http.proxy http://127.0.0.1:48878
git config --global https.proxy http://127.0.0.1:48878
```

---

## 脚本位置

```
D:\code\cloudflare-zt\cf_zt.py
```

所有命令在项目目录下执行。
