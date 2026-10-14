# -*- coding: utf-8 -*-
"""Cloudflare Zero Trust 操作脚本 - 公共配置

安全提示：Token 必须通过环境变量注入，不要硬编码进仓库。
  PowerShell:  $env:CF_API_TOKEN = "你的token"
  Linux:       export CF_API_TOKEN="你的token"

所需环境变量：
  CF_ACCOUNT_ID          - Cloudflare 账号 ID
  CF_API_TOKEN           - Cloudflare API Token
  CF_MAILLIST_ID         - 邮箱列表 ID（可选）
  CF_OVERSEAS_HOSTS_ID   - 海外域名列表 ID（可选）
  CF_ATLASSIAN_USA_EGRESS_ID - Atlassian 美国出口列表 ID（可选）
  CF_USA_EGRESS_RULE_ID  - 美国出口规则 ID（可选）
"""
import os

# 账号 ID（必须从环境变量读取）
ACCOUNT_ID = os.environ.get("CF_ACCOUNT_ID")
if not ACCOUNT_ID:
    raise ValueError("环境变量 CF_ACCOUNT_ID 未设置")

# API Token（必须从环境变量读取）
API_TOKEN = os.environ.get("CF_API_TOKEN")
if not API_TOKEN:
    raise ValueError("环境变量 CF_API_TOKEN 未设置")

# 列表和规则 ID（可选，有默认值）
MAILLIST_ID = os.environ.get("CF_MAILLIST_ID", "aa5b54ec-db96-4d16-aa83-ce4b85c2b01c")
OVERSEAS_HOSTS_ID = os.environ.get("CF_OVERSEAS_HOSTS_ID", "2b763847-f3cc-4fe7-9330-6ac93856ab3e")
ATLASSIAN_USA_EGRESS_ID = os.environ.get("CF_ATLASSIAN_USA_EGRESS_ID", "944ea699-1e13-43fe-b0d1-19e47478f8b2")
USA_EGRESS_RULE_ID = os.environ.get("CF_USA_EGRESS_RULE_ID", "89c78ef1-d128-4ac0-8bdd-f92fb8543d19")

# API 基础地址
API_BASE = f"https://api.cloudflare.com/client/v4/accounts/{ACCOUNT_ID}"
GRAPHQL_URL = "https://api.cloudflare.com/client/v4/graphql"

HEADERS = {
    "Authorization": f"Bearer {API_TOKEN}",
    "Content-Type": "application/json",
}
