# -*- coding: utf-8 -*-
"""Cloudflare Zero Trust 运维脚本 - 统一入口

汇总 2026-10-09 的全部查询/操作诉求，封装为命令行子命令，便于复用。

用法（在本目录下）：
  python cf_zt.py maillist-show                     查看 maillist 全部邮箱
  python cf_zt.py maillist-add a@x.com b@x.com      向 maillist 追加邮箱（可多个）
  python cf_zt.py maillist-del a@x.com              从 maillist 删除指定邮箱
  python cf_zt.py access-logs                       Access 认证/登录记录（北京时间，动作含中文）
  python cf_zt.py users                             用户使用情况统计（谁开始用了）
  python cf_zt.py dns-report [天数]                 DNS 访问聚合报表（默认7天，全账号）
  python cf_zt.py egress [名称]                     出口策略配置（默认查 main）
  python cf_zt.py split-tunnel-show                 查询拆分隧道 Include 列表
  python cf_zt.py split-tunnel-update [域名1] [域名2] ...  更新拆分隧道 Include 列表
  python cf_zt.py split-tunnel-clear                清空拆分隧道 Include 列表
  python cf_zt.py verify                            校验 token 是否有效

说明：
  - Token / 账号 / 列表ID 统一在 cf_config.py 中配置，支持用环境变量覆盖。
  - 本环境 PowerShell 的 ConvertFrom-Json 有兼容性 bug，故统一用 Python + requests。
"""
import sys
import json
import datetime
from collections import defaultdict, Counter

import requests

from cf_config import API_BASE, GRAPHQL_URL, HEADERS, ACCOUNT_ID, MAILLIST_ID, OVERSEAS_HOSTS_ID, ATLASSIAN_USA_EGRESS_ID, USA_EGRESS_RULE_ID


# ---------- 通用工具 ----------
def api_get(path):
    return requests.get(API_BASE + path, headers=HEADERS, timeout=60).json()


def api_patch(path, body):
    return requests.patch(API_BASE + path, headers=HEADERS, data=json.dumps(body), timeout=60).json()


def gql(query):
    return requests.post(GRAPHQL_URL, headers=HEADERS, data=json.dumps({"query": query}), timeout=60).json()


def to_bj(ts):
    """UTC 时间字符串 -> 北京时间(UTC+8)显示"""
    if not ts:
        return "-"
    try:
        dt = datetime.datetime.strptime(ts[:19], "%Y-%m-%dT%H:%M:%S")
        return (dt + datetime.timedelta(hours=8)).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return ts


def utc_days_ago(days):
    return (datetime.datetime.utcnow() - datetime.timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")


ACTION_CN = {
    "login": "认证登录",
    "warp_enrollment": "WARP注册",
    "logout": "登出",
    "token_refresh": "令牌刷新",
}


# ---------- 1. maillist 邮箱列表 ----------
def maillist_show():
    data = api_get(f"/gateway/lists/{MAILLIST_ID}/items?per_page=1000")
    items = data.get("result") or []
    print(f"maillist 当前共 {len(items)} 条：")
    for it in items:
        print("  -", it.get("value"))


def maillist_add(emails):
    if not emails:
        print("请提供至少一个邮箱")
        return
    body = {"append": [{"value": e} for e in emails]}
    resp = api_patch(f"/gateway/lists/{MAILLIST_ID}", body)
    print(f"追加 {emails} -> success={resp.get('success')}")
    maillist_show()


def maillist_del(emails):
    if not emails:
        print("请提供至少一个邮箱")
        return
    body = {"remove": list(emails)}
    resp = api_patch(f"/gateway/lists/{MAILLIST_ID}", body)
    print(f"删除 {emails} -> success={resp.get('success')}")
    maillist_show()


# ---------- 2. Access 认证/登录记录 ----------
def access_logs():
    data = api_get("/access/logs/access_requests?limit=1000")
    logs = data.get("result") or []
    print(f"Access 认证/登录记录：共 {len(logs)} 条（时间=北京时间 UTC+8，倒序）\n")
    for i, e in enumerate(logs, 1):
        action = e.get("action") or "unknown"
        cn = ACTION_CN.get(action, "未知")
        print(f"{i:>2}. {to_bj(e.get('created_at'))}  {(e.get('user_email') or '-'):<26} "
              f"allowed={e.get('allowed')}  {action}({cn})  app={e.get('app_domain')}  ip={e.get('ip_address')}")


# ---------- 3. 用户使用情况统计 ----------
def users_report():
    users = api_get("/access/users").get("result", [])
    print(f"===== Access 用户列表：共 {len(users)} 人 =====")
    for u in sorted(users, key=lambda x: x.get("last_successful_login") or "", reverse=True):
        print(f"  {(u.get('email') or '-'):<28} 最近登录={to_bj(u.get('last_successful_login')):<22} "
              f"gateway_seat={u.get('gateway_seat')}")

    logs = api_get("/access/logs/access_requests?limit=1000").get("result", [])
    by_user = defaultdict(lambda: {"login": 0, "warp": 0, "first": None, "last": None, "ips": set()})
    action_counter = Counter()
    for e in logs:
        email = e.get("user_email") or "(未知)"
        action = e.get("action") or "unknown"
        action_counter[action] += 1
        t = e.get("created_at")
        rec = by_user[email]
        if action == "login":
            rec["login"] += 1
        elif action == "warp_enrollment":
            rec["warp"] += 1
        if e.get("ip_address"):
            rec["ips"].add(e["ip_address"])
        if rec["first"] is None or (t and t < rec["first"]):
            rec["first"] = t
        if rec["last"] is None or (t and t > rec["last"]):
            rec["last"] = t

    print(f"\n--- 动作类型统计 ---")
    for a, c in action_counter.most_common():
        print(f"  {a:<18}{c}")

    print(f"\n--- 按用户统计（活跃用户 {len(by_user)} 人）---")
    for email, rec in sorted(by_user.items(), key=lambda kv: kv[1]["last"] or "", reverse=True):
        print(f"  {email:<28} 登录={rec['login']} WARP={rec['warp']} "
              f"首次={to_bj(rec['first'])} 最近={to_bj(rec['last'])} IP数={len(rec['ips'])}")

    logged_in = [u for u in users if u.get('last_successful_login')]
    print(f"\n===== 汇总 =====")
    print(f"  Access 用户数            : {len(users)}")
    print(f"  有成功登录记录的用户     : {len(logged_in)}")
    print(f"  登录日志中出现的活跃用户 : {len(by_user)}")


# ---------- 4. DNS 访问聚合报表（全账号，无用户维度）----------
def dns_report(days=7):
    since, until = utc_days_ago(days), utc_days_ago(0)

    def top_by(dimension, limit=15):
        q = (f'query {{ viewer {{ accounts(filter:{{accountTag:"{ACCOUNT_ID}"}}) {{ '
             f'gatewayResolverQueriesAdaptiveGroups(limit:{limit}, '
             f'filter:{{datetime_geq:"{since}", datetime_leq:"{until}"}}, orderBy:[count_DESC]) '
             f'{{ count dimensions {{ {dimension} }} }} }} }} }}')
        data = gql(q)
        if data.get("errors"):
            print(f"[{dimension}] errors: {data['errors']}")
            return
        rows = data["data"]["viewer"]["accounts"][0]["gatewayResolverQueriesAdaptiveGroups"]
        print(f"\n=== 近{days}天 按 {dimension} Top{limit} ===")
        for r in rows:
            print(f"  {r['count']:>8}  {r['dimensions'].get(dimension)}")

    print(f"DNS 访问聚合报表（全账号聚合，注意：此数据集无用户维度、仅查询次数非字节数）")
    top_by("queryName", 15)
    top_by("categoryNames", 10)
    top_by("resolverDecision", 10)


# ---------- 5. 出口策略 ----------
def egress(name="main"):
    data = api_get("/gateway/rules")
    rules = data.get("result") or []
    hits = [r for r in rules if name.lower() in str(r.get("name", "")).lower()]
    if not hits:
        print(f"未找到名称含 '{name}' 的 Gateway 规则。现有规则：")
        for r in rules:
            print(f"  - {r.get('name')} (action={r.get('action')})")
        return
    for t in hits:
        print(f">>> {t.get('name')} 配置：\n")
        print(json.dumps(t, ensure_ascii=False, indent=2))


def egress_update(rule_id=None, list_id=None):
    """更新 egress 规则的 traffic 字段，引用指定列表"""
    if not rule_id:
        rule_id = USA_EGRESS_RULE_ID
    if not list_id:
        list_id = ATLASSIAN_USA_EGRESS_ID
    body = {"traffic": f"net.fqdn.host in ${list_id}"}
    resp = api_patch(f"/gateway/rules/{rule_id}", body)
    if resp.get("success"):
        print(f"规则 {rule_id} 已更新为引用列表 {list_id}")
        print(f"  traffic: {resp.get('result', {}).get('traffic')}")
    else:
        print(f"更新失败: {resp.get('errors')}")


def egress_toggle(rule_id=None, enabled=True):
    """启用/禁用 egress 规则"""
    if not rule_id:
        rule_id = USA_EGRESS_RULE_ID
    body = {"enabled": enabled}
    resp = api_patch(f"/gateway/rules/{rule_id}", body)
    if resp.get("success"):
        status = "启用" if enabled else "禁用"
        print(f"规则 {rule_id} 已{status}")
    else:
        print(f"操作失败: {resp.get('errors')}")


# ---------- 7. 拆分隧道管理 ----------
def split_tunnel_show():
    """查询拆分隧道 Include 列表"""
    resp = api_get("/devices/policy/include")
    items = resp.get("result") or []
    print(f"拆分隧道 Include 列表共 {len(items)} 条：")
    for item in items:
        print(f"  - {item.get('host')}")


def split_tunnel_update(domains):
    """更新拆分隧道 Include 列表（完整替换）"""
    if not domains:
        print("请提供至少一个域名")
        return
    body = [{"host": d} for d in domains]
    resp = requests.put(
        f"{API_BASE}/devices/policy/include",
        headers=HEADERS,
        data=json.dumps(body),
        timeout=60
    ).json()
    if resp.get("success"):
        print(f"拆分隧道列表已更新，共 {len(domains)} 个域名")
    else:
        print(f"更新失败: {resp.get('errors')}")


def split_tunnel_clear():
    """清空拆分隧道 Include 列表"""
    resp = requests.put(
        f"{API_BASE}/devices/policy/include",
        headers=HEADERS,
        data=json.dumps([]),
        timeout=60
    ).json()
    if resp.get("success"):
        print("拆分隧道列表已清空")
    else:
        print(f"清空失败: {resp.get('errors')}")


# ---------- 8. 可重用列表管理 ----------
def list_create(name, list_type="DOMAIN", description=""):
    """创建可重用列表"""
    body = {"name": name, "type": list_type, "description": description}
    resp = requests.post(f"{API_BASE}/gateway/lists", headers=HEADERS, data=json.dumps(body), timeout=60).json()
    if resp.get("success"):
        print(f"列表 '{name}' 创建成功，ID: {resp['result']['id']}")
    else:
        print(f"创建失败: {resp.get('errors')}")


def list_add(list_id, values):
    """向列表追加条目"""
    if not values:
        print("请提供至少一个值")
        return
    body = {"append": [{"value": v} for v in values]}
    resp = api_patch(f"/gateway/lists/{list_id}", body)
    if resp.get("success"):
        print(f"已追加 {len(values)} 条到列表 {list_id}")
    else:
        print(f"追加失败: {resp.get('errors')}")


def list_del(list_id, values):
    """从列表删除条目"""
    if not values:
        print("请提供至少一个值")
        return
    body = {"remove": list(values)}
    resp = api_patch(f"/gateway/lists/{list_id}", body)
    if resp.get("success"):
        print(f"已从列表 {list_id} 删除 {len(values)} 条")
    else:
        print(f"删除失败: {resp.get('errors')}")


def list_show(list_id):
    """查看列表内容"""
    resp = api_get(f"/gateway/lists/{list_id}/items?per_page=1000")
    items = resp.get("result") or []
    print(f"列表 {list_id} 共 {len(items)} 条：")
    for it in items:
        print(f"  - {it.get('value')}")


def list_delete(list_id):
    """删除列表"""
    resp = requests.delete(f"{API_BASE}/gateway/lists/{list_id}", headers=HEADERS, timeout=60).json()
    if resp.get("success"):
        print(f"列表 {list_id} 已删除")
    else:
        print(f"删除失败: {resp.get('errors')}")


# ---------- 7. 校验 token ----------
def verify():
    r = requests.get("https://api.cloudflare.com/client/v4/user/tokens/verify",
                     headers=HEADERS, timeout=60).json()
    res = r.get("result") or {}
    print(f"token status={res.get('status')} id={res.get('id')}")


# ---------- 分发 ----------
def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return
    cmd, args = sys.argv[1], sys.argv[2:]
    dispatch = {
        "maillist-show": lambda: maillist_show(),
        "maillist-add": lambda: maillist_add(args),
        "maillist-del": lambda: maillist_del(args),
        "access-logs": lambda: access_logs(),
        "users": lambda: users_report(),
        "dns-report": lambda: dns_report(int(args[0]) if args else 7),
        "egress": lambda: egress(args[0] if args else "main"),
        "egress-update": lambda: egress_update(args[0] if args else None, args[1] if len(args) > 1 else None),
        "egress-toggle": lambda: egress_toggle(args[0] if args else None, args[1] != "false" if args else True),
        "split-tunnel-show": lambda: split_tunnel_show(),
        "split-tunnel-update": lambda: split_tunnel_update(args),
        "split-tunnel-clear": lambda: split_tunnel_clear(),
        "list-create": lambda: list_create(args[0] if args else "", args[1] if len(args) > 1 else "DOMAIN", args[2] if len(args) > 2 else ""),
        "list-add": lambda: list_add(args[0] if args else "", args[1:]),
        "list-del": lambda: list_del(args[0] if args else "", args[1:]),
        "list-show": lambda: list_show(args[0] if args else OVERSEAS_HOSTS_ID),
        "list-delete": lambda: list_delete(args[0] if args else ""),
        "verify": lambda: verify(),
    }
    fn = dispatch.get(cmd)
    if not fn:
        print(f"未知命令: {cmd}\n")
        print(__doc__)
        return
    fn()


if __name__ == "__main__":
    main()
